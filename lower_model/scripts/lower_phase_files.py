import sys

def lower_phase_depth(input_file, output_file, depth_change_km=5.0):
    """
    Reads a phase file, adds depth_change_km to the event depth,
    and writes to a new file.
    Handles formats for phase_sel.txt, phase_allday.txt, and phase_best_allday.txt.
    """
    with open(input_file, 'r') as f_in, open(output_file, 'w') as f_out:
        for line in f_in:
            stripped_line = line.strip()
            if not stripped_line:
                f_out.write(line)
                continue

            # Format for phase_allday.txt and phase_best_allday.txt
            if stripped_line.startswith('#'):
                parts = stripped_line[1:].strip().split()
                if len(parts) >= 9:
                    try:
                        # year mo day hr min sec lon lat depth ...
                        # depth is at index 8
                        depth = float(parts[8])
                        parts[8] = f"{depth + depth_change_km:.2f}"
                        f_out.write("# " + " ".join(parts) + "\n")
                    except ValueError:
                        f_out.write(line)  # Not a valid event line
                else:
                    f_out.write(line)  # Not an event line
            else:
                # Format for phase_sel.txt files
                parts = stripped_line.split()
                # Heuristic: starts with an integer (event id), then year, ...
                if len(parts) >= 10 and parts[0].isdigit() and parts[1].isdigit() and len(parts[1]) == 4:
                    try:
                        # event_idx year mo day time ... lon lat depth ...
                        # depth is at index 9
                        depth = float(parts[9])
                        parts[9] = f"{depth + depth_change_km:.2f}"
                        f_out.write(" ".join(parts) + "\n")
                    except (ValueError, IndexError):
                        f_out.write(line)  # Parsing failed
                else:
                    f_out.write(line)  # Not an event line

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: python3 {sys.argv[0]} <input_file> <output_file>")
        sys.exit(1)
    
    input_f = sys.argv[1]
    output_f = sys.argv[2]
    lower_phase_depth(input_f, output_f)
