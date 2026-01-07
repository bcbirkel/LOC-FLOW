import sys

def lower_station_depth(input_file, output_file, depth_change_km=5.0):
    """
    Reads a station file, lowers the elevation of each station by depth_change_km,
    and writes to a new file.
    Assumes station file format: STA LON LAT ELEV ...
    and that elevation is in km.
    """
    with open(input_file, 'r') as f_in, open(output_file, 'w') as f_out:
        for line in f_in:
            parts = line.strip().split()
            if len(parts) >= 4:
                try:
                    elev = float(parts[3])
                    # Lowering a station means decreasing its elevation
                    parts[3] = f"{elev - depth_change_km:.4f}"
                    f_out.write(" ".join(parts) + "\n")
                except ValueError:
                    # Not a data line, write as is
                    f_out.write(line)
            else:
                # Not a data line, write as is
                f_out.write(line)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: python3 {sys.argv[0]} <input_file> <output_file>")
        sys.exit(1)
    
    input_f = sys.argv[1]
    output_f = sys.argv[2]
    lower_station_depth(input_f, output_f)
