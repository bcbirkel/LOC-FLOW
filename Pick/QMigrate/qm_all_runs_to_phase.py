#!/usr/bin/env python3
"""
Convert ALL QuakeMigrate .event/.picks files from runs/0*/ into a single
VELEST-style phase file.

Default behavior:
  - Scan: /project2/okaya_201/QuakeMigrate/outputs/runs/0*/
  - Write: /project2/okaya_201/LOC-FLOW/Pick/QMigrate/phase_qmigrate.dat

Usage (with defaults):
    python qm_all_runs_to_phase.py

Or override paths:
    python qm_all_runs_to_phase.py \
        --runs-root /project2/okaya_201/QuakeMigrate/outputs/runs \
        --outfile /project2/okaya_201/LOC-FLOW/Pick/QMigrate/phase_qmigrate.dat
"""

import csv
from pathlib import Path
from datetime import datetime
import argparse
import sys


# ---------- Parsing helpers ---------- #

def parse_iso_z(ts):
    """Parse ISO8601 with trailing 'Z' into a timezone-aware datetime."""
    if ts == "-1" or ts == "" or ts is None:
        return None
    ts = ts.strip()
    if ts.endswith("Z"):
        ts = ts[:-1] + "+00:00"
    return datetime.fromisoformat(ts)


def load_event_info(event_file):
    """Return (origin_time, lon, lat, depth, mag) from a .event CSV."""
    with open(event_file, "r", newline="") as f:
        reader = csv.DictReader(f)
        row = next(reader)

    origin = parse_iso_z(row["DT"])
    if origin is None:
        raise ValueError(f"No valid DT in {event_file}")

    lon = float(row["X"])
    lat = float(row["Y"])
    depth = float(row["Z"])

    # Magnitude: use ML if present, else 0.0
    mag = 0.0
    if "ML" in row and row["ML"].strip() not in ("", "-1"):
        try:
            mag = float(row["ML"])
        except ValueError:
            mag = 0.0

    return origin, lon, lat, depth, mag


def iter_picks(picks_file, origin):
    """
    Yield (station, travel_time_seconds, weight, phase) for each valid pick.
    """
    with open(picks_file, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pick_time_str = row["PickTime"].strip()
            if pick_time_str == "-1":
                # No pick for this station/phase
                continue

            station = row["Station"].strip()
            phase = row["Phase"].strip().upper()

            if phase not in {"P", "S"}:
                continue

            pt = parse_iso_z(pick_time_str)
            if pt is None:
                continue

            # Travel time in seconds relative to event origin
            tt = (pt - origin).total_seconds()

            # Drop non-physical/zero/negative travel times
            if tt <= 0:
                continue

            # Weight from PickError: w = 1 - PickError (clipped to [0.1, 1.0])
            try:
                perr = float(row["PickError"])
                w = 1.0 - perr
                if w > 1.0:
                    w = 1.0
                if w < 0.1:
                    w = 0.1
            except Exception:
                w = 1.0

            yield station, tt, w, phase


# ---------- Formatting ---------- #

def format_header(origin, lon, lat, depth, mag, ev_num):
    """
    Format event header line like:

    # 2023  04  10   05    15    36.009    85.5277    27.9349    10.00     6.447     0.0     0.0    0.0    1
    """
    year = origin.year
    month = origin.month
    day = origin.day
    hour = origin.hour
    minute = origin.minute
    sec = origin.second + origin.microsecond / 1e6

    return (
        f"# {year:4d}  {month:02d}  {day:02d}   "
        f"{hour:02d}    {minute:02d}   {sec:6.3f}    "
        f"{lon:8.4f}    {lat:8.4f}    {depth:5.2f}     "
        f"{mag:5.3f}     0.0     0.0    0.0    {ev_num}"
    )


def format_pick_line(station, tt, weight, phase):
    """
    Format a pick line like:

    2D07 1.8514 0.9340 P
    """
    return f"{station:<4s} {tt:6.4f} {weight:6.4f} {phase}"


# ---------- Core conversion ---------- #

def convert_single_run(run_dir: Path, out_f, start_event_number: int) -> int:
    """
    Convert all events/picks in a single run directory and append to open file.

    Parameters
    ----------
    run_dir : Path
        Directory like .../outputs/runs/0416
    out_f : file object
        Open file handle to write phase data.
    start_event_number : int
        Starting event number to label headers.

    Returns
    -------
    next_event_number : int
        Event number after the last one written.
    """
    events_dir = run_dir / "locate" / "events"
    picks_dir = run_dir / "locate" / "picks"

    if not events_dir.is_dir():
        print(f"[WARN] Events directory not found in {run_dir}, skipping.", file=sys.stderr)
        return start_event_number
    if not picks_dir.is_dir():
        print(f"[WARN] Picks directory not found in {run_dir}, skipping.", file=sys.stderr)
        return start_event_number

    event_files = sorted(events_dir.glob("*.event"))
    if not event_files:
        print(f"[WARN] No .event files in {events_dir}, skipping run.", file=sys.stderr)
        return start_event_number

    ev_num = start_event_number

    print(f"[INFO] Processing run: {run_dir.name}  ({len(event_files)} events)")
    for ev_file in event_files:
        stem = ev_file.stem
        picks_file = picks_dir / f"{stem}.picks"

        if not picks_file.exists():
            print(f"[WARN] No picks file for {ev_file.name}, skipping event.", file=sys.stderr)
            continue

        try:
            origin, lon, lat, depth, mag = load_event_info(ev_file)
        except Exception as e:
            print(f"[WARN] Failed to parse event file {ev_file}: {e}", file=sys.stderr)
            continue

        picks = list(iter_picks(picks_file, origin))
        if not picks:
            print(f"[WARN] No valid picks for {ev_file.name}, skipping event.", file=sys.stderr)
            continue

        header_line = format_header(origin, lon, lat, depth, mag, ev_num)
        out_f.write(header_line + "\n")
        for sta, tt, w, ph in picks:
            out_f.write(format_pick_line(sta, tt, w, ph) + "\n")

        ev_num += 1

    return ev_num


def convert_all_runs(runs_root: Path, outfile: Path):
    """
    Scan runs_root for directories starting with '0*', process them
    in sorted order, and write a combined phase file.
    """
    runs = sorted(d for d in runs_root.glob("0*") if d.is_dir())
    if not runs:
        raise FileNotFoundError(f"No run directories starting with '0' found in {runs_root}")

    outfile.parent.mkdir(parents=True, exist_ok=True)

    print(f"[INFO] Writing combined phase file to: {outfile}")
    print(f"[INFO] Found {len(runs)} runs under {runs_root}")

    ev_num = 1
    with open(outfile, "w") as out_f:
        for run_dir in runs:
            ev_num = convert_single_run(run_dir, out_f, ev_num)

    print(f"[INFO] Done. Total events written: {ev_num - 1}")


# ---------- CLI ---------- #

def main():
    default_runs_root = Path("/project2/okaya_201/QuakeMigrate/outputs/runs")
    default_outfile = Path("/project2/okaya_201/LOC-FLOW/Pick/QMigrate/phase_qmigrate.dat")

    parser = argparse.ArgumentParser(
        description="Convert all QuakeMigrate runs/0*/ .event/.picks files into a single VELEST-style phase file."
    )
    parser.add_argument(
        "--runs-root",
        type=Path,
        default=default_runs_root,
        help=f"Root directory containing run subdirs (default: {default_runs_root})",
    )
    parser.add_argument(
        "--outfile",
        type=Path,
        default=default_outfile,
        help=f"Output phase file path (default: {default_outfile})",
    )

    args = parser.parse_args()
    convert_all_runs(args.runs_root, args.outfile)


if __name__ == "__main__":
    main()
