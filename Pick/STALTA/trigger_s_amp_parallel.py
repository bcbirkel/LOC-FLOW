#!/usr/bin/env python3
"""
Parallel S-phase picking using STA/LTA on full-day SAC data.

- Dates: 2023-04-10, nday=1 (matching the P picker).
- Preload station list once.
- Parallelize over stations with ProcessPoolExecutor.
- Optional decimation for STA/LTA (500 Hz -> 100 Hz by default).
- Skip WA simulation if there are no triggers (but still create an empty S.txt).
- Uses 'spawn' start method to avoid fork issues with ObsPy / C libs.
"""

import os
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp

import numpy as np
from obspy import read, UTCDateTime
from obspy.signal.trigger import trigger_onset


# -------------------- CONFIG -------------------- #

ddir = Path("../../Data/waveform_sac/")
stationdir = Path("../../Data/station_all.dat")  # <-- you already changed this

year0 = 2023
mon0 = 5
day0 = 1
nday = 7

paz_wa = {
    "poles": [-6.283 + 4.7124j, -6.283 - 4.7124j],
    "zeros": [0 + 0j],
    "gain": 1.0,
    "sensitivity": 2080,
}

import os
# CPUS = int(os.environ.get("SLURM_CPUS_PER_TASK", "40"))  # default 40 if not under SLURM
# N_WORKERS = max(1, CPUS - 4)  # leave a few cores for overhead / I/O
N_WORKERS=16
# 1 = no decimation; 5 → 500 Hz -> 100 Hz
STA_DECIMATE = 5


# -------------------- HELPERS -------------------- #

def load_station_list(path: Path):
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


def recSTALTAPy_h(a, b, nsta, nlta):
    """
    Same logic as your original recSTALTAPy_h, but:
    - no tolist()
    - uses NumPy arrays for STA/LTA/charfct
    """
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    ndat = a.size

    csta = 1.0 / nsta
    clta = 1.0 / nlta
    icsta = 1.0 - csta
    iclta = 1.0 - clta

    sta = 0.0
    lta = 1e-99

    charfct = np.zeros(ndat, dtype=np.float64)

    for i in range(1, ndat):
        sq = a[i] * a[i] + b[i] * b[i]
        sta = csta * sq + icsta * sta
        lta = clta * sq + iclta * lta
        charfct[i] = sta / lta
        if i < nlta:
            charfct[i] = 0.0

    return charfct



def process_one_station(day_root: Path, year: str, mon: str, day: str,
                        output_dir: Path, station_entry):
    """
    Worker function: returns a status string. Any exceptions are caught and
    returned as 'error ...' instead of killing the process.
    """
    try:
        stlo, stla, net, sta, chan, elev = station_entry

        chane = chan[:2] + "E"
        chann = chan[:2] + "N"

        wave_e = day_root / f"{net}.{sta}.{chane}"
        wave_n = day_root / f"{net}.{sta}.{chann}"

        try:
            ste = read(str(wave_e) + "*")
            stn = read(str(wave_n) + "*")
        except Exception as e:
            return f"error read {net} {sta}: {e!r}"

        if len(ste) == 0 or len(stn) == 0:
            return f"no station data, skip the station {net} {sta}"

        # Preprocess horizontals for STA/LTA
        ste.detrend("demean")
        ste.detrend("linear")
        stn.detrend("demean")
        stn.detrend("linear")
        ste.filter(type="bandpass", freqmin=2.0, freqmax=15.0, zerophase=False)
        stn.filter(type="bandpass", freqmin=2.0, freqmax=15.0, zerophase=False)

        tre = ste[0]
        trn = stn[0]

        df = tre.stats.sampling_rate
        t0 = UTCDateTime(int(year), int(mon), int(day))
        tstart = tre.stats.starttime - t0  # seconds from midnight

        output = output_dir / f"{net}.{sta}.S.txt"
        if output.is_file():
            output.unlink()

        # -------- STA/LTA (possibly decimated) -------- #
        if STA_DECIMATE > 1:
            tre_sta = tre.copy()
            trn_sta = trn.copy()
            tre_sta.decimate(STA_DECIMATE, no_filter=True)
            trn_sta.decimate(STA_DECIMATE, no_filter=True)
            df_sta = tre_sta.stats.sampling_rate
            data_e = tre_sta.data
            data_n = trn_sta.data
        else:
            df_sta = df
            data_e = tre.data
            data_n = trn.data

        nsta = int(0.2 * df_sta)
        nlta = int(2.5 * df_sta)

        if nsta < 1 or nlta <= nsta:
            output.touch()
            return f"bad STA/LTA window for {net} {sta} (df_sta={df_sta})"

        cft = recSTALTAPy_h(data_e, data_n, nsta, nlta)
        on_of = trigger_onset(cft, 4.0, 2.0)

        # No triggers: create empty file, skip WA simulation
        if len(on_of) == 0:
            output.touch()
            return f"no triggers {net} {sta}"

        # -------- WA simulation on horizontals -------- #
        try:
            wa_e = read(str(wave_e) + "*")
            wa_n = read(str(wave_n) + "*")
        except Exception as e:
            output.touch()
            return f"WA read error {net} {sta}: {e!r}"

        wa_e.simulate(
            paz_remove=None,
            paz_simulate=paz_wa,
            taper=True,
            taper_fraction=0.00001,
        )
        wa_n.simulate(
            paz_remove=None,
            paz_simulate=paz_wa,
            taper=True,
            taper_fraction=0.00001,
        )
        datatre = wa_e[0].data
        datatrn = wa_n[0].data

        # -------- Write triggers -------- #
        with output.open("w") as f:
            for trig_on_sta, trig_of_sta in on_of:
                # Map STA/LTA indices back to full-rate indices
                trig_on = int(trig_on_sta * (df / df_sta))
                trig_of = int(trig_of_sta * (df / df_sta))

                trig_off = int(trig_of + (trig_of - trig_on) * 4.0)
                if trig_off >= tre.stats.npts - 1:
                    break

                seg_e = datatre[trig_on:trig_off]
                seg_n = datatrn[trig_on:trig_off]
                if seg_e.size == 0 or seg_n.size == 0:
                    continue

                amp = (
                    np.max(seg_e)
                    + abs(np.min(seg_e))
                    + np.max(seg_n)
                    + abs(np.min(seg_n))
                ) / 4.0 * 1000.0

                max_cft = np.max(cft[trig_on_sta:trig_of_sta])
                if max_cft > 6.0:
                    pick_time = (tstart + trig_on / df)
                    f.write(f"{pick_time} {max_cft} {amp}\n")

        return f"done {net} {sta}"

    except Exception as e:
        # Catch any unexpected errors so they don't kill the worker
        return f"error {net} {sta}: {e!r}"


# -------------------- MAIN -------------------- #

def main():
    stations = load_station_list(stationdir)
    print(f"Loaded {len(stations)} stations from {stationdir}")

    for d in range(nday):
        origins = UTCDateTime(year0, mon0, day0) + 86400 * d
        newdate = origins.strftime("%Y/%m/%d")
        year, mon, day = newdate.split("/")

        print(f"Picking S phases: date {d+1} / {nday}")
        print(year, mon, day)

        date_str = f"{year}{mon}{day}"     # e.g. '20230410'
        day_root = ddir / date_str         # e.g. ../../Data/waveform_sac/20230410

        out_dir = Path(date_str)
        # if out_dir.is_dir():
        #     import shutil
        #     shutil.rmtree(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        if not day_root.is_dir():
            print(f"[WARN] Day directory missing: {day_root}, skipping day.")
            continue

        print(f"Using {N_WORKERS} workers for ~{len(stations)} stations")

        results = []
        # Use 'spawn' context to avoid fork-related crashes
        ctx = mp.get_context("spawn")
        with ProcessPoolExecutor(max_workers=N_WORKERS, mp_context=ctx) as ex:
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
                if i % 25 == 0 or msg.startswith("error"):
                    print(f"[{i}/{len(futures)}] {msg}")

        print(f"Finished day {date_str}")
        n_done = sum(r.startswith("done") for r in results)
        n_notrig = sum(r.startswith("no triggers") for r in results)
        n_skip = sum("skip the station" in r for r in results)
        n_err = sum(r.startswith("error") for r in results)
        print(f"  Stations done: {n_done}, no triggers: {n_notrig}, skipped: {n_skip}, errors: {n_err}")


if __name__ == "__main__":
    # Ensure spawn is used as default start method for safety
    try:
        mp.set_start_method("spawn", force=True)
    except RuntimeError:
        # Already set in this process; that's fine.
        pass
    main()
