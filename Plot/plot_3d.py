#!/usr/bin/env python3
#
# plot location distribution in 3d
#
import os
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D  # Required for projection='3d'
import plotly.graph_objects as go

# --- CONFIGURATION ---

# Define the pickers and location stages to create a grid of plots
# PICKERS = ['STALTA', 'PhaseNet', 'QMigrate']
STAGES = ['Initial', 'VELEST', 'hypoinverse', 'hypoinverse_corr', 'hypoDD_dtct']
PICKERS = ['PhaseNet']
# STAGES = ['Initial', 'VELEST','hypoDD_dtct']


# Toggle which pickers and stages to plot
# Set to False to exclude a picker column or a stage row
PLOT_PICKERS = {picker: True for picker in PICKERS}
PLOT_STAGES = {stage: True for stage in STAGES}

# Add other stages from the original file, disabled by default
PLOT_STAGES['hypoDD_dtcc'] = False
PLOT_STAGES['GrowClust'] = False

# Add option to plot regional earthquakes from a catalog file
PLOT_REGIONAL_EVENTS = True
REGIONAL_EVENTS_FILE = 'Nepal_regional_events_starting2000.csv'

# Add option to plot station locations
PLOT_STATIONS = True
STATION_FILE = '../Data/station_full_filt.dat'

# This dictionary defines the data source for each stage.
# For stages that follow a consistent path pattern for each picker,
# use 'path_template' with {picker} as a placeholder.
# NOTE: For QMigrate, column indices are a guess and may need adjustment.
STAGE_DATA_DEFINITIONS = {
    'Initial': {
        # 'Initial' is a special case with different paths for each picker
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
        # 'filters': [{'col': 19, 'op': '>=', 'val': 0}]  # filter by nddp
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
XMIN, XMAX = 85, 86.5         # Longitude
YMIN, YMAX = 27, 28.5           # Latitude
ZMIN, ZMAX = -5, 25           # Depth
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
VIEW = (20, 5)
# 2D depth view (lon vs dep)
# VIEW = (0, 0)


# --- END CONFIGURATION ---


def set_axes_equal_3d(ax, lon, lat, dep, padding_factor=1.1):
    """Set 3D plot axes to equal scale."""
    if len(lon) == 0 or len(lat) == 0 or len(dep) == 0:
        return

    # Rough conversion: 1 degree lat ~= 111 km.
    # More accurate for lon: 111 * cos(lat).
    mean_lat_rad = np.deg2rad(np.mean(lat))
    km_per_deg_lon = 111.32 * np.cos(mean_lat_rad)
    km_per_deg_lat = 111.32

    # Find the range of the data in km
    min_lon, max_lon = np.min(lon), np.max(lon)
    min_lat, max_lat = np.min(lat), np.max(lat)
    min_dep, max_dep = np.min(dep), np.max(dep)

    range_lon_km = (max_lon - min_lon) * km_per_deg_lon
    range_lat_km = (max_lat - min_lat) * km_per_deg_lat
    range_dep_km = max_dep - min_dep

    # Find the maximum range
    max_range = max(range_lon_km, range_lat_km, range_dep_km) * padding_factor
    if max_range == 0: # handle single point case
        max_range = 1 # give it a 1km box

    # Calculate the center of the data
    mid_lon = (max_lon + min_lon) / 2
    mid_lat = (max_lat + min_lat) / 2
    mid_dep = (max_dep + min_dep) / 2

    # Set the limits
    ax.set_xlim(mid_lon - (max_range / 2 / km_per_deg_lon), mid_lon + (max_range / 2 / km_per_deg_lon))
    ax.set_ylim(mid_lat - (max_range / 2 / km_per_deg_lat), mid_lat + (max_range / 2 / km_per_deg_lat))
    ax.set_zlim(mid_dep - max_range / 2, mid_dep + max_range / 2)


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
        if path == './all_qm_events.csv':
            with open(path, 'r') as f:
                lines = [line.split() for line in f if line.strip()]
            data = np.array(lines, dtype=float)
        else:
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


def load_regional_data(filepath):
    """Load regional earthquake data from a CSV file."""
    if not os.path.exists(filepath):
        print(f"Warning: Regional events file not found: {filepath}")
        return None
    try:
        # Columns: time,latitude,longitude,depth,mag,...
        # Indices:      1        2         3
        data = np.loadtxt(filepath, delimiter=',', skiprows=1, usecols=(1, 2, 3))
        if data.ndim == 1:  # handle file with one line
            data = data.reshape(1, -1)
        lat = data[:, 0]
        lon = data[:, 1]
        dep = data[:, 2]

        # Filter by region
        mask = (lon >= XMIN) & (lon <= XMAX) & \
               (lat >= YMIN) & (lat <= YMAX) & \
               (dep >= ZMIN) & (dep <= ZMAX)

        return {'lon': lon[mask], 'lat': lat[mask], 'dep': dep[mask]}
    except Exception as e:
        print(f"Warning: Could not load or process regional data from {filepath}. Error: {e}")
        return None


def load_station_data(filepath):
    """Load station data from station_all.dat."""
    if not os.path.exists(filepath):
        print(f"Warning: Station file not found: {filepath}")
        return None
    stations = {}  # use dict to store unique stations by name
    try:
        with open(filepath, 'r') as f:
            for line in f:
                parts = line.split()
                if len(parts) < 6:
                    continue
                # lat lon net sta comp elev
                lat, lon, net, sta, elev = parts[0], parts[1], parts[2], parts[3], parts[5]
                station_name = f"{net}.{sta}"
                if station_name not in stations:
                    stations[station_name] = {
                        'lat': float(lat),
                        'lon': float(lon),
                        'dep': -float(elev),  # elev is negative depth
                        'name': station_name
                    }
        if not stations:
            return None

        # convert dict of dicts to dict of lists for plotly
        station_data = {
            'lon': [s['lon'] for s in stations.values()],
            'lat': [s['lat'] for s in stations.values()],
            'dep': [s['dep'] for s in stations.values()],
            'hovertext': [f"{s['name']}<br>Elev: {-s['dep']:.3f} km" for s in stations.values()]
        }
        return station_data
    except Exception as e:
        print(f"Warning: Could not load or process station data from {filepath}. Error: {e}")
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
    """Create a new figure with multiple 2D and 3D views and save it."""
    fig = plt.figure(figsize=(12, 10))
    fig.suptitle(f"{data['title']} ({len(data['lon'])} events)", fontsize=16)

    # 1. Lat vs Lon (map view)
    ax1 = fig.add_subplot(2, 2, 1)
    ax1.scatter(data['lon'], data['lat'], s=10, marker='o')
    ax1.set_title('Map View (Lon vs Lat)')
    ax1.set_xlabel('Longitude')
    ax1.set_ylabel('Latitude')
    ax1.set_xlim(XMIN, XMAX)
    ax1.set_ylim(YMIN, YMAX)
    ax1.set_xticks(np.arange(XMIN, XMAX + DX, DX))
    ax1.set_yticks(np.arange(YMIN, YMAX + DY, DY))
    ax1.grid(True)

    # 2. Lat vs Depth
    ax2 = fig.add_subplot(2, 2, 2)
    ax2.scatter(data['lat'], data['dep'], s=10, marker='o')
    ax2.set_title('Depth Profile (vs Latitude)')
    ax2.set_xlabel('Latitude')
    ax2.set_ylabel('Depth (km)')
    ax2.set_xlim(YMIN, YMAX)
    ax2.set_ylim(ZMIN, ZMAX)
    ax2.set_xticks(np.arange(YMIN, YMAX + DY, DY))
    ax2.set_yticks(np.arange(ZMIN, ZMAX + DZ, DZ))
    ax2.invert_yaxis()
    ax2.grid(True)

    # 3. Lon vs Depth
    ax3 = fig.add_subplot(2, 2, 3)
    ax3.scatter(data['lon'], data['dep'], s=10, marker='o')
    ax3.set_title('Depth Profile (vs Longitude)')
    ax3.set_xlabel('Longitude')
    ax3.set_ylabel('Depth (km)')
    ax3.set_xlim(XMIN, XMAX)
    ax3.set_ylim(ZMIN, ZMAX)
    ax3.set_xticks(np.arange(XMIN, XMAX + DX, DX))
    ax3.set_yticks(np.arange(ZMIN, ZMAX + DZ, DZ))
    ax3.invert_yaxis()
    ax3.grid(True)

    # 4. 3D view
    ax4 = fig.add_subplot(2, 2, 4, projection='3d')
    ax4.scatter(data['lon'], data['lat'], data['dep'], s=10, marker='o', depthshade=True)
    ax4.set_title('3D View')
    ax4.set_xlabel('Longitude')
    ax4.set_ylabel('Latitude')
    ax4.set_zlabel('Depth (km)')
    ax4.set_xlim(XMIN, XMAX)
    ax4.set_ylim(YMIN, YMAX)
    ax4.set_zlim(ZMIN, ZMAX)
    ax4.set_xticks(np.arange(XMIN, XMAX + DX, DX))
    ax4.set_yticks(np.arange(YMIN, YMAX + DY, DY))
    ax4.set_zticks(np.arange(ZMIN, ZMAX + DZ, DZ))
    ax4.invert_zaxis()
    ax4.view_init(elev=VIEW[1], azim=VIEW[0])

    plt.tight_layout(rect=[0, 0, 1, 0.96])  # Adjust for suptitle
    filename = f"{output_dir}/{picker}_{stage}.png"
    plt.savefig(filename)
    plt.close(fig)


def save_individual_zoomed_plot(data, picker, stage, output_dir):
    """Create a new figure with multiple 2D and 3D views (zoomed) and save it."""
    fig = plt.figure(figsize=(12, 10))
    fig.suptitle(f"{data['title']} ({len(data['lon'])} events) - Zoomed", fontsize=16)

    padding_factor = 1.1
    min_lon, max_lon = np.min(data['lon']), np.max(data['lon'])
    min_lat, max_lat = np.min(data['lat']), np.max(data['lat'])
    min_dep, max_dep = np.min(data['dep']), np.max(data['dep'])

    range_lon = (max_lon - min_lon) * padding_factor
    range_lat = (max_lat - min_lat) * padding_factor
    range_dep = (max_dep - min_dep) * padding_factor
    if range_lon == 0: range_lon = 0.01
    if range_lat == 0: range_lat = 0.01
    if range_dep == 0: range_dep = 1.0

    mid_lon = (max_lon + min_lon) / 2
    mid_lat = (max_lat + min_lat) / 2
    mid_dep = (max_dep + min_dep) / 2

    # 1. Lat vs Lon (map view)
    ax1 = fig.add_subplot(2, 2, 1)
    ax1.scatter(data['lon'], data['lat'], s=10, marker='o')
    ax1.set_title('Map View (Lon vs Lat)')
    ax1.set_xlabel('Longitude')
    ax1.set_ylabel('Latitude')
    ax1.set_xlim(mid_lon - range_lon/2, mid_lon + range_lon/2)
    ax1.set_ylim(mid_lat - range_lat/2, mid_lat + range_lat/2)
    ax1.set_aspect('equal', adjustable='box')
    ax1.grid(True)

    # 2. Lat vs Depth
    ax2 = fig.add_subplot(2, 2, 2)
    ax2.scatter(data['lat'], data['dep'], s=10, marker='o')
    ax2.set_title('Depth Profile (vs Latitude)')
    ax2.set_xlabel('Latitude')
    ax2.set_ylabel('Depth (km)')
    ax2.set_xlim(mid_lat - range_lat/2, mid_lat + range_lat/2)
    ax2.set_ylim(mid_dep - range_dep/2, mid_dep + range_dep/2)
    ax2.invert_yaxis()
    ax2.grid(True)

    # 3. Lon vs Depth
    ax3 = fig.add_subplot(2, 2, 3)
    ax3.scatter(data['lon'], data['dep'], s=10, marker='o')
    ax3.set_title('Depth Profile (vs Longitude)')
    ax3.set_xlabel('Longitude')
    ax3.set_ylabel('Depth (km)')
    ax3.set_xlim(mid_lon - range_lon/2, mid_lon + range_lon/2)
    ax3.set_ylim(mid_dep - range_dep/2, mid_dep + range_dep/2)
    ax3.invert_yaxis()
    ax3.grid(True)

    # 4. 3D view
    ax4 = fig.add_subplot(2, 2, 4, projection='3d')
    ax4.scatter(data['lon'], data['lat'], data['dep'], s=10, marker='o', depthshade=True)
    ax4.set_title('3D View (Zoomed, 1:1:1)')
    ax4.set_xlabel('Longitude')
    ax4.set_ylabel('Latitude')
    ax4.set_zlabel('Depth (km)')
    set_axes_equal_3d(ax4, data['lon'], data['lat'], data['dep'])
    ax4.invert_zaxis()
    ax4.view_init(elev=VIEW[1], azim=VIEW[0])

    plt.tight_layout(rect=[0, 0, 1, 0.96])  # Adjust for suptitle
    filename = f"{output_dir}/{picker}_{stage}_zoomed.png"
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
    output_dir_zoomed = "individual_plots_zoomed"
    os.makedirs(output_dir_zoomed, exist_ok=True)

    regional_data = load_regional_data(REGIONAL_EVENTS_FILE) if PLOT_REGIONAL_EVENTS else None

    for i, stage in enumerate(stages_to_plot):
        for j, picker in enumerate(pickers_to_plot):
            ax = axes[i, j]

            if stage == 'Initial' and regional_data:
                ax.scatter(regional_data['lon'], regional_data['lat'], regional_data['dep'],
                           s=5, c='lightgrey', marker='o', depthshade=True)

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
                save_individual_zoomed_plot(data, picker, stage, output_dir_zoomed)

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

    # --- One picker, all stages plots ---
    output_dir_onepicker = "onepicker_allstages"
    os.makedirs(output_dir_onepicker, exist_ok=True)
    output_dir_onepicker_zoomed = "onepicker_allstages_zoomed"
    os.makedirs(output_dir_onepicker_zoomed, exist_ok=True)

    for picker in pickers_to_plot:
        fig, axes_onepicker = plt.subplots(n_rows, 1, figsize=(6, 5 * n_rows),
                                           subplot_kw={'projection': '3d'}, squeeze=False)
        fig.suptitle(f"Picker: {picker}", fontsize=16)

        fig_zoomed, axes_onepicker_zoomed = plt.subplots(n_rows, 1, figsize=(6, 5 * n_rows),
                                                       subplot_kw={'projection': '3d'}, squeeze=False)
        fig_zoomed.suptitle(f"Picker: {picker} (Zoomed, 1:1:1)", fontsize=16)

        # Gather all data for this picker to determine global zoom bounds
        all_lon, all_lat, all_dep = [], [], []
        for stage in stages_to_plot:
            stage_info = get_catalog_info(picker, stage)
            if not stage_info: continue
            data = load_data(stage_info)
            if data and len(data['lon']) > 0:
                all_lon.extend(data['lon'])
                all_lat.extend(data['lat'])
                all_dep.extend(data['dep'])

        for i, stage in enumerate(stages_to_plot):
            ax = axes_onepicker[i, 0]
            ax_zoomed = axes_onepicker_zoomed[i, 0]

            stage_info = get_catalog_info(picker, stage)
            if not stage_info:
                for a, title in [(ax, f"{stage}\n(No definition)"), (ax_zoomed, f"{stage}\n(No definition)")]:
                    a.set_title(title)
                    a.axis('off')
                continue

            data = load_data(stage_info)
            if data and len(data['lon']) > 0:
                plot_title = f"{stage_info['title']} ({len(data['lon'])} events)"
                # Full region plot
                ax.scatter(data['lon'], data['lat'], data['dep'], s=10, marker='o', depthshade=True)
                ax.set_xlim(XMIN, XMAX)
                ax.set_ylim(YMIN, YMAX)
                ax.set_zlim(ZMIN, ZMAX)
                ax.invert_zaxis()
                ax.view_init(elev=VIEW[1], azim=VIEW[0])
                # Zoomed plot
                ax_zoomed.scatter(data['lon'], data['lat'], data['dep'], s=10, marker='o', depthshade=True)
                set_axes_equal_3d(ax_zoomed, np.array(all_lon), np.array(all_lat), np.array(all_dep))
                ax_zoomed.invert_zaxis()
                ax_zoomed.view_init(elev=VIEW[1], azim=VIEW[0])
            else:
                plot_title = f"{stage_info.get('title', f'{picker} - {stage}')}\n(No data)"
                ax.axis('off')
                ax_zoomed.axis('off')

            ax.set_title(plot_title)
            ax_zoomed.set_title(plot_title)
            for a in [ax, ax_zoomed]:
                if a.axison:
                    a.set_ylabel('Latitude')
                    if i == n_rows - 1:
                        a.set_xlabel('Longitude')
                    a.set_zlabel('Depth (km)')

        fig.tight_layout(rect=[0, 0, 1, 0.96])
        fig.savefig(f"{output_dir_onepicker}/{picker}_all_stages.png")
        plt.close(fig)
        
        fig_zoomed.tight_layout(rect=[0, 0, 1, 0.96])
        fig_zoomed.savefig(f"{output_dir_onepicker_zoomed}/{picker}_all_stages_zoomed.png")
        plt.close(fig_zoomed)
    print(f"Saved one-picker-all-stages plots to '{output_dir_onepicker}/' directory.")
    print(f"Saved one-picker-all-stages (zoomed) plots to '{output_dir_onepicker_zoomed}/' directory.")

    # --- All pickers, one stage plots ---
    output_dir_onestage = "allpickers_onestage"
    os.makedirs(output_dir_onestage, exist_ok=True)
    output_dir_onestage_zoomed = "allpickers_onestage_zoomed"
    os.makedirs(output_dir_onestage_zoomed, exist_ok=True)

    for stage in stages_to_plot:
        fig, axes_onestage = plt.subplots(1, n_cols, figsize=(6 * n_cols, 5),
                                          subplot_kw={'projection': '3d'}, squeeze=False)
        fig.suptitle(f"Stage: {stage}", fontsize=16)

        fig_zoomed, axes_onestage_zoomed = plt.subplots(1, n_cols, figsize=(6 * n_cols, 5),
                                                        subplot_kw={'projection': '3d'}, squeeze=False)
        fig_zoomed.suptitle(f"Stage: {stage} (Zoomed, 1:1:1)", fontsize=16)

        # Gather all data for this stage to determine global zoom bounds
        all_lon, all_lat, all_dep = [], [], []
        for picker in pickers_to_plot:
            stage_info = get_catalog_info(picker, stage)
            if not stage_info: continue
            data = load_data(stage_info)
            if data and len(data['lon']) > 0:
                all_lon.extend(data['lon'])
                all_lat.extend(data['lat'])
                all_dep.extend(data['dep'])

        for j, picker in enumerate(pickers_to_plot):
            ax = axes_onestage[0, j]
            ax_zoomed = axes_onestage_zoomed[0, j]

            stage_info = get_catalog_info(picker, stage)
            if not stage_info:
                for a, title in [(ax, f"{picker}\n(No definition)"), (ax_zoomed, f"{picker}\n(No definition)")]:
                    a.set_title(title)
                    a.axis('off')
                continue

            data = load_data(stage_info)
            if data and len(data['lon']) > 0:
                plot_title = f"{stage_info['title']} ({len(data['lon'])} events)"
                # Full region plot
                ax.scatter(data['lon'], data['lat'], data['dep'], s=10, marker='o', depthshade=True)
                ax.set_xlim(XMIN, XMAX)
                ax.set_ylim(YMIN, YMAX)
                ax.set_zlim(ZMIN, ZMAX)
                ax.invert_zaxis()
                ax.view_init(elev=VIEW[1], azim=VIEW[0])
                # Zoomed plot
                ax_zoomed.scatter(data['lon'], data['lat'], data['dep'], s=10, marker='o', depthshade=True)
                set_axes_equal_3d(ax_zoomed, np.array(all_lon), np.array(all_lat), np.array(all_dep))
                ax_zoomed.invert_zaxis()
                ax_zoomed.view_init(elev=VIEW[1], azim=VIEW[0])
            else:
                plot_title = f"{stage_info.get('title', f'{picker} - {stage}')}\n(No data)"
                ax.axis('off')
                ax_zoomed.axis('off')

            ax.set_title(plot_title)
            ax_zoomed.set_title(plot_title)
            for a in [ax, ax_zoomed]:
                if a.axison:
                    a.set_xlabel('Longitude')
                    if j == 0:
                        a.set_ylabel('Latitude')
                        a.set_zlabel('Depth (km)')

        fig.tight_layout(rect=[0, 0, 1, 0.96])
        fig.savefig(f"{output_dir_onestage}/{stage}_all_pickers.png")
        plt.close(fig)

        fig_zoomed.tight_layout(rect=[0, 0, 1, 0.96])
        fig_zoomed.savefig(f"{output_dir_onestage_zoomed}/{stage}_all_pickers_zoomed.png")
        plt.close(fig_zoomed)
    print(f"Saved all-pickers-one-stage plots to '{output_dir_onestage}/' directory.")
    print(f"Saved all-pickers-one-stage (zoomed) plots to '{output_dir_onestage_zoomed}/' directory.")

    plt.show()

    # --- Create Interactive Plotly HTML ---
    # Collect all final hypoDD points to calculate an average surface
    hypoDD_lons, hypoDD_lats, hypoDD_deps = [], [], []
    final_hypoDD_stage = 'hypoDD_dtct'
    if final_hypoDD_stage in stages_to_plot:
        for picker in pickers_to_plot:
            stage_info = get_catalog_info(picker, final_hypoDD_stage)
            if not stage_info:
                continue
            data = load_data(stage_info)
            if data and len(data['lon']) > 0:
                hypoDD_lons.extend(data['lon'])
                hypoDD_lats.extend(data['lat'])
                hypoDD_deps.extend(data['dep'])

    fig = go.Figure()
    traces_metadata = []
    has_regional_events = False
    has_stations = False
    all_lats_for_aspect = []
    has_surface = False

    stage_color_map = {
        'Initial': ['#ff6666', '#ff0000', '#cc0000'],          # Reds
        'VELEST': ['#ffc266', '#ffa31a', '#e68a00'],         # Oranges
        'hypoinverse': ['#99ff99', '#4dff4d', '#00cc00'],    # Greens
        'hypoinverse_corr': ['#80bfff', '#3399ff', '#0066cc'], # Blues
        'hypoDD_dtct': ['#DDA0DD', '#BA55D3', '#9932CC'],    # Purples/Orchids
        'hypoDD_dtcc': ['#b3b3ff', '#8080ff', '#4d4dff'],    # Indigos
        'GrowClust': ['#ff99ff', '#ff4dff', '#ff00ff']       # Violets
    }
    picker_symbol_map = {
        'STALTA': 'circle',
        'PhaseNet': 'cross',
        'QMigrate': 'diamond',
    }

    if PLOT_REGIONAL_EVENTS:
        regional_data = load_regional_data(REGIONAL_EVENTS_FILE)
        if regional_data and len(regional_data['lon']) > 0:
            fig.add_trace(go.Scatter3d(
                x=regional_data['lon'],
                y=regional_data['lat'],
                z=regional_data['dep'],
                mode='markers',
                marker=dict(size=2.5, color='grey'),
                name='Regional Events'
            ))
            all_lats_for_aspect.extend(regional_data['lat'])
            has_regional_events = True

    if PLOT_STATIONS:
        station_data = load_station_data(STATION_FILE)
        if station_data:
            fig.add_trace(go.Scatter3d(
                x=station_data['lon'],
                y=station_data['lat'],
                z=station_data['dep'],
                mode='markers',
                marker=dict(size=4, color='black', symbol='diamond'),
                name='Stations',
                hovertext=station_data['hovertext'],
                hoverinfo='text'
            ))
            all_lats_for_aspect.extend(station_data['lat'])
            has_stations = True

    for stage in stages_to_plot:
        for picker in pickers_to_plot:
            stage_info = get_catalog_info(picker, stage)
            if not stage_info:
                continue

            data = load_data(stage_info)
            if data and len(data['lon']) > 0:
                picker_index = pickers_to_plot.index(picker)
                colors = stage_color_map.get(stage, ['black', 'grey', 'dimgray'])
                color = colors[picker_index % len(colors)]
                symbol = picker_symbol_map.get(picker, 'circle')
                fig.add_trace(go.Scatter3d(
                    x=data['lon'],
                    y=data['lat'],
                    z=data['dep'],
                    mode='markers',
                    marker=dict(
                        size=3,
                        color=color,
                        symbol=symbol
                    ),
                    name=f"{picker} - {stage}",
                    visible=True
                ))
                all_lats_for_aspect.extend(data['lat'])
                traces_metadata.append({'picker': picker, 'stage': stage})

    # Create and add the median hypoDD surface if data is available
    if len(hypoDD_lons) > 0:
        try:
            # Combine into a single array and filter out depth outliers (keep middle 80%)
            all_points = np.array([hypoDD_lons, hypoDD_lats, hypoDD_deps]).T
            depths = all_points[:, 2]
            p10 = np.percentile(depths, 10)
            p90 = np.percentile(depths, 90)
            mask = (depths >= p10) & (depths <= p90)
            filtered_points = all_points[mask]

            if filtered_points.shape[0] > 2:  # Need at least 3 points to define a plane
                # Fit a plane to the points to represent the dipping seismicity
                median_point = np.median(filtered_points, axis=0)
                centered_points = filtered_points - median_point
                _, _, vh = np.linalg.svd(centered_points)
                normal = vh[2, :]

                # Create a grid for the surface. Use meshgrid for clarity.
                lon_vals = np.array([XMIN, XMAX])
                lat_vals = np.array([YMIN, YMAX])
                lon_grid, lat_grid = np.meshgrid(lon_vals, lat_vals)

                # Calculate z (depth) values for the plane
                # Plane equation: a(x-x0)+b(y-y0)+c(z-z0)=0 => z = z0 - (a(x-x0) + b(y-y0))/c
                if normal[2] != 0:
                    dep_grid = median_point[2] - (normal[0] * (lon_grid - median_point[0]) + normal[1] * (lat_grid - median_point[1])) / normal[2]
                else: # Handle vertical plane case, though unlikely
                    print("Warning: Best-fit plane is vertical. Creating a flat surface at median depth instead.")
                    dep_grid = np.full_like(lon_grid, median_point[2])

                # Add surface trace
                fig.add_trace(go.Surface(
                    x=lon_vals,
                    y=lat_vals,
                    z=dep_grid,
                    colorscale='Viridis',
                    opacity=0.5,
                    showscale=False,
                    name='hypoDD Median Surface',
                    visible=True
                ))
                has_surface = True
            else:
                print("Warning: Not enough points for hypoDD surface after depth filtering.")
        except Exception as e:
            print(f"Warning: Could not create hypoDD median surface. Error: {e}")

    # Create buttons for pickers
    num_special_traces = 0
    if has_regional_events:
        num_special_traces += 1
    if has_stations:
        num_special_traces += 1

    picker_buttons = [
        dict(label="All",
             method="restyle",
             args=["visible", [True] * len(fig.data)])
    ]
    for picker in pickers_to_plot:
        visibility = [True if meta['picker'] == picker else 'legendonly' for meta in traces_metadata]
        if num_special_traces > 0:
            visibility = [True] * num_special_traces + visibility
        picker_buttons.append(
            dict(label=picker,
                 method="restyle",
                 args=["visible", visibility])
        )

    # Create buttons for stages
    stage_buttons = [
        dict(label="All",
             method="restyle",
             args=["visible", [True] * len(fig.data)])
    ]
    for stage in stages_to_plot:
        visibility = [True if meta['stage'] == stage else 'legendonly' for meta in traces_metadata]
        if num_special_traces > 0:
            visibility = [True] * num_special_traces + visibility
        stage_buttons.append(
            dict(label=stage,
                 method="restyle",
                 args=["visible", visibility])
        )

    # Define compass properties
    compass_lon = XMIN + (XMAX - XMIN) * 0.1
    compass_lat = YMAX - (YMAX - YMIN) * 0.1
    compass_z = ZMIN + (ZMAX - ZMIN) * 0.05  # Place it near the top surface
    compass_d_lat = (YMAX - YMIN) * 0.05
    compass_d_lon = (XMAX - XMIN) * 0.05

    scene_settings = dict(
        xaxis_title="Longitude",
        yaxis_title="Latitude",
        zaxis_title="Depth (km)",
        xaxis=dict(range=[XMIN, XMAX], showticklabels=True, showbackground=True),
        yaxis=dict(range=[YMIN, YMAX], showticklabels=True, showbackground=True),
        zaxis=dict(range=[ZMAX, ZMIN], showticklabels=True, showbackground=True),  # Inverted Z-axis for depth
        camera=dict(eye=dict(x=2.5, y=2.5, z=2.5)),
        annotations=[
            # Compass
            dict(x=compass_lon, y=compass_lat + compass_d_lat, z=compass_z, text="N", showarrow=False, font=dict(color='black', size=14, family='Arial')),
            dict(x=compass_lon, y=compass_lat - compass_d_lat, z=compass_z, text="S", showarrow=False, font=dict(color='black', size=14, family='Arial')),
            dict(x=compass_lon + compass_d_lon, y=compass_lat, z=compass_z, text="E", showarrow=False, font=dict(color='black', size=14, family='Arial')),
            dict(x=compass_lon - compass_d_lon, y=compass_lat, z=compass_z, text="W", showarrow=False, font=dict(color='black', size=14, family='Arial')),
        ]
    )
    if all_lats_for_aspect:
        mean_lat = np.mean(all_lats_for_aspect)
        km_per_deg_lat = 111.32
        km_per_deg_lon = km_per_deg_lat * np.cos(np.deg2rad(mean_lat))

        range_lon_km = (XMAX - XMIN) * km_per_deg_lon
        range_lat_km = (YMAX - YMIN) * km_per_deg_lat
        range_dep_km = ZMAX - ZMIN

        scene_settings['aspectmode'] = 'manual'
        scene_settings['aspectratio'] = dict(x=range_lon_km, y=range_lat_km, z=range_dep_km)

    updatemenus = [
        dict(
            type="buttons",
            direction="down",
            buttons=picker_buttons,
            x=0.3,
            xanchor="center",
            y=-0.15,
            yanchor="top"
        ),
        dict(
            type="buttons",
            direction="down",
            buttons=stage_buttons,
            x=0.7,
            xanchor="center",
            y=-0.15,
            yanchor="top"
        ),
    ]

    annotations = [
        dict(text="Pickers", x=0.3, y=-0.08, xref="paper", yref="paper",
             align="center", showarrow=False, xanchor="center", yanchor="bottom"),
        dict(text="Stages", x=0.7, y=-0.08, xref="paper", yref="paper",
             align="center", showarrow=False, xanchor="center", yanchor="bottom")
    ]

    if has_surface:
        surface_buttons = [
            dict(label="Show Median Surface", method="restyle", args=[{"visible": [True]}, [-1]]),
            dict(label="Hide Median Surface", method="restyle", args=[{"visible": [False]}, [-1]])
        ]
        updatemenus.append(dict(
            type="buttons",
            direction="right",
            buttons=surface_buttons,
            x=0.5,
            xanchor="center",
            y=-0.25,
            yanchor="top"
        ))
        annotations.append(
            dict(text="Median Surface", x=0.5, y=-0.18, xref="paper", yref="paper",
                 align="center", showarrow=False, xanchor="center", yanchor="bottom")
        )

    fig.update_layout(
        title="Interactive 3D Earthquake Locations",
        width=1200,
        height=900,
        scene=scene_settings,
        legend=dict(title="Catalogs", traceorder='normal'),
        margin=dict(r=200, b=200),  # Increased bottom margin for new buttons
        updatemenus=updatemenus,
        annotations=annotations
    )

    interactive_output = "3Dlocation_interactive.html"
    fig.write_html(interactive_output)
    print(f"Saved interactive plot to {interactive_output}")


if __name__ == '__main__':
    main()
