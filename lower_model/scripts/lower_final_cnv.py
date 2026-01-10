import sys

def lower_cnv_depth(input_file, output_file, depth_change_km=0.75):
    """
    Reads a VELEST final.CNV file, adds depth_change_km to the event depth,
    and writes to a new file.
    """
    with open(input_file, 'r') as f_in, open(output_file, 'w') as f_out:
        for line in f_in:
            # Heuristic for event header line in VELEST .CNV format.
            # Based on fixed columns for lat, lon, and depth.
            is_event_line = False
            if len(line) > 49:
                try:
                    lat_char = line[29]
                    lon_char = line[40]
                    depth_str = line[43:49]
                    float(depth_str)
                    if lat_char in 'NS' and lon_char in 'EW':
                        is_event_line = True
                except (ValueError, IndexError):
                    is_event_line = False
            
            if is_event_line:
                depth = float(line[43:49])
                new_depth = depth + depth_change_km
                new_depth_str = f"{new_depth:6.2f}"
                new_line = line[:43] + new_depth_str + line[49:]
                f_out.write(new_line)
            else:
                f_out.write(line)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: python3 {sys.argv[0]} <input_file> <output_file>")
        sys.exit(1)

    input_f = sys.argv[1]
    output_f = sys.argv[2]
    lower_cnv_depth(input_f, output_f)
