#!/usr/bin/env python3
#
# Creates record section plots for events, showing waveforms and associated picks.
#
import os
import re
from datetime import datetime, timedelta
import obspy
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# --- CONFIGURATION ---
PICKER_MAP = {
    'STALTA': 'sl',
    'PhaseNet': 'pn',
    'QMigrate': 'qm'
}
BASE_DIR_TBL = './'
BASE_DIR_PICKS = './Picks'
BASE_DIR_WAVEFORMS = '../Data/waveform_sac'
OUTPUT_DIR = './RecordSectionPicks'

STATION_PREFIXES = ['2D', 'A', 'B', 'C']
COMPONENTS = ['N', 'E', 'Z'] # Order for plot columns
PLOT_WINDOW_BEFORE_S = 5
PLOT_WINDOW_AFTER_S = 25
# --- END CONFIGURATION ---

def load_events_by_day(tbl_path):
    """Loads events from a .tbl file and groups them by day."""
    events = {}
    with open(tbl_path, 'r') as f:
        for line in f:
            parts = line.split()
            # eqID, year, julian day, month, day, hour, min, sec, ...
            event_id = int(parts[0])
            year, month, day = int(parts[1]), int(parts[3]), int(parts[4])
            hour, minute = int(parts[5]), int(parts[6])
            sec_float = float(parts[7])
            microsecond = int((sec_float - int(sec_float)) * 1_000_000)

            origin_time = datetime(year, month, day, hour, minute, int(sec_float), microsecond)
            date_str = origin_time.strftime('%Y%m%d')

            if date_str not in events:
                events[date_str] = []
            events[date_str].append({'id': event_id, 'origin': origin_time})
    return events

def load_picks(picks_path):
    """Loads picks from a .picks file into a dictionary."""
    picks = {}
    if not os.path.exists(picks_path):
        return picks
    with open(picks_path, 'r') as f:
        for line in f:
            if line.startswith('#'):
                continue
            parts = line.split()
            station, phase, pick_time = parts[0], parts[1], float(parts[2])
            if station not in picks:
                picks[station] = {}
            picks[station][phase] = pick_time
    return picks

def get_station_number(station_name, prefix):
    """Extracts the numeric part of a station name for sorting."""
    try:
        # Remove prefix, then remove any other non-digit characters
        return int(re.sub(r'\D', '', station_name[len(prefix):]))
    except (ValueError, IndexError):
        return -1

def main():
    """Main function to generate record section plots."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Output will be saved in: {os.path.abspath(OUTPUT_DIR)}")

    for picker, picker_short in PICKER_MAP.items():
        tbl_file = os.path.join(BASE_DIR_TBL, f'{picker}.hypoDD.tbl')
        if not os.path.exists(tbl_file):
            print(f"Warning: TBL file not found for {picker}, skipping.")
            continue

        print(f"\n--- Processing Picker: {picker} ---")
        picker_output_dir = os.path.join(OUTPUT_DIR, picker)
        os.makedirs(picker_output_dir, exist_ok=True)

        events_by_day = load_events_by_day(tbl_file)

        for date_str, events in sorted(events_by_day.items()):
            waveform_dir = os.path.join(BASE_DIR_WAVEFORMS, date_str)
            if not os.path.exists(waveform_dir):
                print(f"  Waveform directory not found for {date_str}, skipping day.")
                continue

            print(f"  Loading waveforms for {date_str}...")
            try:
                st = obspy.read(os.path.join(waveform_dir, '4W.*.*.SAC'))
                st.merge(method=1, fill_value='latest')
            except Exception as e:
                print(f"    Could not load waveforms for {date_str}. Error: {e}")
                continue

            for event in sorted(events, key=lambda x: x['origin']):
                event_id = event['id']
                origin_time = event['origin']
                print(f"    Processing event {event_id} at {origin_time.isoformat()}")

                picks_file = os.path.join(BASE_DIR_PICKS, picker, f'{picker_short}.{event_id:03d}.picks')
                event_picks = load_picks(picks_file)

                fig, axes = plt.subplots(len(STATION_PREFIXES), len(COMPONENTS),
                                         figsize=(18, 24), sharex=True, constrained_layout=True)
                fig.suptitle(f'Event {event_id:03d} ({picker}) - {origin_time.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]} UTC', fontsize=16)

                plot_start_time = origin_time - timedelta(seconds=PLOT_WINDOW_BEFORE_S)
                plot_end_time = origin_time + timedelta(seconds=PLOT_WINDOW_AFTER_S)

                for row, prefix in enumerate(STATION_PREFIXES):
                    for col, comp in enumerate(COMPONENTS):
                        ax = axes[row, col]
                        if row == 0:
                            ax.set_title(f'Component {comp}')
                        ax.set_ylabel(f'Stations {prefix}*', rotation=90, size='large', labelpad=20)

                        traces_to_plot = st.select(network='4W', station=f'{prefix}*', channel=f'*{comp}')
                        
                        if not traces_to_plot:
                            ax.text(0.5, 0.5, 'No Data', ha='center', va='center', transform=ax.transAxes)
                            ax.set_yticks([])
                            continue

                        sorted_traces = sorted(list(traces_to_plot), key=lambda tr: get_station_number(tr.stats.station, prefix))
                        
                        y_labels, y_ticks = [], []
                        vertical_gap = 1.5
                        offset = (len(sorted_traces) - 1) * vertical_gap
                        
                        for tr in sorted_traces:
                            tr_cut = tr.copy().trim(obspy.UTCDateTime(plot_start_time), obspy.UTCDateTime(plot_end_time))
                            if not tr_cut.data.any(): continue

                            data = tr_cut.data
                            data = data / (np.max(np.abs(data)) or 1)
                            times = tr_cut.times("matplotlib")
                            
                            ax.plot(times, data + offset, 'k-', linewidth=0.5)
                            y_labels.append(tr.stats.station)
                            y_ticks.append(offset)
                            
                            station_picks = event_picks.get(tr.stats.station)
                            if station_picks:
                                if 'P' in station_picks:
                                    pick_time_abs = origin_time + timedelta(seconds=station_picks['P'])
                                    ax.plot([mdates.date2num(pick_time_abs)], [offset], 'r|', markersize=10, mew=1.5)
                                if 'S' in station_picks:
                                    pick_time_abs = origin_time + timedelta(seconds=station_picks['S'])
                                    ax.plot([mdates.date2num(pick_time_abs)], [offset], 'b|', markersize=10, mew=1.5)

                            offset -= vertical_gap

                        ax.set_yticks(y_ticks)
                        ax.set_yticklabels(y_labels)
                        ax.set_ylim(-1, len(sorted_traces) * vertical_gap)
                
                ax.xaxis_date()
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
                plt.setp(axes[-1, :], xlabel='Time (UTC)')
                fig.autofmt_xdate(rotation=30, ha='right')

                output_filename = os.path.join(picker_output_dir, f'{picker_short}.{event_id:03d}.pickplot.png')
                plt.savefig(output_filename, dpi=150)
                plt.close(fig)
    print("\nDone.")

if __name__ == '__main__':
    main()
