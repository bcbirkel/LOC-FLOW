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
ZMIN, ZMAX = 0, 20           # Depth

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
    num_sections = 8
    min_along = np.min(along_strike_dist)
    max_along = np.max(along_strike_dist)

    # Create 8 equally spaced sections
    total_range = max_along - min_along
    if total_range == 0:
        total_range = 1.0  # km, arbitrary width when no along-strike extent
        min_along -= 0.5   # center events in this arbitrary range
    section_width = total_range / num_sections
    section_centers = min_along + section_width / 2 + np.arange(num_sections) * section_width

    # Determine cross-section length dynamically
    overall_min_cross, overall_max_cross = np.inf, -np.inf
    has_events_in_any_section = False
    for center_dist in section_centers:
        mask = np.abs(along_strike_dist - center_dist) < section_width / 2
        if np.any(mask):
            has_events_in_any_section = True
            section_cross_dist = cross_strike_dist[mask]
            overall_min_cross = min(overall_min_cross, np.min(section_cross_dist))
            overall_max_cross = max(overall_max_cross, np.max(section_cross_dist))

    if has_events_in_any_section:
        padding = (overall_max_cross - overall_min_cross) * 0.1
        if padding == 0: padding = 5 # Add padding if all points are at the same spot
        cross_lim = (overall_min_cross - padding, overall_max_cross + padding)
    else:
        # Fallback if no events are in any section
        cross_lim = (-20, 20)

    # --- 5. Create Combined Plot ---
    fig, axes = plt.subplots(3, 3, figsize=(18, 15), constrained_layout=True)
    fig.suptitle(f"{data['title']} ({len(x)} events)", fontsize=16)

    # --- Plot Map View (top-left) ---
    ax_map = axes[0, 0]
    sc = ax_map.scatter(x, y, s=15, c=dep, cmap='viridis_r', vmin=ZMIN, vmax=ZMAX, alpha=0.7, zorder=10)
    plt.colorbar(sc, ax=ax_map, label='Depth (km)', shrink=0.8)

    # Plot trend line
    x_fit = np.array([x.min() - 2, x.max() + 2])
    y_fit = m * x_fit + b
    ax_map.plot(x_fit, y_fit, 'r-', lw=2, label='Trend Line', zorder=20)

    # Plot cross-section lines and labels on map
    inv_rot_matrix = rot_matrix.T
    for i, center_dist in enumerate(section_centers):
        label = chr(ord('A') + i)
        # Endpoints for labels
        p1_rot = np.array([center_dist, cross_lim[0]])
        p2_rot = np.array([center_dist, cross_lim[1]])
        p1_xy = inv_rot_matrix @ p1_rot
        p2_xy = inv_rot_matrix @ p2_rot

        # Define corners of shaded box
        half_width = section_width / 2
        c1_rot = np.array([center_dist - half_width, cross_lim[0]])
        c2_rot = np.array([center_dist + half_width, cross_lim[0]])
        c3_rot = np.array([center_dist + half_width, cross_lim[1]])
        c4_rot = np.array([center_dist - half_width, cross_lim[1]])

        # Rotate corners back to map XY coords and plot
        corners_rot = np.array([c1_rot, c2_rot, c3_rot, c4_rot]).T
        corners_xy = inv_rot_matrix @ corners_rot
        ax_map.fill(corners_xy[0, :], corners_xy[1, :],
                    facecolor='gray', alpha=0.3, edgecolor='k', lw=1, zorder=5)

        # Add labels at ends with a small offset along the cross-section line direction
        offset_dist = 2.0  # km
        cs_vec = np.array([-np.sin(angle), np.cos(angle)]) # vector along cross-section
        offset = cs_vec * offset_dist
        ax_map.text(p1_xy[0] - offset[0], p1_xy[1] - offset[1], f"{label}",
                    va='center', ha='center', fontsize=10, color='k', fontweight='bold',
                    bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', boxstyle='round,pad=0.1'))
        ax_map.text(p2_xy[0] + offset[0], p2_xy[1] + offset[1], f"{label}'",
                    va='center', ha='center', fontsize=10, color='k', fontweight='bold',
                    bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', boxstyle='round,pad=0.1'))

    ax_map.set_xlabel('East-West distance from center (km)')
    ax_map.set_ylabel('North-South distance from center (km)')
    ax_map.set_title('Map View')
    ax_map.set_aspect('equal', adjustable='box')
    ax_map.grid(True)
    ax_map.legend()

    # --- Plot Cross Sections ---
    axes_cs = axes.flatten()[1:]
    for i, center_dist in enumerate(section_centers):
        ax = axes_cs[i]
        mask = np.abs(along_strike_dist - center_dist) < section_width / 2
        n_events_in_section = np.sum(mask)

        if n_events_in_section > 0:
            cs_x = cross_strike_dist[mask]
            cs_dep = dep[mask]
            ax.scatter(cs_x, cs_dep, s=15, c=cs_dep, cmap='viridis_r', vmin=ZMIN, vmax=ZMAX, alpha=0.7)

            if n_events_in_section > 1:
                # Fit line to determine dip
                m_cs, b_cs = np.polyfit(cs_x, cs_dep, 1)

                # Plot line
                x_line = np.array(cross_lim)
                y_line = m_cs * x_line + b_cs
                ax.plot(x_line, y_line, 'r-', lw=1.5, alpha=0.2)

                # Calculate and annotate dip
                dip = np.rad2deg(np.arctan(m_cs))
                ax.text(0.05, 0.95, f'Avg X-sect Dip: ~{dip:.1f}°',
                        transform=ax.transAxes, va='top', ha='left',
                        bbox=dict(facecolor='white', alpha=0.5, edgecolor='none', pad=0.2))

        label = chr(ord('A') + i)
        ax.set_title(f"Section {label}-{label}' @ {center_dist:.1f} km ({n_events_in_section} events)")

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

    filename = f"{output_dir}/{picker}_{stage}_cross_section_map.png"
    plt.savefig(filename)
    plt.close(fig)


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
