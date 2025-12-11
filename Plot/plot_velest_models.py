#!/usr/bin/env python3
#
# plot 1D velocity profiles from VELEST model files
#
import os
import glob
import numpy as np
import matplotlib.pyplot as plt
pickers = ["QMigrate", "PhaseNet", "STALTA"]

def main(picker):
    """
    Finds all VELEST model*.nd files, plots their P and S wave velocity
    profiles, and saves the resulting figure.
    """
    # Path is relative to the script's location in Plot/
    search_path = f'../location/VELEST/{picker}/model*.nd'
    model_files = sorted(glob.glob(search_path))

    if not model_files:
        print(f"No model files found at '{search_path}'. Exiting.")
        return

    # --- Data Loading and Processing ---
    models_data = {}
    for file_path in model_files:
        try:
            model_name = os.path.splitext(os.path.basename(file_path))[0]
            model_num = int(model_name.replace('model', ''))
            data = np.loadtxt(file_path)
            models_data[model_num] = {
                'depth': data[:, 0], 'vp': data[:, 1], 'vs': data[:, 2],
                'path': file_path, 'name': model_name
            }
        except (ValueError, IndexError) as e:
            print(f"Warning: Could not parse model number from {file_path}. Skipping. Error: {e}")
            continue

    # --- Calculate Velocity Changes for Table ---
    table_data = []
    sorted_keys = sorted(models_data.keys())
    for i in range(1, len(sorted_keys)):
        prev_model_num = sorted_keys[i-1]
        curr_model_num = sorted_keys[i]

        prev_model = models_data[prev_model_num]
        curr_model = models_data[curr_model_num]

        if len(prev_model['vp']) != len(curr_model['vp']):
            print(f"Warning: Skipping model comparison between {prev_model['name']} and {curr_model['name']} due to different layer counts.")
            continue

        vp_diff = np.sum(np.abs(curr_model['vp'] - prev_model['vp']))
        vs_diff = np.sum(np.abs(curr_model['vs'] - prev_model['vs']))

        update_str = f"model{prev_model_num} → model{curr_model_num}"
        table_data.append([update_str, f"{vp_diff:.2f}", f"{vs_diff:.2f}"])


    # --- Plotting Setup ---
    fig = plt.figure(figsize=(12, 10))
    gs = fig.add_gridspec(2, 2, height_ratios=[3, 1])
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1], sharey=ax1)

    fig.suptitle(f'VELEST 1D Velocity Models from {picker}', fontsize=16)

    # Create a mapping from model name (e.g., 'model1') to a color
    unique_model_names = sorted([m['name'] for m in models_data.values()], key=lambda name: int(name.replace('model', '')))
    if unique_model_names:
        colors = plt.cm.viridis(np.linspace(0, 1, len(unique_model_names)))
        color_map = {name: colors[i] for i, name in enumerate(unique_model_names)}
    else:
        color_map = {}

    for model_num in sorted_keys:
        model = models_data[model_num]
        try:
            picker_name = os.path.basename(os.path.dirname(model['path']))
            label = f"{picker_name}-{model['name']}"
            color = color_map.get(model['name'])

            depth, vp, vs = model['depth'], model['vp'], model['vs']

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
            print(f"Warning: Could not process model {model_num}. Error: {e}")

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

    # --- Add Table ---
    if table_data:
        ax_table = fig.add_subplot(gs[1, :])
        ax_table.axis('off')
        col_labels = ['Model Update', 'Σ|ΔVp|', 'Σ|ΔVs|']
        table = ax_table.table(cellText=table_data, colLabels=col_labels, loc='center', cellLoc='center')
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 1.5)

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    output_filename = f'velest_model_profiles_{picker}.png'
    plt.savefig(output_filename)
    print(f"Saved plot to {output_filename}")

if __name__ == '__main__':
    for picker in pickers:
        main(picker)
