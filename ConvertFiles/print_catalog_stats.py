#!/usr/bin/env python3
#
# Reads .tbl catalog files and prints summary statistics for each.
#
import os
import glob
import itertools
import numpy as np
from datetime import datetime
from obspy.geodetics import gps2dist_azimuth

# --- CONFIGURATION ---
PICKERS = ['STALTA', 'PhaseNet', 'QMigrate']
PICKER_MAP = {
    'STALTA': 'sl',
    'PhaseNet': 'pn',
    'QMigrate': 'qm'
}
BASE_DIR_TBL = './'
BASE_DIR_PICKS = './Picks'
STATION_FILE_PATH = '../Data/station_filt.dat'
# --- END CONFIGURATION ---

def load_catalog_data(tbl_path):
    """Loads event data from a .tbl catalog file into a list of dictionaries."""
    events = []
    with open(tbl_path, 'r') as f:
        for line in f:
            parts = line.split()
            # eqID, year, julian, month, day, hour, min, sec, lon, lat, depth, mag, err_NS, err_EW, err_Z
            if len(parts) < 15:
                continue

            try:
                sec_float = float(parts[7])
                event = {
                    'id': int(parts[0]),
                    'origin': datetime(
                        year=int(parts[1]),
                        month=int(parts[3]),
                        day=int(parts[4]),
                        hour=int(parts[5]),
                        minute=int(parts[6]),
                        second=int(sec_float),
                        microsecond=int((sec_float - int(sec_float)) * 1_000_000)
                    ),
                    'lon': float(parts[8]),
                    'lat': float(parts[9]),
                    'depth': float(parts[10]),
                    'mag': float(parts[11]),
                    'err_ns': float(parts[12]),
                    'err_ew': float(parts[13]),
                    'err_z': float(parts[14]),
                }
                events.append(event)
            except (ValueError, IndexError) as e:
                print(f"Warning: Could not parse line in {tbl_path}: {line.strip()}. Error: {e}")
    
    return events

def load_station_count(station_file_path):
    """Counts the number of unique stations in the station file."""
    if not os.path.exists(station_file_path):
        print(f"Warning: Station file not found at {station_file_path}. Cannot calculate pick rates.")
        return 0
    with open(station_file_path, 'r') as f:
        # Assuming format: lat lon net station ...
        stations = set(line.split()[3] for line in f if len(line.split()) >= 4)
    return len(stations)

def calculate_pick_stats(picker_name, num_days, num_stations):
    """Calculates average P and S picks per station per day."""
    if num_days == 0 or num_stations == 0:
        return 0, 0

    picker_short = PICKER_MAP.get(picker_name)
    if not picker_short:
        return 0, 0

    picks_dir = os.path.join(BASE_DIR_PICKS, picker_name)
    pick_files = glob.glob(os.path.join(picks_dir, f'{picker_short}.*.picks'))

    p_count, s_count = 0, 0
    for pick_file in pick_files:
        with open(pick_file, 'r') as f:
            for line in f:
                if line.startswith('#'):
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    if parts[1].upper() == 'P':
                        p_count += 1
                    elif parts[1].upper() == 'S':
                        s_count += 1

    avg_p = p_count / num_stations / num_days if num_stations and num_days else 0
    avg_s = s_count / num_stations / num_days if num_stations and num_days else 0
    return avg_p, avg_s


def print_stats(picker_name, events, num_stations):
    """Calculates and prints statistics for a loaded catalog."""
    print(f"\n--- Statistics for {picker_name} ---")

    num_events = len(events)
    print(f"Total Events: {num_events}")

    if num_events == 0:
        return

    dates = [e['origin'] for e in events]
    min_date, max_date = min(dates), max(dates)
    num_days = (max_date - min_date).days + 1
    print(f"Date Range:   {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')} ({num_days} days)")

    lon = np.array([e['lon'] for e in events])
    lat = np.array([e['lat'] for e in events])
    depth = np.array([e['depth'] for e in events])
    mag = np.array([e['mag'] for e in events])
    err_ns = np.array([e['err_ns'] for e in events])
    err_ew = np.array([e['err_ew'] for e in events])
    err_z = np.array([e['err_z'] for e in events])

    print("\nLocation:")
    print(f"  Longitude:  {np.min(lon):.4f} to {np.max(lon):.4f}")
    print(f"  Latitude:   {np.min(lat):.4f} to {np.max(lat):.4f}")
    print(f"  Depth (km): {np.min(depth):.3f} to {np.max(depth):.3f} (Mean: {np.mean(depth):.3f})")

    print("\nMagnitude:")
    print(f"  Range: {np.min(mag):.2f} to {np.max(mag):.2f}")
    print(f"  Mean:  {np.mean(mag):.2f}, Median: {np.median(mag):.2f}")

    print("\nLocation Errors (km):")
    print(f"  North-South (err_NS): Mean={np.mean(err_ns):.4f}, Median={np.median(err_ns):.4f}, Std={np.std(err_ns):.4f}")
    print(f"  East-West (err_EW):   Mean={np.mean(err_ew):.4f}, Median={np.median(err_ew):.4f}, Std={np.std(err_ew):.4f}")
    print(f"  Vertical (err_Z):     Mean={np.mean(err_z):.4f}, Median={np.median(err_z):.4f}, Std={np.std(err_z):.4f}")

    avg_p, avg_s = calculate_pick_stats(picker_name, num_days, num_stations)
    print("\nPick Statistics:")
    print(f"  Avg P picks/station/day: {avg_p:.2f}")
    print(f"  Avg S picks/station/day: {avg_s:.2f}")


def find_common_events(cat1, cat2, time_window_s=10):
    """Finds common events between two catalogs based on origin time."""
    cat1_sorted = sorted(cat1, key=lambda e: e['origin'])
    cat2_sorted = sorted(cat2, key=lambda e: e['origin'])
    
    common_events = []
    i, j = 0, 0
    time_window = datetime.timedelta(seconds=time_window_s)
    
    while i < len(cat1_sorted) and j < len(cat2_sorted):
        event1 = cat1_sorted[i]
        event2 = cat2_sorted[j]
        
        time_diff = event1['origin'] - event2['origin']
        
        if abs(time_diff) <= time_window:
            common_events.append((event1, event2))
            i += 1
            j += 1
        elif time_diff < -time_window:
            i += 1
        else: # time_diff > time_window
            j += 1
            
    return common_events

def print_comparison_stats(picker1, picker2, common_events):
    """Calculates and prints statistics for common events between two catalogs."""
    print(f"\n--- Comparison: {picker1} vs {picker2} ---")
    
    if not common_events:
        print("  No common events found within time window.")
        return
        
    print(f"  Found {len(common_events)} common events.")

    dist_diffs = []
    depth_diffs = []
    err_ns_diffs = []
    err_ew_diffs = []
    err_z_diffs = []

    for e1, e2 in common_events:
        dist_m, _, _ = gps2dist_azimuth(e1['lat'], e1['lon'], e2['lat'], e2['lon'])
        dist_diffs.append(dist_m / 1000.0)
        depth_diffs.append(abs(e1['depth'] - e2['depth']))
        
        err_ns_diffs.append(abs(e1['err_ns'] - e2['err_ns']))
        err_ew_diffs.append(abs(e1['err_ew'] - e2['err_ew']))
        err_z_diffs.append(abs(e1['err_z'] - e2['err_z']))

    print("\n  Absolute Location Differences:")
    print(f"    Horizontal (km): Mean={np.mean(dist_diffs):.4f}, Median={np.median(dist_diffs):.4f}")
    print(f"    Vertical (km):   Mean={np.mean(depth_diffs):.4f}, Median={np.median(depth_diffs):.4f}")

    print("\n  Absolute Error Differences (km):")
    print(f"    err_NS: Mean={np.mean(err_ns_diffs):.4f}, Median={np.median(err_ns_diffs):.4f}")
    print(f"    err_EW: Mean={np.mean(err_ew_diffs):.4f}, Median={np.median(err_ew_diffs):.4f}")
    print(f"    err_Z:  Mean={np.mean(err_z_diffs):.4f}, Median={np.median(err_z_diffs):.4f}")


def main():
    """Main function to find, process, and compare all .tbl files."""
    num_stations = load_station_count(STATION_FILE_PATH)
    all_catalogs = {}

    for picker in PICKERS:
        tbl_file = os.path.join(BASE_DIR_TBL, f'{picker}.hypoDD.tbl')
        if not os.path.exists(tbl_file):
            print(f"\nWarning: TBL file not found for {picker}, skipping: {tbl_file}")
            continue
        try:
            all_catalogs[picker] = load_catalog_data(tbl_file)
        except Exception as e:
            print(f"Error processing {tbl_file}: {e}")

    # Print individual stats
    for picker, events in all_catalogs.items():
        print_stats(picker, events, num_stations)
    
    # Print comparison stats
    print("\n" + "="*50)
    print(" " * 15 + "CATALOG COMPARISONS")
    print("="*50)

    for picker1, picker2 in itertools.combinations(all_catalogs.keys(), 2):
        cat1 = all_catalogs[picker1]
        cat2 = all_catalogs[picker2]
        common_events = find_common_events(cat1, cat2)
        print_comparison_stats(picker1, picker2, common_events)


if __name__ == '__main__':
    main()
