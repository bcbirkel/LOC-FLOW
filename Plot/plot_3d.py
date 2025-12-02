#!/usr/bin/env python3
#
# plot location distribution in 3d
#
import os
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # Required for projection='3d'

# --- CONFIGURATION ---

# Define the pickers and location stages to create a grid of plots
PICKERS = ['STALTA', 'PhaseNet', 'QMigrate']
STAGES = ['Initial', 'VELEST', 'hypoinverse', 'hypoinverse_corr', 'hypoDD_dtct']

# Toggle which pickers and stages to plot
# Set to False to exclude a picker column or a stage row
PLOT_PICKERS = {picker: True for picker in PICKERS}
PLOT_STAGES = {stage: True for stage in STAGES}

# Add other stages from the original file, disabled by default
PLOT_STAGES['hypoDD_dtcc'] = False
PLOT_STAGES['GrowClust'] = False

# This dictionary defines the data source for each stage.
# For stages that follow a consistent path pattern for each picker,
# use 'path_template' with {picker} as a placeholder.
# NOTE: For QMigrate, column indices are a guess and may need adjustment.
STAGE_DATA_DEFINITIONS = {
    'Initial': {
        # 'Initial' is a special case with different paths for each picker
        'STALTA': {
            'path': '../REAL/runs/STALTA/catalogSA_allday.txt',
            'cols': {'lon': 6, 'lat': 7, 'dep': 8},
            'title': 'STALTA - REAL'
        },
        'PhaseNet': {
            'path': '../REAL/runs/PhaseNet/catalogSA_allday.txt',
            'cols': {'lon': 6, 'lat': 7, 'dep': 8},
            'title': 'PhaseNet - REAL'
        },
        'QMigrate': {
            'path': '../Pick/QMigrate/qmigrate.cat',
            'cols': {'lon': 4, 'lat': 5, 'dep': 6}, # NOTE: Column indices are a guess
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
        'cols': {'lon': 4, 'lat': 5, 'dep': 6},
        'title_template': '{picker} - HYPOINVERSE'
    },
    'hypoinverse_corr': {
        'path_template': '../location/hypoinverse_corr/{picker}/new.cat',
        'cols': {'lon': 4, 'lat': 5, 'dep': 6},
        'title_template': '{picker} - HYPOINVERSE_corr'
    },
    'hypoDD_dtct': {
        'path_template': '../hypoDD_dtct/{picker}/hypoDD.reloc',
        'cols': {'lon': 1, 'lat': 2, 'dep': 3},
        'title_template': '{picker} - hypoDD (dt.ct)',
        'filters': [{'col': 19, 'op': '>=', 'val': 0}]  # filter by nddp
    },
    'hypoDD_dtcc': {
        'path_template': '../hypoDD_dtcc/{picker}/hypoDD.reloc',
        'cols': {'lon': 1, 'lat': 2, 'dep': 3},
        'title_template': '{picker} - hypoDD (dt.cc)',
        'filters': [{'col': 17, 'op': '>=', 'val': 0}]  # filter by nddp
    },
    'GrowClust': {
        'path_template': '../GrowClust/{picker}/OUT/out.growclust_cat',
        'alt_path_template': '../MatchLocate/GrowClust/{picker}/OUT/out.growclust_cat',
        'cols': {'lon': 8, 'lat': 7, 'dep': 9},
        'title_template': '{picker} - GrowClust',
        'filters': [
            {'col': 14, 'op': '>=', 'val': 0},  # filter by npar
            {'col': 15, 'op': '>=', 'val': 0}   # filter by nddp
        ]
    }
}

# Plotting region (manually specify)
# The whole region
XMIN, XMAX = 85, 86.2         # Longitude
YMIN, YMAX = 26, 29           # Latitude
ZMIN, ZMAX = -5, 40           # Depth
DX, DY, DZ = 0.2, 0.2, 5      # Ticks step

# The zoomed region (one-day data from matlab script)
# XMIN, XMAX = 13.31, 13.338
# YMIN, YMAX = 42.635, 42.655
# ZMIN, ZMAX = 7.8, 11
# DX, DY, DZ = 0.004, 0.003, 0.5

# View angles for the main combined plot
# 2D map view (lon vs lat)
# VIEW = (0, 90)
# 3D view
VIEW = (23, 15)
# 2D depth view (lon vs dep)
# VIEW = (0, 0)

# View angles for saved individual PNG files
VIEWS_TO_SAVE = {
    'map': (0, 90),       # 2D map view (lon vs lat)
    '3d': (23, 15),        # 3D view
    'depth_lon': (0, 0),  # 2D depth view (lon vs dep)
    'depth_lat': (90, 0)  # 2D depth view (lat vs dep)
}

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


def save_individual_plot(data, picker, stage, output_dir):
    """Create a new figure for a single dataset and save it from multiple angles."""
    fig = plt.figure(figsize=(8, 7))
    ax = fig.add_subplot(111, projection='3d')

    ax.scatter(data['lon'], data['lat'], data['dep'], s=10, marker='o', depthshade=True)

    title = f"{data['title']} ({len(data['lon'])} events)"
    ax.set_title(title)

    ax.set_xlim(XMIN, XMAX)
    ax.set_ylim(YMIN, YMAX)
    ax.set_zlim(ZMIN, ZMAX)

    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    ax.set_zlabel('Depth (km)')

    ax.set_xticks(np.arange(XMIN, XMAX + DX, DX))
    ax.set_yticks(np.arange(YMIN, YMAX + DY, DY))
    ax.set_zticks(np.arange(ZMIN, ZMAX + DZ, DZ))

    ax.invert_zaxis()

    for view_name, (azim, elev) in VIEWS_TO_SAVE.items():
        ax.view_init(elev=elev, azim=azim)
        filename = f"{output_dir}/{picker}_{stage}_{view_name}.png"
        plt.savefig(filename)

    plt.close(fig)


def main():
    """Main function to load data and generate plots."""
    pickers_to_plot = [p for p, plot in PLOT_PICKERS.items() if plot]
    stages_to_plot = [s for s, plot in PLOT_STAGES.items() if plot and s in STAGE_DATA_DEFINITIONS]

    if not pickers_to_plot or not stages_to_plot:
        print("No pickers or stages selected for plotting. Exiting.")
        return

    n_cols = len(pickers_to_plot)
    n_rows = len(stages_to_plot)

    fig, axes = plt.subplots(n_rows, n_cols, figsize=(6 * n_cols, 5 * n_rows),
                             subplot_kw={'projection': '3d'}, squeeze=False)

    # Create output directory for individual plots
    output_dir = "individual_plots"
    os.makedirs(output_dir, exist_ok=True)

    for i, stage in enumerate(stages_to_plot):
        for j, picker in enumerate(pickers_to_plot):
            ax = axes[i, j]

            stage_info = get_catalog_info(picker, stage)
            if not stage_info:
                plot_title = f"{picker}\n{stage}\n(No definition)"
                ax.set_title(plot_title)
                ax.axis('off')
                continue

            data = load_data(stage_info)

            plot_title = ""
            if data and len(data['lon']) > 0:
                plot_title = f"{stage_info['title']} ({len(data['lon'])} events)"
                ax.scatter(data['lon'], data['lat'], data['dep'], s=10, marker='o', depthshade=True)
                save_individual_plot(data, picker, stage, output_dir)

                ax.set_xlim(XMIN, XMAX)
                ax.set_ylim(YMIN, YMAX)
                ax.set_zlim(ZMIN, ZMAX)
                ax.invert_zaxis()
                ax.view_init(elev=VIEW[1], azim=VIEW[0])
            else:
                plot_title = f"{stage_info.get('title', f'{picker} - {stage}')}\n(No data)"
                ax.axis('off')

            if i == 0:  # Add picker name to top row titles
                plot_title = f"{picker}\n{plot_title}"

            ax.set_title(plot_title)

            # Set labels only on outer axes to avoid clutter
            if ax.axison and j == 0:  # First column
                ax.set_ylabel('Latitude')
                ax.set_zlabel('Depth (km)')
            if ax.axison and i == n_rows - 1:  # Last row
                ax.set_xlabel('Longitude')

    plt.tight_layout()
    plt.savefig('3Dlocation_grid.jpg')
    # plt.savefig('3Dlocation_grid.pdf')
    print("Saved combined plot to 3Dlocation_grid.jpg")
    print(f"Saved individual plots to '{output_dir}/' directory.")
    plt.show()


if __name__ == '__main__':
    main()
