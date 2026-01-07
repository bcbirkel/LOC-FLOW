import sys
import re

def is_velest_event_line(parts):
    """
    Heuristically checks if a line (split into parts) is a VELEST event header line.
    e.g. YYYY MM DD HH MM SS.SS LAT LON DEP ...
    """
    if len(parts) < 9:
        return False
    try:
        # Check if first 6 parts are numeric (date and time)
        for i in range(6):
            float(parts[i])
        # Check if parts 6, 7, 8 (lat, lon, depth) are numeric
        for i in range(6, 9):
            float(parts[i])
        return True
    except ValueError:
        return False

def is_hypoinverse_event_line(line):
    """
    Heuristically checks if a line is a hypoinverse event summary line.
    An event line starts with a date and time, e.g., YYYYMMDDHHMM...
    """
    return len(line) >= 38 and re.match(r'^\s*\d{14,}', line.strip())

def lower_phase_depth(input_file, output_file, depth_change_km=5.0):
    """
    Reads a phase file, adds depth_change_km to the event depth,
    and writes to a new file.
    Tries to auto-detect VELEST or Hypoinverse format for event lines.
    """
    with open(input_file, 'r') as f_in, open(output_file, 'w') as f_out:
        for line in f_in:
            stripped_line = line.strip()
            parts = stripped_line.split()

            if is_hypoinverse_event_line(line): # use original line for fixed-width
                try:
                    # Depth is in columns 34-38 (F5.2 format, 1-indexed)
                    # Python slicing is 0-indexed, so 33:38
                    depth_str = line[33:38]
                    depth = float(depth_str)
                    new_depth = depth + depth_change_km
                    new_depth_str = f"{new_depth:5.2f}"
                    
                    if len(new_depth_str) > 5:
                        print(f"Warning: new depth {new_depth_str} for line in {input_file} might not fit in 5 characters. Truncating.", file=sys.stderr)
                        new_depth_str = new_depth_str[:5]

                    # Use original line to preserve spacing
                    new_line = line[:33] + new_depth_str + line[38:]
                    f_out.write(new_line)
                except (ValueError, IndexError):
                    f_out.write(line) # Not a valid event line or parsing failed
            elif is_velest_event_line(parts):
                try:
                    # Depth is the 9th column (index 8) in VELEST format
                    depth = float(parts[8])
                    parts[8] = f"{depth + depth_change_km:.2f}"
                    f_out.write(" ".join(parts) + "\n")
                except (ValueError, IndexError):
                    f_out.write(line) # Parsing failed
            else:
                f_out.write(line) # Not an event line

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: python3 {sys.argv[0]} <input_file> <output_file>")
        sys.exit(1)
    
    input_f = sys.argv[1]
    output_f = sys.argv[2]
    lower_phase_depth(input_f, output_f)
