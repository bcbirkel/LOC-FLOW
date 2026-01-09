#!/usr/bin/env python3

import os
import itertools
from datetime import datetime, timedelta

import matplotlib.pyplot as plt
from obspy.geodetics import gps2dist_azimuth

def load_catalog_data(tbl_path):
    """Loads event data from a .tbl catalog file into a list of dictionaries."""
    events = []
    try:
        with open(tbl_path, 'r') as f:
            for line in f:
                parts = line.split()
                # eqID, year, jday, month, day, hour, min, sec, lon, lat, depth, mag, ...
                if len(parts) < 12:
                    continue
                try:
                    sec_float = float(parts[7])
                    event = {
                        'id': parts[0],
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
                    }
                    events.append(event)
                except (ValueError, IndexError) as e:
                    print(f"Warning: Could not parse line in {tbl_path}: {line.strip()}. Error: {e}")
    except FileNotFoundError:
        print(f"Error: Catalog file not found at {tbl_path}")
    return events

def find_common_events(cat1, cat2, time_window_s, dist_window_km):
    """
    Finds all pairs of common events between two catalogs based on origin time and location.
    This uses a sliding window approach for robustness.
    """
    cat1_sorted = sorted(cat1, key=lambda e: e['origin'])
    cat2_sorted = sorted(cat2, key=lambda e: e['origin'])

    common_events = []
    time_window = timedelta(seconds=time_window_s)
    dist_window_m = dist_window_km * 1000.0

    j_start = 0
    for event1 in cat1_sorted:
        # Advance j_start to the beginning of the possible match window for event1
        while j_start < len(cat2_sorted) and cat2_sorted[j_start]['origin'] < event1['origin'] - time_window:
            j_start += 1

        # Iterate through cat2 events within the time window of event1
        j = j_start
        while j < len(cat2_sorted) and cat2_sorted[j]['origin'] <= event1['origin'] + time_window:
            event2 = cat2_sorted[j]

            # Check distance for events inside the time window
            dist_m, _, _ = gps2dist_azimuth(event1['lat'], event1['lon'], event2['lat'], event2['lon'])
            if dist_m <= dist_window_m:
                common_events.append((event1, event2))
            
            j += 1

    return common_events

def plot_and_save_overlaps(common_events, time_s, dist_km, output_dir):
    """Generates plots and text files for a set of overlapping events."""
    if not common_events:
        print(f"No common events for T={time_s}s, D={dist_km}km. Skipping.")
        return

    print(f"Found {len(common_events)} common events for T={time_s}s, D={dist_km}km.")
    
    phasenet_events = [pair[0] for pair in common_events]
    qmigrate_events = [pair[1] for pair in common_events]
    
    list_filename = os.path.join(output_dir, f"overlap_T{time_s}s_D{dist_km}km.txt")
    with open(list_filename, 'w') as f:
        f.write("# Overlapping Event IDs (PhaseNet_ID, QMigrate_ID)\n")
        for pn_event, qm_event in common_events:
            f.write(f"{pn_event['id']}, {qm_event['id']}\n")

    fig, axes = plt.subplots(1, 3, figsize=(20, 6))
    title = f'Overlapping Events (T <= {time_s}s, D <= {dist_km}km) - {len(common_events)} pairs'
    fig.suptitle(title, fontsize=16)

    ax1 = axes[0]
    ax1.scatter([e['lon'] for e in phasenet_events], [e['lat'] for e in phasenet_events],
                marker='o', label='PhaseNet', alpha=0.7, zorder=10)
    ax1.scatter([e['lon'] for e in qmigrate_events], [e['lat'] for e in qmigrate_events],
                marker='x', label='QMigrate', alpha=0.7, zorder=10)
    
    for pn_event, qm_event in common_events:
        ax1.plot([pn_event['lon'], qm_event['lon']], [pn_event['lat'], qm_event['lat']], 'k-', alpha=0.3)

    ax1.set_xlabel('Longitude')
    ax1.set_ylabel('Latitude')
    ax1.set_title('Map View')
    ax1.legend()
    ax1.grid(True)
    ax1.set_aspect('equal', adjustable='box')

    ax2 = axes[1]
    ax2.scatter([e['lon'] for e in phasenet_events], [e['depth'] for e in phasenet_events],
                marker='o', label='PhaseNet', alpha=0.7)
    ax2.scatter([e['lon'] for e in qmigrate_events], [e['depth'] for e in qmigrate_events],
                marker='x', label='QMigrate', alpha=0.7)
    for pn_event, qm_event in common_events:
        ax2.plot([pn_event['lon'], qm_event['lon']], [pn_event['depth'], qm_event['depth']], 'k-', alpha=0.3)
    ax2.set_xlabel('Longitude')
    ax2.set_ylabel('Depth (km)')
    ax2.set_title('Lon vs Depth')
    ax2.invert_yaxis()
    ax2.grid(True)
    ax2.legend()
    
    ax3 = axes[2]
    ax3.scatter([e['lat'] for e in phasenet_events], [e['depth'] for e in phasenet_events],
                marker='o', label='PhaseNet', alpha=0.7)
    ax3.scatter([e['lat'] for e in qmigrate_events], [e['depth'] for e in qmigrate_events],
                marker='x', label='QMigrate', alpha=0.7)
    for pn_event, qm_event in common_events:
        ax3.plot([pn_event['lat'], qm_event['lat']], [pn_event['depth'], qm_event['depth']], 'k-', alpha=0.3)
    ax3.set_xlabel('Latitude')
    ax3.set_ylabel('Depth (km)')
    ax3.set_title('Lat vs Depth')
    ax3.invert_yaxis()
    ax3.grid(True)
    ax3.legend()

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plot_filename = os.path.join(output_dir, f"overlap_T{time_s}s_D{dist_km}km.png")
    plt.savefig(plot_filename, dpi=300)
    plt.close(fig)
    print(f"Saved plot to {plot_filename} and list to {list_filename}")


def main():
    """Main function to find, plot, and save overlapping events for different parameters."""
    phasenet_catalog_file = 'ConvertFiles/PhaseNet.hypoDD.tbl'
    qmigrate_catalog_file = 'ConvertFiles/QMigrate.hypoDD.tbl'
    output_dir = 'overlapping_events'
    
    os.makedirs(output_dir, exist_ok=True)
    
    print("Loading catalog data...")
    phasenet_events = load_catalog_data(phasenet_catalog_file)
    qmigrate_events = load_catalog_data(qmigrate_catalog_file)
    
    if not phasenet_events or not qmigrate_events:
        print("Could not load one or both catalogs. Aborting.")
        return
        
    time_windows_s = [10, 30, 60]
    dist_windows_km = [0.1, 0.5, 1.0]
    
    param_grid = list(itertools.product(time_windows_s, dist_windows_km))
    
    for time_s, dist_km in param_grid:
        print(f"\n--- Processing T={time_s}s, D={dist_km}km ---")
        common_events = find_common_events(phasenet_events, qmigrate_events, time_window_s=time_s, dist_window_km=dist_km)
        plot_and_save_overlaps(common_events, time_s, dist_km, output_dir)
        
    print("\nProcessing complete.")

if __name__ == '__main__':
    main()
