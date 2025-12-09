#!/usr/bin/env python3
"""
Create daily [date].phase_sel.txt files from QuakeMigrate .event/.picks outputs.

For each event:
- Read .event to get origin time, lon, lat, depth, ML, ML_Err.
- Read .picks to get P/S picks, residuals, pick errors, etc.
- Use station file to compute azimuths and station gap.

Output:
  /project2/okaya_201/LOC-FLOW/Pick/QMigrate/YYYYMMDD.phase_sel.txt

Default inputs:
  runs_root  = /project2/okaya_201/QuakeMigrate/outputs/runs
  station_fn = /project2/okaya_201/QuakeMigrate/inputs/all_stations.txt
"""

import csv
import math
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import argparse
import sys


# --------- Event quality thresholds --------- #
MIN_P_PICKS = 8
MIN_S_PICKS = 5
MIN_TOTAL_PICKS = 10
MIN_STATIONS_WITH_BOTH = 5


# ----------------- Helpers ----------------- #

def parse_iso_z(ts):
    """Parse ISO8601 with trailing 'Z' into a timezone-aware datetime (UTC)."""
    if ts is None:
        return None
    ts = ts.strip()
    if ts in ("", "-1"):
        return None
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    dt = datetime.fromisoformat(ts)
    # Ensure UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def load_event_info(event_file):
    """
    Return dict with origin, lon, lat, depth, mag, mag_err from a .event CSV.
    """
    with open(event_file, "r", newline="") as f:
        reader = csv.DictReader(f)
        row = next(reader)

    origin = parse_iso_z(row["DT"])
    if origin is None:
        raise ValueError(f"No valid DT in {event_file}")

    lon = float(row["X"])
    lat = float(row["Y"])
    depth = float(row["Z"])

    # Magnitude
    mag = 0.0
    if "ML" in row and row["ML"].strip() not in ("", "-1"):
        try:
            mag = float(row["ML"])
        except ValueError:
            mag = 0.0

    # Magnitude uncertainty (mag var)
    mag_err = 0.0
    if "ML_Err" in row and row["ML_Err"].strip() not in ("", "-1"):
        try:
            mag_err = float(row["ML_Err"])
        except ValueError:
            mag_err = 0.0

    return {
        "origin": origin,
        "lon": lon,
        "lat": lat,
        "depth": depth,
        "mag": mag,
        "mag_err": mag_err,
    }


def load_stations(station_file):
    """
    Load station lat/lon from CSV with columns:
    Latitude,Longitude,Elevation,Name

    Returns dict: {station_name: (lat, lon)}
    """
    stations = {}
    with open(station_file, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row["Name"].strip()
            lat = float(row["Latitude"])
            lon = float(row["Longitude"])
            stations[name] = (lat, lon)
    return stations


def bearing_deg(lat1, lon1, lat2, lon2):
    """Azimuth (station) from (lat1,lon1) to (lat2,lon2) in degrees [0, 360)."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dlon = math.radians(lon2 - lon1)

    x = math.sin(dlon) * math.cos(phi2)
    y = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlon)
    az = math.atan2(x, y)
    deg = math.degrees(az)
    return (deg + 360.0) % 360.0


def compute_station_gap(azimuths):
    """
    Compute azimuthal gap (degrees) from a list of azimuths [0,360).
    """
    if not azimuths:
        return 360.0
    if len(azimuths) == 1:
        return 360.0

    az_sorted = sorted(azimuths)
    gaps = []
    for i in range(len(az_sorted) - 1):
        gaps.append(az_sorted[i + 1] - az_sorted[i])
    # Wrap-around gap
    gaps.append((az_sorted[0] + 360.0) - az_sorted[-1])

    return max(gaps)


def iter_picks(picks_file, origin, event_lat, event_lon, station_coords):
    """
    Yield pick dicts:

    {
      "network": "4W",
      "station": str,
      "phase": "P"/"S",
      "pick_dt": datetime,
      "tt_rel": float (sec since origin),
      "tt_abs": float (sec since midnight) [computed later],
      "amp_mm": float,
      "resid": float,
      "weight": float,
      "azimuth": float or None
    }
    """
    with open(picks_file, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pick_time_str = row["PickTime"].strip()
            if pick_time_str == "-1":
                continue

            station = row["Station"].strip()
            phase = row["Phase"].strip().upper()
            if phase not in {"P", "S"}:
                continue

            pick_dt = parse_iso_z(pick_time_str)
            if pick_dt is None:
                continue

            # Travel time relative to origin
            tt_rel = (pick_dt - origin).total_seconds()
            if tt_rel <= 0:
                # Non-physical / bad
                continue

            # Residual
            try:
                resid = float(row["Residual"])
            except Exception:
                resid = 0.0

            # Weight from PickError
            try:
                perr = float(row["PickError"])
                w = 1.0 - perr
                if w > 1.0:
                    w = 1.0
                if w < 0.1:
                    w = 0.1
            except Exception:
                w = 1.0

            # Amplitude in mm: not in QuakeMigrate files → 0.0 placeholder
            amp_mm = 0.0

            # Azimuth
            az = None
            if station in station_coords:
                st_lat, st_lon = station_coords[station]
                az = bearing_deg(event_lat, event_lon, st_lat, st_lon)

            yield {
                "network": "4W",  # adjust if you later want per-station networks
                "station": station,
                "phase": phase,
                "pick_dt": pick_dt,
                "tt_rel": tt_rel,
                "amp_mm": amp_mm,
                "resid": resid,
                "weight": w,
                "azimuth": az,
            }


# ----------------- Formatting ----------------- #

def format_event_line(num, origin, origin_rel_zero, lon, lat, depth,
                      mag, mag_err, picks, station_gap):
    """
    Event line in EXACT REAL/hypoinverse phase_sel format, matching 20230410.phase_sel.txt.

    Columns (based on the example):
      0-4   : event number (right-aligned, width 5)
      8-11  : year (4d)
      13-14 : month (2d)
      16-17 : day (2d)
      19-30 : time "hh:mm:ss.sss" (12 chars)
      35-43 : origin time rel ZERO (sec, f9.3)
      46-52 : RMS residual (f7.4)
      53-61 : lon (f9.4)
      62-70 : lat (f9.4)
      71-77 : depth (f7.2)
      78-83 : mag (f6.3)
      84-90 : mag var (f7.3)
      91-94 : Np (i4)
      95-98 : Ns (i4)
      99-102: Ntot (i4)
      103-105: Nboth (i3)
      106-   : station gap (f6.2)
    """

    year = origin.year
    month = origin.month
    day = origin.day
    hour = origin.hour
    minute = origin.minute
    sec = origin.second + origin.microsecond / 1e6

    # counts
    nP = sum(1 for p in picks if p["phase"] == "P")
    nS = sum(1 for p in picks if p["phase"] == "S")
    nTot = len(picks)

    # stations with both P and S
    phases_by_sta = defaultdict(set)
    for p in picks:
        phases_by_sta[p["station"]].add(p["phase"])
    nBoth = sum(1 for s, phs in phases_by_sta.items() if {"P", "S"}.issubset(phs))

    # RMS residual
    if picks:
        rms_resid = math.sqrt(sum(p["resid"] ** 2 for p in picks) / len(picks))
    else:
        rms_resid = 0.0

    # Build fixed-width char array
    # 112 is comfortably long enough for all fields
    line = [" "] * 112

    def put(s: str, start: int):
        line[start:start + len(s)] = s

    # event number at col 0, width 5
    put(f"{num:5d}", 0)
    # year, month, day
    put(f"{year:4d}", 8)
    put(f"{month:02d}", 13)
    put(f"{day:02d}", 16)
    # time hh:mm:ss.sss (length 12) at col 19
    put(f"{hour:02d}:{minute:02d}:{sec:06.3f}", 19)
    # origin rel ZERO (sec) at col 35, width 9, 3 decimals
    put(f"{origin_rel_zero:9.3f}", 35)
    # RMS residual at col 46, width 7, 4 decimals
    put(f"{rms_resid:7.4f}", 46)
    # lon/lat (deg) at 53, 62; width 9, 4 decimals
    put(f"{lon:9.4f}", 53)
    put(f"{lat:9.4f}", 62)
    # depth (km) at 71, width 7, 2 decimals
    put(f"{depth:7.2f}", 71)
    # magnitude and mag variance
    put(f"{mag:6.3f}", 78)
    put(f"{mag_err:7.3f}", 84)
    # counts
    put(f"{nP:4d}", 91)
    put(f"{nS:4d}", 95)
    put(f"{nTot:4d}", 99)
    put(f"{nBoth:3d}", 103)
    # station gap at 106, width 6, 2 decimals
    put(f"{station_gap:6.2f}", 106)

    return "".join(line).rstrip()


def format_phase_line(pick, tt_abs):
    """
    Phase line in EXACT REAL/hypoinverse format, matching 20230410.phase_sel.txt.

    From the example line:
        "   4W     2D07     P   18937.8600    1.8514 5.24e+04 -0.1563   0.9340 179.0916"

    Columns (0-based indices inferred):
      3-4   : network (2 chars)          (e.g., "4W")
      10-13 : station (4 chars)          (e.g., "2D07")
      19    : phase (1 char)             ("P" or "S")
      23-32 : abs travetime (f10.4)      (sec since ZERO)
      36-42 : rel travetime (f7.4)       (sec since origin)
      44-52 : amplitude (9 chars, 2.2e format) (mm)
      53-59 : residual (f7.4)
      63-68 : weight (f6.4)
      70-77 : azimuth (f8.4)
    """

    net = pick["network"]
    sta = pick["station"]
    ph = pick["phase"]
    tt_rel = pick["tt_rel"]
    amp_mm = pick["amp_mm"]
    resid = pick["resid"]
    weight = pick["weight"]
    az = pick["azimuth"] if pick["azimuth"] is not None else -999.0

    # Build fixed-width char array ~80 columns
    line = [" "] * 80

    def put(s: str, start: int):
        line[start:start + len(s)] = s

    # network: at col 3 (2 chars)
    put(f"{net:>2s}", 3)
    # station: at col 10 (4 chars right-aligned)
    put(f"{sta:>4s}", 10)
    # phase: at col 19
    put(f"{ph:1s}", 19)
    # abs travetime: at col 23, width 10, 4 decimals
    put(f"{tt_abs:10.4f}", 23)
    # rel travetime: at col 36, width 7, 4 decimals
    put(f"{tt_rel:7.4f}", 36)
    # amplitude in mm: scientific notation, width 9
    put(f"{amp_mm:9.2e}", 44)
    # residual: at col 53, width 7, 4 decimals
    put(f"{resid:7.4f}", 53)
    # weight: at col 63, width 6, 4 decimals
    put(f"{weight:6.4f}", 63)
    # azimuth: at col 70, width 8, 4 decimals
    put(f"{az:8.4f}", 70)

    return "".join(line).rstrip()


# ----------------- Main conversion ----------------- #

def event_counts_and_both(picks):
    """
    Compute Np, Ns, Ntot, Nboth given a list of picks.
    """
    nP = sum(1 for p in picks if p["phase"] == "P")
    nS = sum(1 for p in picks if p["phase"] == "S")
    nTot = len(picks)

    phases_by_sta = defaultdict(set)
    for p in picks:
        phases_by_sta[p["station"]].add(p["phase"])
    nBoth = sum(1 for s, phs in phases_by_sta.items() if {"P", "S"}.issubset(phs))

    return nP, nS, nTot, nBoth


def collect_events(runs_root: Path, station_coords):
    """
    Walk runs_root/0*/ and collect all events into a dict keyed by date.

    Applies filters:
      Np >= MIN_P_PICKS
      Ns >= MIN_S_PICKS
      Ntot >= MIN_TOTAL_PICKS
      Nboth >= MIN_STATIONS_WITH_BOTH

    Returns:
      events_by_date: {date: [event_dict, ...]}
    """
    events_by_date = defaultdict(list)

    runs = sorted(d for d in runs_root.glob("0*") if d.is_dir())
    if not runs:
        raise FileNotFoundError(f"No run directories starting with '0' in {runs_root}")

    for run_dir in runs:
        events_dir = run_dir / "locate" / "events"
        picks_dir = run_dir / "locate" / "picks"

        if not events_dir.is_dir() or not picks_dir.is_dir():
            print(f"[WARN] Missing events/picks in {run_dir}, skipping.", file=sys.stderr)
            continue

        event_files = sorted(events_dir.glob("*.event"))
        if not event_files:
            print(f"[WARN] No .event files in {events_dir}, skipping.", file=sys.stderr)
            continue

        print(f"[INFO] Processing run {run_dir.name} with {len(event_files)} events")

        for ev_file in event_files:
            stem = ev_file.stem
            picks_file = picks_dir / f"{stem}.picks"
            if not picks_file.exists():
                print(f"[WARN] No picks file for {ev_file.name}, skipping.", file=sys.stderr)
                continue

            try:
                einfo = load_event_info(ev_file)
            except Exception as e:
                print(f"[WARN] Failed to parse {ev_file}: {e}", file=sys.stderr)
                continue

            origin = einfo["origin"]
            lon = einfo["lon"]
            lat = einfo["lat"]
            depth = einfo["depth"]

            picks = list(iter_picks(picks_file, origin, lat, lon, station_coords))
            if not picks:
                print(f"[WARN] No valid picks for {ev_file.name}, skipping.", file=sys.stderr)
                continue

            # ---- NEW FILTER BLOCK: apply Np/Ns/Ntot/Nboth thresholds ---- #
            nP, nS, nTot, nBoth = event_counts_and_both(picks)
            if (
                nP < MIN_P_PICKS
                or nS < MIN_S_PICKS
                or nTot < MIN_TOTAL_PICKS
                or nBoth < MIN_STATIONS_WITH_BOTH
            ):
                print(
                    f"[INFO] Skipping event {ev_file.name}: "
                    f"Np={nP}, Ns={nS}, Ntot={nTot}, Nboth={nBoth}",
                    file=sys.stderr,
                )
                continue
            # -------------------------------------------------------------- #

            # Unique station azimuths for gap
            az_by_sta = {}
            for p in picks:
                if p["azimuth"] is not None:
                    az_by_sta[p["station"]] = p["azimuth"]
            gap = compute_station_gap(list(az_by_sta.values()))

            events_by_date[origin.date()].append({
                "origin": origin,
                "lon": lon,
                "lat": lat,
                "depth": depth,
                "mag": einfo["mag"],
                "mag_err": einfo["mag_err"],
                "picks": picks,
                "gap": gap,
            })

    return events_by_date


def write_phase_sel_files(events_by_date, out_dir: Path):
    """
    For each date, write YYYYMMDD.phase_sel.txt in out_dir.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    for date, events in sorted(events_by_date.items(), key=lambda kv: kv[0]):
        # Sort events of the day by origin time
        events.sort(key=lambda e: e["origin"])
        out_fn = out_dir / f"{date:%Y%m%d}.phase_sel.txt"
        print(f"[INFO] Writing {out_fn} with {len(events)} events")

        # ZERO = midnight of that day (UTC)
        zero = datetime(date.year, date.month, date.day, tzinfo=timezone.utc)

        with open(out_fn, "w") as f:
            for i, ev in enumerate(events, start=1):
                origin = ev["origin"]
                lon = ev["lon"]
                lat = ev["lat"]
                depth = ev["depth"]
                mag = ev["mag"]
                mag_err = ev["mag_err"]
                picks = ev["picks"]
                gap = ev["gap"]

                origin_rel_zero = (origin - zero).total_seconds()

                # Event header line
                ev_line = format_event_line(
                    i, origin, origin_rel_zero, lon, lat, depth,
                    mag, mag_err, picks, gap
                )
                f.write(ev_line + "\n")

                # Phase lines
                for p in picks:
                    tt_abs = (p["pick_dt"] - zero).total_seconds()
                    ph_line = format_phase_line(p, tt_abs)
                    f.write(ph_line + "\n")


def main():
    default_runs_root = Path("/project2/okaya_201/QuakeMigrate/outputs/runs")
    default_station_file = Path("/project2/okaya_201/QuakeMigrate/inputs/all_stations.txt")
    default_out_dir = Path("/project2/okaya_201/LOC-FLOW/Pick/QMigrate")

    parser = argparse.ArgumentParser(
        description="Create daily [date].phase_sel.txt files from QuakeMigrate .event/.picks outputs."
    )
    parser.add_argument(
        "--runs-root",
        type=Path,
        default=default_runs_root,
        help=f"Root of runs (default: {default_runs_root})",
    )
    parser.add_argument(
        "--station-file",
        type=Path,
        default=default_station_file,
        help=f"Station file CSV (default: {default_station_file})",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=default_out_dir,
        help=f"Output directory for phase_sel files (default: {default_out_dir})",
    )

    args = parser.parse_args()

    stations = load_stations(args.station_file)
    events_by_date = collect_events(args.runs_root, stations)
    write_phase_sel_files(events_by_date, args.out_dir)


if __name__ == "__main__":
    main()
