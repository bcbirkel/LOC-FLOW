import sys

def lower_model_depth(input_file, output_file, depth_change_km=5.0):
    """
    Reads a velocity model file, adds depth_change_km to the depth of each layer,
    interpolates new layers between 0 and 5km, and writes to a new file.
    Assumes depth is the first column for lines that represent layers.
    """
    lowered_layers = []
    non_layer_lines = []

    with open(input_file, 'r') as f_in:
        for line in f_in:
            parts = line.strip().split()
            if len(parts) > 0:
                try:
                    depth = float(parts[0])
                    new_depth = depth + depth_change_km
                    new_parts = [f"{new_depth:.2f}"] + parts[1:]
                    lowered_layers.append(new_parts)
                except ValueError:
                    non_layer_lines.append(line)
            else:
                non_layer_lines.append(line)
    
    layer_0km = next((layer for layer in lowered_layers if float(layer[0]) == 0.0), None)
    layer_5km = next((layer for layer in lowered_layers if float(layer[0]) == 5.0), None)

    if layer_0km and layer_5km:
        vp0, vs0 = float(layer_0km[1]), float(layer_0km[2])
        vp5, vs5 = float(layer_5km[1]), float(layer_5km[2])
        other_props = layer_0km[3:]

        for d_km in range(1, 5): # For depths 1, 2, 3, 4 km
            vp_interp = vp0 + (vp5 - vp0) * d_km / 5.0
            vs_interp = vs0 + (vs5 - vs0) * d_km / 5.0
            new_layer = [f"{float(d_km):.2f}", f"{vp_interp:.5f}", f"{vs_interp:.5f}"] + other_props
            lowered_layers.append(new_layer)

    lowered_layers.sort(key=lambda x: float(x[0]))
    
    with open(output_file, 'w') as f_out:
        if non_layer_lines:
            # Assuming non-layer lines (if any) are headers.
            for line in non_layer_lines:
                f_out.write(line)
        
        for layer in lowered_layers:
            f_out.write(" ".join(layer) + "\n")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: python3 {sys.argv[0]} <input_file> <output_file>")
        sys.exit(1)

    input_f = sys.argv[1]
    output_f = sys.argv[2]
    lower_model_depth(input_f, output_f)
