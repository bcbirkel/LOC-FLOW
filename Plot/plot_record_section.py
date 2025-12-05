#!/usr/bin/env python3
#
# Plot record sections for events on a specific day from a given catalog.
#
# Example usage:
# 
# python plot_record_section.py 2023-04-13 --picker QMigrate --stage Initial --only_stations 2D
# python plot_record_section.py 2023-04-13 --picker QMigrate --only_stations 2D --plot_mode picker_stages

import argparse
import os
import glob
from datetime import datetime
import time

import numpy as np
import matplotlib.pyplot as plt
from obspy import read, UTCDateTime, Stream
from obspy.geodetics import gps2dist_azimuth

# This dictionary is adapted from plot_3d.py to include origin time columns.
# It helps in locating catalog files and parsing them.
# NOTE: lon/lat for hypoDD is swapped compared to plot_3d.py to match standard format.
PICKERS = ['STALTA', 'PhaseNet', 'QMigrate']
STAGES = ['Initial', 'VELEST', 'hypoinverse', 'hypoinverse_corr', 'hypoDD_dtct']
STAGE_DATA_DEFINITIONS = {
    'Initial': {
        'STALTA': {
            'path': '../REAL/catalogSA_allday.txt',
            'cols': {'lon': 6, 'lat': 7, 'dep': 8, 'yr': 0, 'mo': 1, 'dy': 2, 'hr': 3, 'mi': 4, 'sc': 5, 'id': 0},
        },
        'PhaseNet': {
            'path': '../REAL/runs/PhaseNet/catalogSA_allday.txt',
            'cols': {'lon': 6, 'lat': 7, 'dep': 8, 'yr': 0, 'mo': 1, 'dy': 2, 'hr': 3, 'mi': 4, 'sc': 5, 'id': 0},
        },
        'QMigrate': {
            'path': '../REAL/runs/QMigrate/all_events_trimmed.txt',
            'cols': {'lon': 8, 'lat': 9, 'dep': 10, 'yr': 2, 'mo': 3, 'dy': 4, 'hr': 5, 'mi': 6, 'sc': 7},
        },
    },
    'VELEST': {
        'path_template': '../location/VELEST/{picker}/new.cat',
        'cols': {'lon': 5, 'lat': 4, 'dep': 6, 'yr': 0, 'mo': 0, 'dy': 0, 'hr': 1, 'mi': 2, 'sc': 3},
    },
    'hypoinverse': {
        'path_template': '../location/hypoinverse/{picker}/new.cat',
        'cols': {'lon': 5, 'lat': 4, 'dep': 6, 'yr': 0, 'mo': 0, 'dy': 0, 'hr': 1, 'mi': 2, 'sc': 3},
    },
    'hypoinverse_corr': {
        'path_template': '../location/hypoinverse_corr/{picker}/new.cat',
        'cols': {'lon': 5, 'lat': 4, 'dep': 6, 'yr': 0, 'mo': 0, 'dy': 0, 'hr': 1, 'mi': 2, 'sc': 3},
    },
    'hypoDD_dtct': {
        'path_template': '../hypoDD_dtct/{picker}/hypoDD.reloc',
        'cols': {'lat': 1, 'lon': 2, 'dep': 3, 'yr': 10, 'mo': 11, 'dy': 12, 'hr': 13, 'mi': 14, 'sc': 15, 'id': 0},
    },
}

WAVEFORM_DIR = '/project2/okaya_201/data/daily_200Hz'
PLOT_WINDOW_SEC = 30  # seconds to plot after origin time

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
    if not cols:
        print(f"Warning: No column definitions for catalog, skipping: {catalog_path}")
        return []
    if not os.path.exists(catalog_path):
        print(f"Warning: Catalog file not found: {catalog_path}")
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
            if 'yr' in cols and cols['yr'] == cols['mo']:
                if str(row[cols['yr']])[0:2] == '23':
                    twoyear = int(str(row[cols['yr']])[0:2])
                    year = twoyear + 2000
                    month = int(str(row[cols['mo']])[2:4])
                    day = int(str(row[cols['dy']])[4:6])
                elif str(row[cols['yr']])[0:2] == '20':
                    year = int(str(row[cols['yr']])[0:4])
                    month = int(str(row[cols['mo']])[4:6])
                    day = int(str(row[cols['dy']])[6:8])
                # print(f'{year},{month},{day}')
            else:
                year = int(row[cols['yr']])
                month = int(row[cols['mo']])
                day = int(row[cols['dy']])

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
                month,
                day,
                int(row[cols['hr']]),
                minutes,
            )

            if event_dt.date() == target_date.date():
                origin_time = UTCDateTime(
                    year,
                    month,
                    day,
                    int(row[cols['hr']]),
                    minutes,
                    seconds
                )
                event = {
                    'origin_time': origin_time,
                    'lat': row[cols['lat']],
                    'lon': row[cols['lon']],
                    'dep': row[cols['dep']],
                }
                if 'id' in cols:
                    event['id'] = int(row[cols['id']])
                else:
                    # Create a placeholder ID if not present
                    event['id'] = f"{year}{month}{day}{int(row[cols['hr']])}{minutes}{int(seconds)}"

                events.append(event)
        except (ValueError, KeyError, IndexError) as e:
            continue
    return events


def find_nearest_event(ref_event, events, time_window=60):
    """Finds the nearest event in a list within a time window."""
    best_match = None
    min_dt = float('inf')
    for event in events:
        dt = abs(ref_event['origin_time'] - event['origin_time'])
        if dt < time_window and dt < min_dt:
            min_dt = dt
            best_match = event
    return best_match

def load_station_data(station_file='../Data/station_filt.dat'):
    """Load station data into a dictionary for quick lookup."""
    station_locs = {}
    if not os.path.exists(station_file):
        print(f"Warning: Station file not found: {station_file}")
        return station_locs
    
    with open(station_file, 'r') as f:
        for line in f:
            try:
                parts = line.split()
                if len(parts) < 4: continue
                lat, lon, net, sta = parts[0], parts[1], parts[2], parts[3]
                key = f"{net}.{sta}"
                if key not in station_locs:
                    station_locs[key] = (float(lat), float(lon))
            except (ValueError, IndexError):
                continue
    return station_locs

def plot_record_section_on_ax(ax, event, component, event_waveforms, station_locs, only_stations=None, time_window_buffer=40):
    """Plots a single record section on a given matplotlib axis."""
    if not event_waveforms:
        return 0

    traces = []
    # Create a set of unique stations (net.sta) to iterate over
    station_ids = sorted(list(set(f"{tr.stats.network}.{tr.stats.station}" for tr in event_waveforms)))

    for station_id in station_ids:
        net, sta = station_id.split('.')
        if only_stations and not sta.startswith(only_stations):
            continue
        
        station_traces = event_waveforms.select(network=net, station=sta)
        if not station_traces:
            continue

        # Find coordinates from any trace for this station
        lat, lon = None, None
        for tr_ in station_traces:
            if hasattr(tr_.stats, 'latitude') and hasattr(tr_.stats, 'longitude'):
                lat, lon = tr_.stats.latitude, tr_.stats.longitude
                break
            elif hasattr(tr_.stats, 'sac'):
                if hasattr(tr_.stats.sac, 'stla') and hasattr(tr_.stats.sac, 'stlo'):
                    lat, lon = tr_.stats.sac.stla, tr_.stats.sac.stlo
                    break
        
        if lat is None or lon is None:
            if station_id in station_locs:
                lat, lon = station_locs[station_id]
            else:
                continue

        component_traces = station_traces.select(component=component)
        if not component_traces:
            continue
        tr = component_traces[0].copy()

        try:
            if not (tr.stats.starttime <= event['origin_time'] <= tr.stats.endtime):
                continue
            dist_m, _, _ = gps2dist_azimuth(event['lat'], event['lon'], lat, lon)
            traces.append((dist_m / 1000.0, tr))
        except Exception:
            continue
    
    if not traces:
        return 0

    traces.sort(key=lambda x: x[0])
    
    max_dist = traces[-1][0] if traces else 1
    for dist, tr in traces:
        time_axis = tr.times(reftime=event['origin_time'])
        norm_data = tr.data / (np.max(np.abs(tr.data)) + 1e-9)
        scaling_factor = max_dist / (len(traces) * 1.0) # Adjust for better visual separation
        
        ax.plot(time_axis[0:int(tr.stats.sampling_rate*(PLOT_WINDOW_SEC+time_window_buffer))], dist + scaling_factor * norm_data[0:int(tr.stats.sampling_rate*(PLOT_WINDOW_SEC+time_window_buffer))], 'k-', linewidth=0.3)
        ax.text(PLOT_WINDOW_SEC * 1.01, dist, f" {tr.stats.station}", va='center', ha='left')

    ax.set_ylim(bottom=0, top=max_dist * 1.1)
    ax.set_xlim(0, PLOT_WINDOW_SEC)
    ax.set_xlabel('Time (s)')
    ax.set_ylabel('Distance (km)')

    return len(traces)

def main():
    """Main function to parse arguments and run plotting."""
    script_start_time = time.time()
    parser = argparse.ArgumentParser(description="Plot record sections for a given day, comparing across pickers and stages.")
    parser.add_argument("date", help="Date in YYYY-MM-DD format")
    parser.add_argument("--picker", help="Picker name to focus on for 'picker_stages' mode.")
    parser.add_argument("--stage", help="Stage to plot (e.g., Initial, hypoDD_dtct). If not given, all stages are processed.")
    parser.add_argument("--plot_mode", choices=['individual', 'all_in_one', 'picker_stages'], default='individual',
                        help="Plotting mode: 'individual' for separate plots, 'all_in_one' for a single large figure (default), 'picker_stages' for all stages of a specified picker.")
    parser.add_argument("--only_stations", type=str, help="Only plot stations starting with this string (e.g., '2D', 'A').")
    args = parser.parse_args()

    if args.plot_mode == 'picker_stages' and not args.picker:
        parser.error("--picker is required for 'picker_stages' plot mode.")

    t0 = time.time()
    station_locs = load_station_data()
    print(f"Loaded station data in {time.time() - t0:.2f}s")

    try:
        target_date = datetime.strptime(args.date, '%Y-%m-%d')
    except ValueError:
        print("Error: Date must be in YYYY-MM-DD format.")
        return

    # Load reference catalog (QMigrate/hypoDD_dtct)
    t0 = time.time()
    ref_catalog_info = get_catalog_info('QMigrate', 'hypoDD_dtct')
    ref_events = load_events_for_day(ref_catalog_info['path'], ref_catalog_info['cols'], target_date)
    print(f"Loaded reference catalog ({len(ref_events)} events) in {time.time() - t0:.2f}s")

    if not ref_events:
        print("No events found in the reference catalog (QMigrate/hypoDD_dtct).")
        return

    # Load all other available catalogs
    t0 = time.time()
    all_catalogs = {}
    
    stages_to_plot = STAGES
    if args.stage:
        if args.stage in STAGES:
            stages_to_plot = [args.stage]
        else:
            print(f"Error: Stage '{args.stage}' not defined.")
            return

    for stage in stages_to_plot:
        stage_def = STAGE_DATA_DEFINITIONS[stage]
        if 'path_template' in stage_def:
            for picker in PICKERS:
                # print(stage)
                info = get_catalog_info(picker, stage)
                events = load_events_for_day(info['path'], info['cols'], target_date)
                print(f"{stage}/{picker}: has {len(events)}")
                if events: all_catalogs[(picker, stage)] = events
        elif stage == 'Initial':
            for picker in PICKERS:
                info = get_catalog_info(picker, stage)
                events = load_events_for_day(info['path'], info['cols'], target_date)
                print(f"{stage}/{picker}: has {len(events)}")
                if events: all_catalogs[(picker, stage)] = events
    print(f"Loaded all other catalogs in {time.time() - t0:.2f}s")

    # For each reference event, find matches and plot
    total_events = len(ref_events)
    for i, ref_event in enumerate(ref_events):
        event_start_time = time.time()
        print(f"\nProcessing reference event ID {ref_event['id']} at {ref_event['origin_time']} ({i + 1}/{total_events})")
        
        # Load waveform data for a window around the reference event
        # This window is large enough to contain data for all matched events.
        t0 = time.time()
        event_day_str = ref_event['origin_time'].strftime('%Y%m%d')
        daily_waveform_dir = os.path.join(WAVEFORM_DIR, event_day_str)
        event_waveforms = Stream()
        if os.path.isdir(daily_waveform_dir):
            time_window_buffer = 40  # seconds, to account for matched events (30s) + read buffer (10s)
            read_starttime = ref_event['origin_time'] - time_window_buffer
            read_endtime = ref_event['origin_time'] + PLOT_WINDOW_SEC + time_window_buffer
            
            mseed_pattern = f'{args.only_stations}*.mseed' if args.only_stations else '*.mseed'
            mseed_files = glob.glob(os.path.join(daily_waveform_dir, mseed_pattern))
            
            for f in mseed_files:
                try:
                    event_waveforms += read(f, starttime=read_starttime, endtime=read_endtime)
                except Exception:
                    continue # File may not contain data for this window
            print(f"  Loaded {len(event_waveforms)} traces in {time.time() - t0:.2f}s")

        if not event_waveforms:
            print("  No waveforms found for this event's time window, skipping.")
            continue
        else:
            event_waveforms.filter("bandpass",freqmin=1,freqmax=40)

        t0 = time.time()
        matched_events = {('QMigrate', 'hypoDD_dtct'): ref_event}
        for (picker, stage), events in all_catalogs.items():
            if picker == 'QMigrate' and stage == 'hypoDD_dtct': continue
            match = find_nearest_event(ref_event, events, 120)
            if match:
                matched_events[(picker, stage)] = match
                print(f"  Found match for {picker}/{stage}: event at {match['origin_time']}")
            else:
                print(f"  Couldn't find match for {picker}/{stage}")
        print(f"  Found matched events in {time.time() - t0:.2f}s")

        t0 = time.time()
        output_dir = os.path.join("record_sections", f"event_{ref_event['id']}_{ref_event['origin_time'].strftime('%Y%m%dT%H%M%S')}")
        os.makedirs(output_dir, exist_ok=True)

        if args.plot_mode == 'individual':
            for (picker, stage), event in matched_events.items():
                components = ['N', 'E', 'Z']
                fig, axes = plt.subplots(1, len(components), figsize=(24, 10), sharey=True)
                fig.suptitle(f'Event ID: {ref_event["id"]} - {picker}/{stage}\nOrigin: {event["origin_time"]}', fontsize=16)

                total_traces_plotted = 0
                for i, comp in enumerate(components):
                    ax = axes[i]
                    num_traces = plot_record_section_on_ax(ax, event, comp, event_waveforms, station_locs, args.only_stations, time_window_buffer)
                    total_traces_plotted += num_traces
                    ax.set_title(f'Component: {comp}')
                    if i > 0:
                        ax.set_ylabel('')  # Distance label only on first plot
                
                if total_traces_plotted > 0:
                    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
                    filename = os.path.join(output_dir, f"{picker}_{stage}.png")
                    plt.savefig(filename)
                    print(f"  Saved plot: {filename}")
                else:
                    print(f"  --> Could not plot record section for {picker}/{stage}: No suitable waveform data found.")
                plt.close(fig)
        
        elif args.plot_mode == 'all_in_one':
             # Determine grid size
            plot_keys = sorted(matched_events.keys())
            n_plots = len(plot_keys)
            if n_plots == 0: continue
            ncols = min(n_plots, 3) # Max 3 columns for picker/stage combinations
            nrows = (n_plots + ncols - 1) // ncols
            components = ['N', 'E', 'Z']
            
            # We will have a grid of picker/stages, with 3 component plots vertically for each.
            fig, axes = plt.subplots(nrows * len(components), ncols, figsize=(ncols * 8, nrows * 15), squeeze=False, sharex='col', sharey='all')
            fig.suptitle(f'Record Sections for Event ID: {ref_event["id"]} ({ref_event["origin_time"]})', fontsize=16)

            total_traces_plotted = 0
            for i, (picker, stage) in enumerate(plot_keys):
                event = matched_events[(picker, stage)]
                for comp_idx, comp in enumerate(components):
                    row_idx = (i // ncols) * len(components) + comp_idx
                    col_idx = i % ncols
                    ax = axes[row_idx, col_idx]

                    num_traces = plot_record_section_on_ax(ax, event, comp, event_waveforms, station_locs, args.only_stations, time_window_buffer)
                    total_traces_plotted += num_traces

                    if comp_idx == 0:
                        ax.set_title(f'{picker} / {stage}')
                    
                    ax.set_ylabel(f'Dist (km)\n{comp}')

            # Hide unused axes
            for i in range(n_plots, nrows * ncols):
                for comp_idx in range(len(components)):
                    row_idx = (i // ncols) * len(components) + comp_idx
                    col_idx = i % ncols
                    fig.delaxes(axes[row_idx, col_idx])
            
            if total_traces_plotted > 0:
                plt.tight_layout(rect=[0, 0.03, 1, 0.95])
                filename = os.path.join(output_dir, "all_in_one.png")
                plt.savefig(filename)
                print(f"  Saved plot: {filename}")
            else:
                print(f"  --> Could not plot any record sections for event {ref_event['id']}: No suitable waveform data found.")
            plt.close(fig)
        
        elif args.plot_mode == 'picker_stages':
            # stages_for_picker = sorted([s for p, s in matched_events.keys() if p == args.picker])
            stages_for_picker = [s for p, s in matched_events.keys() if p == args.picker]
            n_plots = len(stages_for_picker)
            if n_plots == 0: continue
            
            components = ['N', 'E', 'Z']
            fig, axes = plt.subplots(n_plots, len(components), figsize=(24, n_plots * 7), squeeze=False, sharey='row')
            fig.suptitle(f'Record Sections for Event ID: {ref_event["id"]} - Picker: {args.picker}', fontsize=16)

            total_traces_plotted = 0
            for i, stage in enumerate(stages_for_picker):
                event = matched_events[(args.picker, stage)]
                for j, comp in enumerate(components):
                    ax = axes[i, j]
                    num_traces = plot_record_section_on_ax(ax, event, comp, event_waveforms, station_locs, args.only_stations, time_window_buffer)
                    total_traces_plotted += num_traces

                    if i == 0:  # Top row
                        ax.set_title(f'Component: {comp}')
                    if j == 0:  # First column
                        ax.set_ylabel(f'Dist (km)\nStage: {stage}')
                    else:
                        ax.set_ylabel('')  # Y-labels only on first column
            
            if total_traces_plotted > 0:
                plt.tight_layout(rect=[0, 0.03, 1, 0.95])
                filename = os.path.join(output_dir, f"{args.picker}_stages.png")
                plt.savefig(filename)
                print(f"  Saved plot: {filename}")
            else:
                print(f"  --> Could not plot any record sections for picker {args.picker} for event {ref_event['id']}: No suitable waveform data found.")
            plt.close(fig)
        print(f"  Generated and saved plots in {time.time() - t0:.2f}s")
        print(f"  Total time for this event: {time.time() - event_start_time:.2f}s")

    print(f"\nTotal script execution time: {time.time() - script_start_time:.2f}s")

if __name__ == '__main__':
    main()
