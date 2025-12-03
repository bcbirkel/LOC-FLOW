#!/usr/bin/env python3
#
# Plot record sections for events on a specific day from a given catalog.
#
# Example usage:
# python plot_record_section.py 2016-10-14 QMigrate hypoDD_dtct
#

import argparse
import os
import glob
from datetime import datetime

import numpy as np
import matplotlib.pyplot as plt
from obspy import read, UTCDateTime
from obspy.geodetics import gps2dist_azimuth

# This dictionary is adapted from plot_3d.py to include origin time columns.
# It helps in locating catalog files and parsing them.
# NOTE: lon/lat for hypoDD is swapped compared to plot_3d.py to match standard format.
STAGE_DATA_DEFINITIONS = {
    'Initial': {
        'STALTA': {
            'path': '../REAL/catalogSA_allday.txt',
            'cols': {'lon': 6, 'lat': 7, 'dep': 8, 'yr': 1, 'mo': 2, 'dy': 3, 'hr': 4, 'mi': 5, 'sc': 5, 'id': 0},
        },
        'PhaseNet': {
            'path': '../REAL/runs/PhaseNet/catalogSA_allday.txt',
            'cols': {'lon': 6, 'lat': 7, 'dep': 8, 'yr': 1, 'mo': 2, 'dy': 3, 'hr': 4, 'mi': 5, 'sc': 5, 'id': 0},
        },
    },
    'hypoDD_dtct': {
        'path_template': '../hypoDD_dtct/{picker}/hypoDD.reloc',
        'cols': {'lat': 2, 'lon': 1, 'dep': 3, 'yr': 10, 'mo': 11, 'dy': 12, 'hr': 13, 'mi': 14, 'sc': 15, 'id': 0},
    },
    # Add other stages here if needed, with their column definitions
}

WAVEFORM_DIR = '../Data/waveform_sac'
PLOT_WINDOW_SEC = 60  # seconds to plot after origin time

def get_catalog_info(picker, stage):
    """Dynamically construct catalog info from definitions."""
    stage_def = STAGE_DATA_DEFINITIONS.get(stage, {})
    if 'path_template' in stage_def:
        info = stage_def.copy()
        info['path'] = info['path_template'].format(picker=picker)
        return info
    elif picker in stage_def:
        return stage_def[picker]
    return None

def load_events_for_day(catalog_path, cols, target_date):
    """Load catalog, filter events for a target day."""
    if not os.path.exists(catalog_path):
        print(f"Error: Catalog file not found: {catalog_path}")
        return []

    try:
        data = np.loadtxt(catalog_path, comments='#')
    except Exception as e:
        print(f"Error reading catalog file {catalog_path}: {e}")
        return []

    if data.ndim == 1:
        data = data.reshape(1, -1)

    events = []
    for row in data:
        try:
            # Handle 2-digit years
            year = int(row[cols['yr']])
            if year < 100:
                year += 2000
            
            # For REAL catalog, seconds might be fractional part of minutes column
            if 'sc' in cols and cols['sc'] == cols['mi']:
                minutes = int(row[cols['mi']])
                seconds = (row[cols['mi']] - minutes) * 60
            else:
                minutes = int(row[cols['mi']])
                seconds = row[cols['sc']]

            event_dt = datetime(
                year,
                int(row[cols['mo']]),
                int(row[cols['dy']]),
                int(row[cols['hr']]),
                minutes,
            )
            if event_dt.date() == target_date.date():
                origin_time = UTCDateTime(
                    year,
                    int(row[cols['mo']]),
                    int(row[cols['dy']]),
                    int(row[cols['hr']]),
                    minutes,
                    seconds
                )
                event = {
                    'id': int(row[cols['id']]),
                    'origin_time': origin_time,
                    'lat': row[cols['lat']],
                    'lon': row[cols['lon']],
                    'dep': row[cols['dep']],
                }
                events.append(event)
        except (ValueError, KeyError, IndexError) as e:
            continue
    return events


def plot_record_section_for_event(event, picker, stage, stations_2d_only=False):
    """Plots N and E component record sections for a single event."""
    print(f"Processing event ID {event['id']} at {event['origin_time']}")
    
    event_day_str = event['origin_time'].strftime('%Y%m%d')
    # Assuming daily directories for waveforms, which is a common practice.
    daily_waveform_dir = os.path.join(WAVEFORM_DIR, event_day_str)
    
    if not os.path.isdir(daily_waveform_dir):
        print(f"  Waveform directory for day {event_day_str} not found, trying main waveform directory.")
        daily_waveform_dir = WAVEFORM_DIR # Fallback to main directory

    sac_files = glob.glob(os.path.join(daily_waveform_dir, '*.*[EN].*.SAC'))
    if not sac_files:
        print(f"  No SAC files with E/N components found for event date in {daily_waveform_dir}")
        return

    traces_n, traces_e = [], []
    
    # Get unique stations from available E/N component files
    stations = set('.'.join(os.path.basename(f).split('.')[0:2]) for f in sac_files)

    for station_id in sorted(list(stations)):
        net, sta = station_id.split('.')
        if stations_2d_only and not sta.startswith("2D"):
            continue
        try:
            st = read(os.path.join(daily_waveform_dir, f"*{net}.{sta}*??[NE].*.SAC"))
            # print("read in " + str(st[0].stats))
            
            tr_n = st.select(component="N")[0]
            tr_e = st.select(component="E")[0]

            # Check if trace contains the event time
            if not (tr_n.stats.starttime <= event['origin_time'] <= tr_n.stats.endtime):
                continue

            dist_m, _, _ = gps2dist_azimuth(event['lat'], event['lon'],
                                          tr_n.stats.sac.stla, tr_n.stats.sac.stlo)
            dist_km = dist_m / 1000.0

            traces_n.append((dist_km, tr_n))
            traces_e.append((dist_km, tr_e))

        except Exception:
            print("data file selection didn't work")
            continue
    
    if not traces_n:
        print("  No suitable waveforms found for this event.")
        return

    # Sort traces by distance
    traces_n.sort(key=lambda x: x[0])
    traces_e.sort(key=lambda x: x[0])
    
    # Create output directory
    output_dir = f"record_sections_{picker}_{stage}"
    os.makedirs(output_dir, exist_ok=True)

    # Plotting
    for traces, component in [(traces_n, 'N'), (traces_e, 'E')]:
        if not traces:
            continue
        fig, ax = plt.subplots(figsize=(10, 15))
        
        max_dist = traces[-1][0]
        for dist, tr in traces:
            time_axis = tr.times(reftime=event['origin_time'])
            print("beginning of time axis: " + str(time_axis[0]) + ", origin time: " + str(event['origin_time']))
            
            # Normalize and scale for plotting
            norm_data = tr.data / (np.max(np.abs(tr.data)) + 1e-9)
            scaling_factor = max_dist / len(traces) # Scale wiggles based on number of traces
            
            ax.plot(time_axis[0:int(tr.stats.sampling_rate*PLOT_WINDOW_SEC)]+time_axis[0], dist + scaling_factor * norm_data[0:int(tr.stats.sampling_rate*PLOT_WINDOW_SEC)], 'k-', linewidth=0.5)
            ax.text(PLOT_WINDOW_SEC * 1.01, dist, f" {tr.stats.station}", va='center', ha='left')

        # ax.set_ylim(bottom=0)
        # ax.set_xlim(0, PLOT_WINDOW_SEC)
        ax.set_xlabel('Time (s)')
        ax.set_ylabel('Distance (km)')
        ax.set_title(f'Record Section - Event ID: {event["id"]} ({event["origin_time"]})\nComponent: {component} - Catalog: {picker}/{stage}')
        plt.tight_layout()
        
        output_filename = os.path.join(output_dir, f"event_{event['id']}_{event['origin_time'].strftime('%Y%m%dT%H%M%S')}_{component}.png")
        plt.savefig(output_filename)
        print(f"  Saved plot: {output_filename}")
        plt.close(fig)


def main():
    """Main function to parse arguments and run plotting."""
    parser = argparse.ArgumentParser(description="Plot record sections for a given day, picker, and stage.")
    parser.add_argument("date", help="Date in YYYY-MM-DD format")
    parser.add_argument("picker", help="Picker name (e.g., STALTA, PhaseNet, QMigrate)")
    parser.add_argument("stage", help="Location stage (e.g., Initial, hypoDD_dtct)")
    parser.add_argument("--stations_2d_only", action="store_true", help="Only plot stations starting with '2D'")
    args = parser.parse_args()

    try:
        target_date = datetime.strptime(args.date, '%Y-%m-%d')
    except ValueError:
        print("Error: Date must be in YYYY-MM-DD format.")
        return

    catalog_info = get_catalog_info(args.picker, args.stage)
    if not catalog_info:
        print(f"Error: No catalog definition found for picker '{args.picker}' and stage '{args.stage}'.")
        return

    cols = catalog_info.get('cols')
    if not cols or not all(k in cols for k in ['yr', 'mo', 'dy', 'hr', 'mi', 'sc', 'lat', 'lon', 'dep', 'id']):
        print(f"Error: Column definitions are incomplete for stage '{args.stage}'.")
        return

    events = load_events_for_day(catalog_info['path'], cols, target_date)

    if not events:
        print(f"No events found for {args.date} in catalog for {args.picker}/{args.stage}.")
        return
        
    print(f"Found {len(events)} events for {args.date}.")

    for event in events:
        plot_record_section_for_event(event, args.picker, args.stage, args.stations_2d_only)

if __name__ == '__main__':
    main()
