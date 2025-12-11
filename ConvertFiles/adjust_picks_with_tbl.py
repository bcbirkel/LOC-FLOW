#!/usr/bin/env python3
#
# Adjusts pick times from hypoDD.pha files based on origin time shifts
# from hypoDD.reloc (.tbl) catalogs.
#
import os
import datetime

# --- CONFIGURATION ---
PICKER_MAP = {
    'STALTA': 'sl',
    'PhaseNet': 'pn',
    'QMigrate': 'qm'
}
BASE_DIR_PHA = '../hypoDD_dtct'
BASE_DIR_TBL = './'
OUTPUT_DIR = './Picks'
# --- END CONFIGURATION ---

def load_tbl_origins(tbl_path):
    """Loads origin times from a .tbl file into a dict keyed by event ID."""
    origins = {}
    with open(tbl_path, 'r') as f:
        for line in f:
            parts = line.split()
            # eqID, year, julian day, month, day, hour, min, sec, ...
            eqID = int(parts[0])
            year = int(parts[1])
            month = int(parts[3])
            day = int(parts[4])
            hour = int(parts[5])
            minute = int(parts[6])
            sec_float = float(parts[7])
            microsecond = int((sec_float - int(sec_float)) * 1_000_000)

            origins[eqID] = datetime.datetime(
                year, month, day, hour, minute, int(sec_float), microsecond
            )
    return origins

def write_picks_file(eqID, picks, picker_short, output_dir):
    """Writes picks for a single event to a .picks file."""
    filename = f"{picker_short}.{eqID:03d}.picks"
    filepath = os.path.join(output_dir, filename)

    with open(filepath, 'w') as f:
        for station, phase, pick_time in picks:
            f.write(f"{station} {phase} {pick_time:.4f}\n")

def process_pha_file(pha_path, tbl_origins, picker_short, output_dir):
    """Processes a hypoDD.pha file, adjusts pick times, and writes .picks files."""
    current_event_picks = []
    current_event_id = None
    origin_diff_sec = None

    with open(pha_path, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            # Event header line
            if line.startswith('#'):
                # Write out the previous event's data before processing the new one
                if current_event_id is not None and origin_diff_sec is not None and current_event_picks:
                    write_picks_file(current_event_id, current_event_picks, picker_short, output_dir)

                # Reset for the new event
                current_event_picks = []
                current_event_id = None
                origin_diff_sec = None

                # Parse new header
                parts = line.split()
                # Format: # year month day hour minute second lat lon depth a b c d eqID
                if len(parts) < 15: continue

                eqID = int(parts[14])
                year = int(parts[1])
                month = int(parts[2])
                day = int(parts[3])
                hour = int(parts[4])
                minute = int(parts[5])
                sec_float = float(parts[6])
                microsecond = int((sec_float - int(sec_float)) * 1_000_000)

                pha_origin = datetime.datetime(
                    year, month, day, hour, minute, int(sec_float), microsecond
                )

                if eqID in tbl_origins:
                    current_event_id = eqID
                    tbl_origin = tbl_origins[eqID]
                    origin_diff = tbl_origin - pha_origin
                    origin_diff_sec = origin_diff.total_seconds()
                else:
                    print(f"Warning: Event ID {eqID} from {pha_path} not in .tbl catalog. Skipping.")

            # Phase pick line
            elif current_event_id is not None and origin_diff_sec is not None:
                parts = line.split()
                # Format: station pickTime weight phase
                if len(parts) < 4: continue

                station = parts[0]
                pha_pick_time = float(parts[1])
                phase = parts[3]

                adjusted_pick_time = pha_pick_time - origin_diff_sec
                current_event_picks.append((station, phase, adjusted_pick_time))

    # Write the very last event in the file after the loop finishes
    if current_event_id is not None and origin_diff_sec is not None and current_event_picks:
        write_picks_file(current_event_id, current_event_picks, picker_short, output_dir)


def main():
    """Main function to drive the pick adjustment process."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Output will be saved in: {os.path.abspath(OUTPUT_DIR)}")

    for picker, picker_short in PICKER_MAP.items():
        tbl_file = os.path.join(BASE_DIR_TBL, f'{picker}.hypoDD.tbl')
        pha_file = os.path.join(BASE_DIR_PHA, picker, 'hypoDD.pha')

        if not os.path.exists(tbl_file):
            print(f"Warning: TBL file not found, skipping {picker}: {tbl_file}")
            continue
        if not os.path.exists(pha_file):
            print(f"Warning: PHA file not found, skipping {picker}: {pha_file}")
            continue

        print(f"Processing picker: {picker}")
        # 1. Load origin times from the relocated .tbl catalog
        tbl_origins = load_tbl_origins(tbl_file)

        # 2. Process the .pha file to adjust picks and write output files
        process_pha_file(pha_file, tbl_origins, picker_short, OUTPUT_DIR)
        print(f"  -> Finished processing {picker}.")

if __name__ == '__main__':
    main()
