#!/usr/bin/env phasenet
"""
Parallel P-phase picking using STA/LTA on full-day SAC data.

Changes relative to original version:
- Preload station list once.
- Parallelize over stations with ProcessPoolExecutor.
- Optional decimation for STA/LTA (500 Hz -> 100 Hz by default).
- Skip WA simulation if there are no triggers (but still write empty P file).
"""

import os
import shutil
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np
from obspy import read, UTCDateTime
from obspy.signal.trigger import recursive_sta_lta, trigger_onset

# -------------------- CONFIG -------------------- #

# Root directory of SAC waveform files, organized as:
#   ddir / YYYYMMDD / NET.STA.CHAN.*
ddir = Path("../../Data/waveform_sac/")

# Station file: "stlo, stla, net, sta, chan, elev" per line
stationdir = Path("../../Data/station_all.dat")

# Date range
year0 = 2023
mon0 = 5
day0 = 6
nday = 2  # number of days

# WA simulation parameters
# https://docs.obspy.org/_modules/obspy/signal/invsim.html
paz_wa = {
    "poles": [-6.283 + 4.7124j, -6.283 - 4.7124j],
    "zeros": [0 + 0j],
    "gain": 1.0,
    "sensitivity": 2080,
}

# CPUS = int(os.environ.get("SLURM_CPUS_PER_TASK", "40"))  # default 40 if not under SLURM
# N_WORKERS = max(1, CPUS - 4)  # leave a few cores for overhead / I/O
N_WORKERS = 16
# Optional decimation factor for STA/LTA only (after bandpass)
# 1 = no decimation; 5 → 500 Hz → 100 Hz for triggering
STA_DECIMATE = 5


# -------------------- HELPERS -------------------- #

def load_station_list(path: Path):
    """
    Load station metadata from CSV-like file:
        stlo, stla, net, sta, chan, elev
    Returns a list of tuples.
    """
    stations = []
    with path.open("r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 6:
                continue
            stlo, stla, net, sta, chan, elev = parts[:6]
            stations.append((stlo, stla, net.strip(), sta.strip(), chan.strip(), elev))
    return stations


def process_one_station(day_root: Path, year: str, mon: str, day: str,
                        output_dir: Path, station_entry):
    """
    Process one station for a given day:
    - Read Z, N, E components.
    - Preprocess vertical (detrend + bandpass).
    - (Optionally) decimate for STA/LTA.
    - Run STA/LTA and trigger_onset.
    - If triggers exist: simulate WA on horizontals and compute amplitudes.
    - Write P picks to 'output_dir/net.sta.P.txt'.

    Returns a short message for logging.
    """
    stlo, stla, net, sta, chan, elev = station_entry

    chanz = chan[:2] + "Z"
    chann = chan[:2] + "N"
    chane = chan[:2] + "E"

    wavez = day_root / f"{net}.{sta}.{chanz}"
    wavee = day_root / f"{net}.{sta}.{chane}"
    waven = day_root / f"{net}.{sta}.{chann}"

    try:
        stz = read(str(wavez) + "*")
        ste = read(str(wavee) + "*")
        stn = read(str(waven) + "*")
    except Exception:
        return f"no station, skip the station {net} {sta}"

    if len(stz) == 0 or len(ste) == 0 or len(stn) == 0:
        return f"no station data, skip the station {net} {sta}"

    trz = stz[0]
    tre = ste[0]
    trn = stn[0]

    # Preprocess vertical
    trz.detrend("demean")
    trz.detrend("linear")
    trz.filter(type="bandpass", freqmin=2.0, freqmax=24.0, zerophase=False)

    df = trz.stats.sampling_rate
    t0 = UTCDateTime(int(year), int(mon), int(day))
    tstart = trz.stats.starttime - t0  # seconds from midnight

    # Output file
    output = output_dir / f"{net}.{sta}.P.txt"

    # ------------- STA/LTA (possibly decimated) ------------- #
    if STA_DECIMATE > 1:
        trz_sta = trz.copy()
        # already bandpassed, so we can decimate without internal filter
        trz_sta.decimate(STA_DECIMATE, no_filter=True)
        df_sta = trz_sta.stats.sampling_rate
        data_sta = trz_sta.data
    else:
        df_sta = df
        data_sta = trz.data

    nsta = int(0.1 * df_sta)
    nlta = int(2.5 * df_sta)

    if nsta < 1 or nlta <= nsta:
        return f"bad STA/LTA window for {net} {sta} (df_sta={df_sta})"

    cft = recursive_sta_lta(data_sta, nsta, nlta)
    on_of = trigger_onset(cft, 6.0, 2.0)

    # If no triggers: create empty file (to match old behavior), skip simulate()
    if len(on_of) == 0:
        output.touch()
        return f"no triggers {net} {sta}"

    # ------------- WA simulation on horizontals ------------- #
    tre.simulate(
        paz_remove=None,
        paz_simulate=paz_wa,
        taper=True,
        taper_fraction=0.00001,
    )
    trn.simulate(
        paz_remove=None,
        paz_simulate=paz_wa,
        taper=True,
        taper_fraction=0.00001,
    )
    datatre = tre.data
    datatrn = trn.data

    # ------------- Write triggers ------------- #
    with output.open("w") as f:
        for trig_on_sta, trig_of_sta in on_of:
            # Map STA/LTA indices back to full-rate indices
            trig_on = int(trig_on_sta * (df / df_sta))
            trig_of = int(trig_of_sta * (df / df_sta))

            # 3 sec later to include potential S phase:
            # trig_off = trig_of + 4×window_length + 3 s   (in FULL-RATE samples)
            trig_off = int(trig_of + (trig_of - trig_on) * 4.0 + 3 * df)
            if trig_off >= trz.stats.npts - 1:
                break

            seg_e = datatre[trig_on:trig_off]
            seg_n = datatrn[trig_on:trig_off]
            if seg_e.size == 0 or seg_n.size == 0:
                continue

            # average amplitude (half peak-to-peak), mm
            amp = (
                np.max(seg_e)
                + abs(np.min(seg_e))
                + np.max(seg_n)
                + abs(np.min(seg_n))
            ) / 4.0 * 1000.0

            max_cft = np.max(cft[trig_on_sta:trig_of_sta])
            if max_cft > 10.0:
                pick_time = (tstart + trig_on / df)
                f.write(f"{pick_time:.4f} {max_cft:.4f} {amp:.4e}\n")

    return f"done {net} {sta}"


# -------------------- MAIN -------------------- #

def main():
    stations = load_station_list(stationdir)
    print(f"Loaded {len(stations)} stations from {stationdir}")

    for d in range(nday):
        origins = UTCDateTime(year0, mon0, day0) + 86400 * d
        newdate = origins.strftime("%Y/%m/%d")
        year, mon, day = newdate.split("/")

        print(f"Picking P phases: date {d+1} / {nday}")
        print(year, mon, day)

        date_str = f"{year}{mon}{day}"          # e.g. '20230410'
        day_root = ddir / date_str             # e.g. ../../Data/waveform_sac/20230410

        # Output directory for this day (relative to current working directory)
        out_dir = Path(date_str)
        if out_dir.is_dir():
            shutil.rmtree(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        if not day_root.is_dir():
            print(f"[WARN] Day directory missing: {day_root}, skipping day.")
            continue

        print(f"Using {N_WORKERS} workers for ~{len(stations)} stations")

        # Parallel over stations
        results = []
        with ProcessPoolExecutor(max_workers=N_WORKERS) as ex:
            futures = [
                ex.submit(
                    process_one_station,
                    day_root,
                    year,
                    mon,
                    day,
                    out_dir,
                    st_entry,
                )
                for st_entry in stations
            ]

            for i, fut in enumerate(as_completed(futures), start=1):
                msg = fut.result()
                results.append(msg)
                # Light progress logging
                if i % 25 == 0:
                    print(f"[{i}/{len(futures)}] {msg}")

        print(f"Finished day {date_str}")
        # Optionally summarize results:
        n_done = sum("done" in r for r in results)
        n_notrig = sum("no triggers" in r for r in results)
        n_skip = sum("skip" in r for r in results)
        print(f"  Stations done: {n_done}, no triggers: {n_notrig}, skipped: {n_skip}")


if __name__ == "__main__":
    main()
