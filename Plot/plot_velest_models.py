#!/usr/bin/env python3
#
# plot 1D velocity profiles from VELEST model files
#
import os
import glob
import numpy as np
import matplotlib.pyplot as plt

def main():
    """
    Finds all VELEST model*.nd files, plots their P and S wave velocity
    profiles, and saves the resulting figure.
    """
    # Path is relative to the script's location in Plot/
    search_path = '../location/VELEST/*/model*.nd'
    model_files = sorted(glob.glob(search_path))

    if not model_files:
        print(f"No model files found at '{search_path}'. Exiting.")
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 8), sharey=True)
    fig.suptitle('VELEST 1D Velocity Models', fontsize=16)

    # Create a mapping from model name (e.g., 'model1') to a color
    unique_model_names = sorted(list(set([os.path.splitext(os.path.basename(f))[0] for f in model_files])))
    if unique_model_names:
        colors = plt.cm.viridis(np.linspace(0, 1, len(unique_model_names)))
        color_map = {name: colors[i] for i, name in enumerate(unique_model_names)}
    else:
        color_map = {}


    for file_path in model_files:
        try:
            # Extract picker and model name for the label
            model_name = os.path.splitext(os.path.basename(file_path))[0]
            picker_name = os.path.basename(os.path.dirname(file_path))
            label = f"{picker_name}-{model_name}"
            color = color_map.get(model_name)

            # Load data: depth, Vp, Vs
            data = np.loadtxt(file_path)
            depth, vp, vs = data[:, 0], data[:, 1], data[:, 2]

            # Create coordinates for a step plot. Velocity is constant within a layer.
            x_vp = np.repeat(vp, 2)
            x_vs = np.repeat(vs, 2)

            # The depth value is the top of the layer.
            # Create corresponding depth coordinates for the step plot.
            y_depth = np.concatenate(([depth[0]], np.repeat(depth[1:], 2)))

            # Add a bottom to the last layer for plotting
            last_depth = depth[-1] + 5 # arbitrary 5km thickness for the last layer
            y_depth = np.append(y_depth, last_depth)

            # Plot Vp profile
            ax1.plot(x_vp, y_depth, label=label, color=color)

            # Plot Vs profile
            ax2.plot(x_vs, y_depth, label=label, color=color)

        except Exception as e:
            print(f"Warning: Could not process file {file_path}. Error: {e}")

    # Configure P-wave velocity plot
    ax1.set_title('P-wave Velocity (Vp)')
    ax1.set_xlabel('Velocity (km/s)')
    ax1.set_ylabel('Depth (km)')
    ax1.grid(True)
    ax1.legend()

    # Configure S-wave velocity plot
    ax2.set_title('S-wave Velocity (Vs)')
    ax2.set_xlabel('Velocity (km/s)')
    ax2.grid(True)
    ax2.legend()

    # Invert depth axis for both plots
    ax1.invert_yaxis()

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    output_filename = 'velest_model_profiles.png'
    plt.savefig(output_filename)
    print(f"Saved plot to {output_filename}")

if __name__ == '__main__':
    main()
