#!/usr/bin/env python3
"""
Select one "best" event per day based on station gap from daily phase_sel files,
and copy the corresponding event (header + phases) from the all-days phase file
into a new file: phase_best_allday.txt.

Inputs (defaults):
  --phase-all   /project2/okaya_201/LOC-FLOW/Pick/QMigrate/phase_qmigrate.dat
  --phase-sel-dir
                /project2/okaya_201/LOC-FLOW/Pick/QMigrate
  --out-file    /project2/okaya_201/LOC-FLOW/Pick/QMigrate/phase_best_allday.txt

Assumptions:

1) Daily phase_sel files look like the attached examples, e.g.:

       1   2023 04 10 05:15:36.009    18936.009  0.2331 85.5277  27.9349  10.00  6.447 0.278  15  24  39  24 182.61
      4W      2D01   P   18945.993    9.9841  0.00e+00   0.0000   1.0000   6.3194
      ...

   We treat the first line as an event header. Columns (split by whitespace) are:

     0: event index (integer)
     1: year (YYYY)
     2: month (MM)
     3: day (DD)
     4: time "HH:MM:SS.sss"
     ...
    -1: station gap (last column, float)

2) The all-days file phase_qmigrate.dat looks like:

   #  2023  04  10   11    32   18.215     85.5467   27.9393   9.43904  4.39265 0.146484 0.        0.        0.           6
     4W      2D01   P  41538.228    9. , ...

   Where each event begins with a line starting with '#'.
   Tokens are:

     "#" year month day hour minute second lon lat depth mag mag_err ...

We match events between phase_sel and phase_qmigrate.dat by:

  key = (year, month, day, hour, minute, round(second, 3))

and copy the matching event chunk into phase_best_allday.txt.
"""

import argparse
from pathlib import Path
import re
from datetime import date
import sys


# Regex to detect an event header line in phase_sel files
# Example matched line (with leading spaces):
# "    1   2023 04 10 05:15:36.009    18936.009  0.2331 ..."
PHASE_SEL_HEADER_RE = re.compile(
    r"^\s*\d+\s+(\d{4})\s+(\d{2})\s+(\d{2})\s+(\d{2}):(\d{2}):(\d{2}\.\d{3})"
)


def parse_best_events_from_phase_sel(phase_sel_dir: Path):
    """
    Scan all daily phase_sel files in the directory, find the event
    with the smallest station gap for each date.

    Returns:
        best_by_date: dict[date] = {
            "key": (year, month, day, hour, minute, sec_3dec),
            "gap": float,
            "line": original_header_line_str,
        }
    """
    best_by_date = {}

    # Accept files like YYYYMMDD.phase_sel.txt or YYYYMMDD.phase_sel
    candidates = sorted(
        list(phase_sel_dir.glob("*.phase_sel.txt")) +
        list(phase_sel_dir.glob("*.phase_sel"))
    )

    if not candidates:
        print(f"[ERROR] No phase_sel files found in {phase_sel_dir}", file=sys.stderr)
        return best_by_date

    print(f"[INFO] Found {len(candidates)} phase_sel files to scan in {phase_sel_dir}")

    for path in candidates:
        with path.open("r") as f:
            for line in f:
                m = PHASE_SEL_HEADER_RE.match(line)
                if not m:
                    continue

                year_s, month_s, day_s, hh_s, mm_s, ss_s = m.groups()
                year = int(year_s)
                month = int(month_s)
                day_int = int(day_s)
                hh = int(hh_s)
                mm = int(mm_s)
                sec_float = float(ss_s)
                sec_3dec = round(sec_float, 3)

                parts = line.split()
                try:
                    gap = float(parts[-1])
                except Exception:
                    # If something goes wrong parsing gap, skip this event
                    print(
                        f"[WARN] Could not parse station gap from line in {path.name}: {line.strip()}",
                        file=sys.stderr,
                    )
                    continue

                d = date(year, month, day_int)
                key = (year, month, day_int, hh, mm, sec_3dec)

                rec = {
                    "key": key,
                    "gap": gap,
                    "line": line.rstrip("\n"),
                }

                if d not in best_by_date or gap < best_by_date[d]["gap"]:
                    best_by_date[d] = rec

    print(f"[INFO] Found best events for {len(best_by_date)} days from phase_sel files.")
    return best_by_date


def parse_all_days_phase_file(phase_all_path: Path):
    """
    Parse the all-days phase file (e.g., phase_qmigrate.dat).

    Build a mapping:
        key = (year, month, day, hour, minute, sec_3dec)
        value = list of lines (header + all its phase lines)

    Returns:
        events_by_key: dict[key] = [lines...]
    """
    events_by_key = {}

    if not phase_all_path.exists():
        print(f"[ERROR] All-days phase file not found: {phase_all_path}", file=sys.stderr)
        return events_by_key

    with phase_all_path.open("r") as f:
        current_key = None
        current_lines = []

        for line in f:
            if line.startswith("#"):
                # New event header
                # Flush previous
                if current_key is not None:
                    events_by_key[current_key] = current_lines

                # Parse new header
                # Example:
                # "#  2023  04  10   11    32   18.215     85.5467 ..."
                parts = line[1:].split()
                if len(parts) < 6:
                    print(
                        f"[WARN] Unexpected header format in all-days file: {line.strip()}",
                        file=sys.stderr,
                    )
                    current_key = None
                    current_lines = [line]
                    continue

                try:
                    year = int(parts[0])
                    month = int(parts[1])
                    day_int = int(parts[2])
                    hh = int(parts[3])
                    mm = int(parts[4])
                    sec = float(parts[5])
                except Exception:
                    print(
                        f"[WARN] Failed to parse date/time from header: {line.strip()}",
                        file=sys.stderr,
                    )
                    current_key = None
                    current_lines = [line]
                    continue

                sec_3dec = round(sec, 3)
                current_key = (year, month, day_int, hh, mm, sec_3dec)
                current_lines = [line]  # include the header itself

            else:
                # Phase line or something else; just append to current chunk
                if current_key is not None:
                    current_lines.append(line)

        # Flush last event
        if current_key is not None:
            events_by_key[current_key] = current_lines

    print(f"[INFO] Parsed {len(events_by_key)} events from {phase_all_path.name}")
    return events_by_key


def write_best_events(best_by_date, events_by_key, out_path: Path):
    """
    For each date in best_by_date, take the matching event from events_by_key and
    write it verbatim to out_path.

    Prints warnings for any missing events.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)

    missing = []

    with out_path.open("w") as out_f:
        for d in sorted(best_by_date.keys()):
            rec = best_by_date[d]
            key = rec["key"]

            if key not in events_by_key:
                # If not found, we warn and continue
                year, month, day_int, hh, mm, sec = key
                missing.append(
                    f"{year:04d}-{month:02d}-{day_int:02d} "
                    f"{hh:02d}:{mm:02d}:{sec:06.3f}"
                )
                continue

            lines = events_by_key[key]
            for line in lines:
                out_f.write(line)

    if missing:
        print(
            "[WARN] Some best events were not found in the all-days phase file:",
            file=sys.stderr,
        )
        for m in missing:
            print(f"  Missing event {m}", file=sys.stderr)
    else:
        print("[INFO] All best events successfully matched and written.")

    print(f"[INFO] Wrote best events to {out_path}")


def main():
    default_phase_all = Path("/project2/okaya_201/LOC-FLOW/Pick/QMigrate/phase_qmigrate.dat")
    default_phase_sel_dir = Path("/project2/okaya_201/LOC-FLOW/Pick/QMigrate")
    default_out_file = default_phase_sel_dir / "phase_best_allday.txt"

    parser = argparse.ArgumentParser(
        description=(
            "Create phase_best_allday.txt by selecting one event per day with "
            "the smallest station gap from daily phase_sel files and copying "
            "the corresponding event from the all-days phase file."
        )
    )
    parser.add_argument(
        "--phase-all",
        type=Path,
        default=default_phase_all,
        help=f"All-days phase file (default: {default_phase_all})",
    )
    parser.add_argument(
        "--phase-sel-dir",
        type=Path,
        default=default_phase_sel_dir,
        help=f"Directory containing daily phase_sel files (default: {default_phase_sel_dir})",
    )
    parser.add_argument(
        "--out-file",
        type=Path,
        default=default_out_file,
        help=f"Output file (default: {default_out_file})",
    )

    args = parser.parse_args()

    best_by_date = parse_best_events_from_phase_sel(args.phase_sel_dir)
    if not best_by_date:
        print("[ERROR] No best events found; aborting.", file=sys.stderr)
        sys.exit(1)

    events_by_key = parse_all_days_phase_file(args.phase_all)
    if not events_by_key:
        print("[ERROR] No events found in all-days phase file; aborting.", file=sys.stderr)
        sys.exit(1)

    write_best_events(best_by_date, events_by_key, args.out_file)


if __name__ == "__main__":
    main()
