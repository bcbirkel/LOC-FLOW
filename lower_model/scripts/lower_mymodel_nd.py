import sys

def lower_model_depth(input_file, output_file, depth_change_km=5.0):
    """
    Reads a velocity model file, adds depth_change_km to the depth of each layer,
    and writes to a new file.
    Assumes depth is the first column for lines that represent layers.
    """
    with open(input_file, 'r') as f_in, open(output_file, 'w') as f_out:
        for line in f_in:
            parts = line.strip().split()
            if len(parts) > 0:
                try:
                    # Assuming depth is the first column
                    depth = float(parts[0])
                    # Lowering a layer means increasing its depth
                    parts[0] = f"{depth + depth_change_km:.2f}"
                    f_out.write(" ".join(parts) + "\n")
                except ValueError:
                    # Not a layer line, write as is
                    f_out.write(line)
            else:
                f_out.write(line)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: python3 {sys.argv[0]} <input_file> <output_file>")
        sys.exit(1)

    input_f = sys.argv[1]
    output_f = sys.argv[2]
    lower_model_depth(input_f, output_f)
