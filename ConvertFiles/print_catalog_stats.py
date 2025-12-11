#!/usr/bin/env python3
#
# Reads .tbl catalog files and prints summary statistics for each.
#
import os
import numpy as np
from datetime import datetime

# --- CONFIGURATION ---
PICKERS = ['STALTA', 'PhaseNet', 'QMigrate']
BASE_DIR_TBL = './'
# --- END CONFIGURATION ---

def load_catalog_data(tbl_path):
    """Loads numeric data and dates from a .tbl catalog file."""
    # Columns to load: lon, lat, depth, mag, err_NS, err_EW, err_Z
    numeric_data = []
    dates = []
    with open(tbl_path, 'r') as f:
        for line in f:
            parts = line.split()
            # eqID, year, julian, month, day, hour, min, sec, lon, lat, depth, mag, err_NS, err_EW, err_Z
            #   0     1       2      3     4     5     6    7    8    9     10    11    12      13      14
            if len(parts) < 15:
                continue

            try:
                # Parse date and time
                year = int(parts[1])
                month = int(parts[3])
                day = int(parts[4])
                hour = int(parts[5])
                minute = int(parts[6])
                sec_float = float(parts[7])
                second = int(sec_float)
                microsecond = int((sec_float - second) * 1_000_000)
                dates.append(datetime(year, month, day, hour, minute, second, microsecond))

                # Parse numeric columns from longitude onwards
                numeric_data.append([float(p) for p in parts[8:]])
            except (ValueError, IndexError) as e:
                print(f"Warning: Could not parse line in {tbl_path}: {line.strip()}. Error: {e}")
    
    return np.array(numeric_data), dates

def print_stats(picker_name, data, dates):
    """Calculates and prints statistics for a loaded catalog."""
    print(f"\n--- Statistics for {picker_name} ---")

    num_events = len(dates)
    print(f"Total Events: {num_events}")

    if num_events == 0:
        return

    print(f"Date Range:   {min(dates).strftime('%Y-%m-%d')} to {max(dates).strftime('%Y-%m-%d')}")

    # Data columns (from index 8 of original file):
    # lon, lat, depth, mag, err_NS, err_EW, err_Z
    #   0,   1,     2,   3,      4,      5,      6
    lon = data[:, 0]
    lat = data[:, 1]
    depth = data[:, 2]
    mag = data[:, 3]
    err_ns = data[:, 4]
    err_ew = data[:, 5]
    err_z = data[:, 6]

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


def main():
    """Main function to find and process all .tbl files."""
    for picker in PICKERS:
        tbl_file = os.path.join(BASE_DIR_TBL, f'{picker}.hypoDD.tbl')
        if not os.path.exists(tbl_file):
            print(f"\nWarning: TBL file not found for {picker}, skipping: {tbl_file}")
            continue

        try:
            data, dates = load_catalog_data(tbl_file)
            print_stats(picker, data, dates)
        except Exception as e:
            print(f"Error processing {tbl_file}: {e}")

if __name__ == '__main__':
    main()
