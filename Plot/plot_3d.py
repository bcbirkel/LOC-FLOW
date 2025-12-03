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
PICKERS = ['STALTA', 'PhaseNet', 'QMigrate']
STAGES = ['Initial', 'VELEST', 'hypoinverse', 'hypoinverse_corr', 'hypoDD_dtct']

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
            'path': './all_qm_events.csv',
            'cols': {'lon': 8, 'lat': 9, 'dep': 6}, # NOTE: Column indices are a guess
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

    # --- Create Interactive Plotly HTML ---
    fig = go.Figure()
    traces_metadata = []
    has_regional_events = False

    stage_color_map = {
        'Initial': 'red',
        'VELEST': 'orange',
        'hypoinverse': 'green',
        'hypoinverse_corr': 'blue',
        'hypoDD_dtct': 'purple',
        'hypoDD_dtcc': 'indigo',
        'GrowClust': 'violet'
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
            has_regional_events = True

    for stage in stages_to_plot:
        for picker in pickers_to_plot:
            stage_info = get_catalog_info(picker, stage)
            if not stage_info:
                continue

            data = load_data(stage_info)
            if data and len(data['lon']) > 0:
                color = stage_color_map.get(stage, 'black')
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
                traces_metadata.append({'picker': picker, 'stage': stage})

    # Create buttons for pickers
    picker_buttons = [
        dict(label="All",
             method="restyle",
             args=["visible", [True] * len(fig.data)])
    ]
    for picker in pickers_to_plot:
        visibility = [meta['picker'] == picker for meta in traces_metadata]
        if has_regional_events:
            visibility = [True] + visibility
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
        visibility = [meta['stage'] == stage for meta in traces_metadata]
        if has_regional_events:
            visibility = [True] + visibility
        stage_buttons.append(
            dict(label=stage,
                 method="restyle",
                 args=["visible", visibility])
        )

    fig.update_layout(
        title="Interactive 3D Earthquake Locations",
        scene=dict(
            xaxis_title="Longitude",
            yaxis_title="Latitude",
            zaxis_title="Depth (km)",
            xaxis=dict(range=[XMIN, XMAX]),
            yaxis=dict(range=[YMIN, YMAX]),
            zaxis=dict(range=[ZMAX, ZMIN]),  # Inverted Z-axis for depth
        ),
        legend=dict(title="Catalogs", traceorder='normal'),
        margin=dict(r=200),  # Add right margin for buttons
        updatemenus=[
            dict(
                type="buttons",
                direction="down",
                buttons=picker_buttons,
                x=1.1,
                xanchor="left",
                y=1.0,
                yanchor="top"
            ),
            dict(
                type="buttons",
                direction="down",
                buttons=stage_buttons,
                x=1.1,
                xanchor="left",
                y=0.6,
                yanchor="top"
            ),
        ],
        annotations=[
            dict(text="Pickers", x=1.02, y=1.02, xref="paper", yref="paper",
                 align="left", showarrow=False, xanchor="left", yanchor="bottom"),
            dict(text="Stages", x=1.02, y=0.62, xref="paper", yref="paper",
                 align="left", showarrow=False, xanchor="left", yanchor="bottom")
        ]
    )

    interactive_output = "3Dlocation_interactive.html"
    fig.write_html(interactive_output)
    print(f"Saved interactive plot to {interactive_output}")


if __name__ == '__main__':
    main()
