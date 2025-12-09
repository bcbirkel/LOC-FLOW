#!/usr/bin/env python3
#
# plot event cross sections perpendicular to the main trend
#
import os
import numpy as np
import matplotlib.pyplot as plt

# --- CONFIGURATION (from plot_3d.py) ---

# Define the pickers and location stages
PICKERS = ['STALTA', 'PhaseNet', 'QMigrate']
STAGES = ['Initial', 'VELEST', 'hypoinverse', 'hypoinverse_corr', 'hypoDD_dtct']

# Toggle which pickers and stages to plot
PLOT_PICKERS = {picker: True for picker in PICKERS}
PLOT_STAGES = {stage: True for stage in STAGES}

# This dictionary defines the data source for each stage.
STAGE_DATA_DEFINITIONS = {
    'Initial': {
        'STALTA': {
            'path': '/project2/okaya_201/LOC-FLOW/complete_STALTA/REAL/catalogSA_allday.txt',
            'cols': {'lon': 6, 'lat': 7, 'dep': 8},
            'title': 'STALTA - REAL'
        },
        'PhaseNet': {
            'path': '../REAL/runs/PhaseNet/catalogSA_allday.txt',
            'cols': {'lon': 6, 'lat': 7, 'dep': 8},
            'title': 'PhaseNet - REAL'
        },
        'QMigrate': {
            'path': '../REAL/runs/QMigrate/all_events_trimmed.txt',
            'cols': {'lon': 8, 'lat': 9, 'dep': 10},
            'title': 'QMigrate - Initial'
        }
    },
    'VELEST': {
        'path_template': '../location/VELEST/{picker}/new.cat',
        'cols': {'lon': 5, 'lat': 4, 'dep': 6},
        'title_template': '{picker} - VELEST'
    },
    'hypoinverse': {
        'path_template': '../location/hypoinverse/{picker}/new.cat',
        'cols': {'lon': 5, 'lat': 4, 'dep': 6},
        'title_template': '{picker} - HYPOINVERSE'
    },
    'hypoinverse_corr': {
        'path_template': '../location/hypoinverse_corr/{picker}/new.cat',
        'cols': {'lon': 5, 'lat': 4, 'dep': 6},
        'title_template': '{picker} - HYPOINVERSE_corr'
    },
    'hypoDD_dtct': {
        'path_template': '../hypoDD_dtct/{picker}/hypoDD.reloc',
        'cols': {'lon': 2, 'lat': 1, 'dep': 3},
        'title_template': '{picker} - hypoDD (dt.ct)',
    },
}

# Plotting region (manually specify) - for initial data filtering
XMIN, XMAX = 85, 86.5         # Longitude
YMIN, YMAX = 27, 28.5           # Latitude
ZMIN, ZMAX = -5, 25           # Depth

# --- END CONFIGURATION ---


def apply_filters(data, filters):
    """Apply filters to the data."""
    if not filters:
        return data
    mask = np.ones(data.shape[0], dtype=bool)
    for f in filters:
        op = f['op']
        if op == '>=':
            mask &= (data[:, f['col']] >= f['val'])
        elif op == '<=':
            mask &= (data[:, f['col']] <= f['val'])
        elif op == '>':
            mask &= (data[:, f['col']] > f['val'])
        elif op == '<':
            mask &= (data[:, f['col']] < f['val'])
        elif op == '==':
            mask &= (data[:, f['col']] == f['val'])
        elif op == '!=':
            mask &= (data[:, f['col']] != f['val'])
    return data[mask]


def load_data(stage_info):
    """Load and filter data for a given stage."""
    path = stage_info['path']
    alt_path = stage_info.get('alt_path')

    if not os.path.exists(path):
        if alt_path and os.path.exists(alt_path):
            path = alt_path
        else:
            print(f"Warning: Data file not found for '{stage_info['title']}': {path}")
            return None

    try:
        data = np.loadtxt(path)
        if data.ndim == 1:  # handle file with one line
            data = data.reshape(1, -1)
        if data.shape[0] == 0:
            print(f"Warning: Data file is empty for '{stage_info['title']}': {path}")
            return None

        # Apply filters before extracting columns
        data = apply_filters(data, stage_info.get('filters'))

        lon = data[:, stage_info['cols']['lon']]
        lat = data[:, stage_info['cols']['lat']]
        dep = data[:, stage_info['cols']['dep']]

        # Filter by region
        mask = (lon >= XMIN) & (lon <= XMAX) & \
               (lat >= YMIN) & (lat <= YMAX) & \
               (dep >= ZMIN) & (dep <= ZMAX)

        return {'lon': lon[mask], 'lat': lat[mask], 'dep': dep[mask], 'title': stage_info['title']}
    except Exception as e:
        print(f"Warning: Could not load or process data for '{stage_info['title']}' from {path}. Error: {e}")
        return None


def get_catalog_info(picker, stage):
    """Dynamically construct catalog info from definitions."""
    stage_def = STAGE_DATA_DEFINITIONS.get(stage, {})

    if 'path_template' in stage_def:
        info = stage_def.copy()
        info['path'] = info['path_template'].format(picker=picker)
        if 'alt_path_template' in info:
            info['alt_path'] = info['alt_path_template'].format(picker=picker)
        if 'title_template' in info:
            info['title'] = info['title_template'].format(picker=picker)
        return info
    elif picker in stage_def:
        # Special case like 'Initial'
        return stage_def[picker]
    else:
        # This picker doesn't have a definition for this stage
        return None


def angle_to_compass(deg):
    """Converts an angle in degrees (0 = East) to a compass direction string."""
    deg = (deg + 360) % 360
    dirs = ['E', 'NE', 'N', 'NW', 'W', 'SW', 'S', 'SE']
    # Each slice is 45 degrees. E is -22.5 to 22.5.
    index = int(round(deg / 45.0)) % 8
    return dirs[index]


def process_and_plot_catalog(data, picker, stage, output_dir):
    """
    Processes a catalog's events to plot a map view with a trend line
    and perpendicular cross-sections.
    """
    if len(data['lon']) < 2:
        print(f"  -> Skipping {data['title']}: Not enough data points ({len(data['lon'])}) to fit a trend line.")
        return

    # 1. Convert lon/lat to local XY in km
    mean_lon = np.mean(data['lon'])
    mean_lat = np.mean(data['lat'])
    km_per_deg_lat = 111.32
    km_per_deg_lon = km_per_deg_lat * np.cos(np.deg2rad(mean_lat))

    x = (data['lon'] - mean_lon) * km_per_deg_lon
    y = (data['lat'] - mean_lat) * km_per_deg_lat
    dep = data['dep']

    # 2. Fit trend line to x, y data
    m, b = np.polyfit(x, y, 1)

    # 3. Define rotated coordinate system
    angle = np.arctan(m)
    # Rotation matrix to align x-axis with the trend line
    rot_matrix = np.array([[np.cos(angle), np.sin(angle)],
                           [-np.sin(angle), np.cos(angle)]])
    coords = np.vstack([x, y])
    rotated_coords = rot_matrix @ coords
    along_strike_dist = rotated_coords[0, :]
    cross_strike_dist = rotated_coords[1, :]

    # --- 4. Define Cross Sections ---
    min_along = np.min(along_strike_dist)
    max_along = np.max(along_strike_dist)

    # Create section centers every 10 km
    start_center = np.floor(min_along / 10) * 10 + 5
    end_center_exclusive = np.ceil(max_along / 10) * 10
    section_centers = np.arange(start_center, end_center_exclusive, 10.0)

    if len(section_centers) == 0:
        # Handle case where data spans less than 10km
        section_centers = [np.mean(along_strike_dist)]

    # Determine common x-axis limits for cross sections for better comparison
    max_cross_abs = np.max(np.abs(cross_strike_dist)) if len(cross_strike_dist) > 0 else 20
    cross_lim = (-max_cross_abs - 5, max_cross_abs + 5)


    # --- 5. Plot Map View ---
    fig_map, ax_map = plt.subplots(figsize=(10, 10))
    sc = ax_map.scatter(x, y, s=15, c=dep, cmap='viridis_r', alpha=0.7, zorder=10)
    cbar = plt.colorbar(sc, ax=ax_map, label='Depth (km)')

    # Plot trend line
    x_fit = np.array([x.min() - 2, x.max() + 2])
    y_fit = m * x_fit + b
    ax_map.plot(x_fit, y_fit, 'r-', lw=2, label='Trend Line', zorder=20)

    # Plot cross-section lines and labels on map
    inv_rot_matrix = rot_matrix.T
    for i, center_dist in enumerate(section_centers):
        label = chr(ord('A') + i)
        # Endpoints in rotated coords
        p1_rot = np.array([center_dist, cross_lim[0]])
        p2_rot = np.array([center_dist, cross_lim[1]])
        # Rotate back to map XY coords
        p1_xy = inv_rot_matrix @ p1_rot
        p2_xy = inv_rot_matrix @ p2_rot
        ax_map.plot([p1_xy[0], p2_xy[0]], [p1_xy[1], p2_xy[1]], 'k-', lw=1.5, zorder=15)

        # Add labels at ends with a small offset along the trend line direction
        offset_dist = 2.0  # km
        offset_vec = np.array([np.cos(angle), np.sin(angle)]) * offset_dist
        ax_map.text(p1_xy[0] + offset_vec[0], p1_xy[1] + offset_vec[1], f"{label}",
                    va='center', ha='center', fontsize=10, color='k', fontweight='bold',
                    bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', boxstyle='round,pad=0.1'))
        ax_map.text(p2_xy[0] + offset_vec[0], p2_xy[1] + offset_vec[1], f"{label}'",
                    va='center', ha='center', fontsize=10, color='k', fontweight='bold',
                    bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', boxstyle='round,pad=0.1'))

    ax_map.set_xlabel('East-West distance from center (km)')
    ax_map.set_ylabel('North-South distance from center (km)')
    ax_map.set_title(f"Map View: {data['title']} ({len(x)} events)")
    ax_map.set_aspect('equal', adjustable='box')
    ax_map.grid(True)
    ax_map.legend()

    map_filename = f"{output_dir}/{picker}_{stage}_map.png"
    plt.savefig(map_filename)
    plt.close(fig_map)

    # --- 6. Plot Cross Sections ---
    num_sections = len(section_centers)
    if num_sections == 0:
        return

    ncols = min(4, num_sections)
    nrows = int(np.ceil(num_sections / ncols))
    fig_cs, axes_cs = plt.subplots(nrows, ncols, figsize=(5 * ncols, 5 * nrows), squeeze=False)
    fig_cs.suptitle(f"Cross Sections Perpendicular to Trend (10km wide): {data['title']}", fontsize=16)
    axes_cs = axes_cs.flatten()

    for i, center_dist in enumerate(section_centers):
        ax = axes_cs[i]
        mask = (along_strike_dist >= center_dist - 5) & (along_strike_dist < center_dist + 5)
        n_events_in_section = np.sum(mask)

        if n_events_in_section > 0:
            ax.scatter(cross_strike_dist[mask], dep[mask], s=15, alpha=0.7)

        label = chr(ord('A') + i)
        ax.set_title(f"Section {label}-{label}' @ {center_dist:.0f} km ({n_events_in_section} events)")

        # Add compass direction to x-axis
        cs_angle_deg = np.rad2deg(angle + np.pi/2)
        dir_pos = angle_to_compass(cs_angle_deg)       # right side of plot (A')
        dir_neg = angle_to_compass(cs_angle_deg + 180) # left side of plot (A)

        ax.set_xlabel(f'Cross-strike distance (km)\n({dir_neg} <-> {dir_pos})')
        ax.set_ylabel('Depth (km)')
        ax.set_ylim(ZMAX, ZMIN)  # Inverted depth axis
        ax.set_xlim(cross_lim)
        ax.set_aspect('equal', adjustable='box')
        ax.grid(True)

    # Hide unused subplots
    for i in range(num_sections, len(axes_cs)):
        axes_cs[i].axis('off')

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    cs_filename = f"{output_dir}/{picker}_{stage}_cross_sections.png"
    plt.savefig(cs_filename)
    plt.close(fig_cs)


def main():
    """Main function to load data and generate plots."""
    pickers_to_plot = [p for p, plot in PLOT_PICKERS.items() if plot]
    stages_to_plot = [s for s, plot in PLOT_STAGES.items() if plot and s in STAGE_DATA_DEFINITIONS]

    if not pickers_to_plot or not stages_to_plot:
        print("No pickers or stages selected for plotting. Exiting.")
        return

    output_dir = "cross_section_plots"
    os.makedirs(output_dir, exist_ok=True)
    print(f"Saving plots to '{output_dir}/'")

    for stage in stages_to_plot:
        for picker in pickers_to_plot:
            print(f"Processing: {picker} - {stage}")
            stage_info = get_catalog_info(picker, stage)
            if not stage_info:
                print(f"  -> No definition found, skipping.")
                continue

            data = load_data(stage_info)

            if data and data['lon'].size > 0:
                process_and_plot_catalog(data, picker, stage, output_dir)
            else:
                print(f"  -> No data found or loaded, skipping.")

    print("\nDone.")


if __name__ == '__main__':
    main()
