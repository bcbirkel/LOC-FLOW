#!/usr/bin/env python3
#
# plot location distribution in 3d
#
import os
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # Required for projection='3d'

# --- CONFIGURATION ---

# Toggle which stages to plot
PLOT_STAGES = {
    'REAL': True,
    'VELEST': True,
    'hypoinverse': True,
    'hypoinverse_corr': True,
    'hypoDD_dtct': True,
    'hypoDD_dtcc': False, # Disabled by default as in matlab script
    'GrowClust': False,   # Disabled by default as in matlab script
}

# Data files and column indices (0-indexed)
# For filters, `col` is the column index, `op` is the operator (e.g., '>=', '=='), and `val` is the value.
STAGE_DATA = {
    'REAL': {
        'path': '../REAL/catalogSA_allday.txt',
        'cols': {'lon': 7, 'lat': 6, 'dep': 8},
        'title': 'REAL catalog (SA)'
    },
    'VELEST': {
        'path': '../location/VELEST/new.cat',
        'cols': {'lon': 5, 'lat': 4, 'dep': 6},
        'title': 'VELEST catalog'
    },
    'hypoinverse': {
        'path': '../location/hypoinverse/new.cat',
        'cols': {'lon': 5, 'lat': 4, 'dep': 6},
        'title': 'HYPOINVERSE catalog'
    },
    'hypoinverse_corr': {
        'path': '../location/hypoinverse_corr/new.cat',
        'cols': {'lon': 5, 'lat': 4, 'dep': 6},
        'title': 'HYPOINVERSE_corr catalog'
    },
    'hypoDD_dtct': {
        'path': '../hypoDD_dtct/hypoDD.reloc',
        'cols': {'lon': 2, 'lat': 1, 'dep': 3},
        'title': 'hypoDD catalog (dt.ct)',
        'filters': [{'col': 19, 'op': '>=', 'val': 0}]  # filter by nddp
    },
    'hypoDD_dtcc': {
        'path': '../hypoDD_dtcc/hypoDD.reloc',
        'cols': {'lon': 2, 'lat': 1, 'dep': 3},
        'title': 'hypoDD catalog (dt.cc)',
        'filters': [{'col': 17, 'op': '>=', 'val': 0}]  # filter by nddp
    },
    'GrowClust': {
        'path': '../GrowClust/OUT/out.growclust_cat',
        'alt_path': '../MatchLocate/GrowClust/OUT/out.growclust_cat',
        'cols': {'lon': 8, 'lat': 7, 'dep': 9},
        'title': 'GrowClust catalog',
        'filters': [
            {'col': 14, 'op': '>=', 'val': 0},  # filter by npar
            {'col': 15, 'op': '>=', 'val': 0}   # filter by nddp
        ]
    }
}

# Filter values for relocations
# you may only show those events with P's DT or CC constraints
# also consider useall=0 in hypoDD_dtcc/run_hypoDD_dtcc.sh and GrowClust/IN/gen_input.pl
nddp = 0
npar = 0
if 'hypoDD_dtct' in STAGE_DATA and STAGE_DATA['hypoDD_dtct'].get('filters'):
    STAGE_DATA['hypoDD_dtct']['filters'][0]['val'] = nddp
if 'hypoDD_dtcc' in STAGE_DATA and STAGE_DATA['hypoDD_dtcc'].get('filters'):
    STAGE_DATA['hypoDD_dtcc']['filters'][0]['val'] = nddp
if 'GrowClust' in STAGE_DATA and STAGE_DATA['GrowClust'].get('filters'):
    STAGE_DATA['GrowClust']['filters'][0]['val'] = npar
    STAGE_DATA['GrowClust']['filters'][1]['val'] = nddp

# Plotting region (manually specify)
# The whole region
XMIN, XMAX = 27, 29           # Longitude
YMIN, YMAX = 85, 86.2         # Latitude
ZMIN, ZMAX = -5, 40           # Depth
DX, DY, DZ = 0.2, 0.2, 5      # Ticks step

# The zoomed region (one-day data from matlab script)
# XMIN, XMAX = 13.31, 13.338
# YMIN, YMAX = 42.635, 42.655
# ZMIN, ZMAX = 7.8, 11
# DX, DY, DZ = 0.004, 0.003, 0.5

# View angles (azimuth, elevation)
# 2D map view (lon vs lat)
VIEW = (0, 90)
# 3D view
# VIEW = (23, 15)
# 2D depth view (lon vs dep)
# VIEW = (0, 0)

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


def main():
    """Main function to load data and generate plots."""
    stages_to_plot = [name for name, plot in PLOT_STAGES.items() if plot]

    plot_data = []
    for stage_name in stages_to_plot:
        data = load_data(STAGE_DATA[stage_name])
        if data and len(data['lon']) > 0:
            plot_data.append(data)
        elif data is not None:
            print(f"Info: No events to plot for '{data['title']}' within the specified region.")


    if not plot_data:
        print("No data to plot. Exiting.")
        return

    n_plots = len(plot_data)
    cols = int(np.ceil(np.sqrt(n_plots)))
    rows = int(np.ceil(n_plots / cols))

    fig = plt.figure(figsize=(6 * cols, 5 * rows))

    for i, data in enumerate(plot_data):
        ax = fig.add_subplot(rows, cols, i + 1, projection='3d')

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
        ax.view_init(elev=VIEW[1], azim=VIEW[0])

    plt.tight_layout()
    plt.savefig('3Dlocation.jpg')
    # plt.savefig('3Dlocation.pdf')
    print("Saved plot to 3Dlocation.jpg")
    plt.show()


if __name__ == '__main__':
    main()
