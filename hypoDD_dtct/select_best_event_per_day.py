#!/usr/bin/env python3

import math
import os

def select_best_event_per_day(input_file, output_file):
    """
    Reads a hypoDD.pha file, finds the event with the lowest total error for each day,
    and writes these events to a new file.
    """
    def calculate_error(header_line):
        """Calculates total error from errX, errY, and errZ."""
        parts = header_line.split()
        # Columns: # yr mo dy hr mn sc lat lon dep mag errX errY errZ eqID
        err_x = float(parts[11])
        err_y = float(parts[12])
        err_z = float(parts[13])
        return math.sqrt(err_x**2 + err_y**2 + err_z**2)

    events = []
    with open(input_file, 'r') as f:
        event_lines = []
        for line in f:
            if line.startswith('#'):
                if event_lines:
                    events.append(event_lines)
                event_lines = [line]
            elif line.strip():
                event_lines.append(line)
        if event_lines:  # Append last event
            events.append(event_lines)

    best_events_per_day = {}

    for event in events:
        header = event[0]
        parts = header.split()
        day_key = tuple(map(int, parts[1:4]))  # (year, month, day)
        error = calculate_error(header)
        
        if day_key not in best_events_per_day or error < best_events_per_day[day_key]['error']:
            best_events_per_day[day_key] = {
                'error': error,
                'event_data': event
            }
    
    # Sort events by date before writing
    sorted_days = sorted(best_events_per_day.keys())

    with open(output_file, 'w') as f:
        for day_key in sorted_days:
            f.writelines(best_events_per_day[day_key]['event_data'])

if __name__ == '__main__':
    pickers = ["STALTA", "PhaseNet", "QMigrate"]
    for picker in pickers:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        input_pha = os.path.join(script_dir, picker, 'hypoDD.pha')
        output_pha = os.path.join(script_dir, picker, 'hypoDD_best.pha')
        
        select_best_event_per_day(input_pha, output_pha)
        
        print(f"Created '{output_pha}' with the best event per day from '{input_pha}'.")
