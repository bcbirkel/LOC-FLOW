import csv
import os
import shutil
import matplotlib.pyplot as plt


def get_station_center(station_file):
    """
    Calculates the geometric center (centroid) of the station array.
    """
    lons = []
    lats = []
    # Use 'utf-8-sig' to handle potential BOM at the start of the file
    try:
        with open(station_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f)
            header = next(reader)
            
            try:
                lon_idx = header.index('Longitude')
                lat_idx = header.index('Latitude')
            except ValueError as e:
                print(f"Error finding columns in station file: {e}")
                print(f"Header found: {header}")
                return None, None

            for row in reader:
                if row:
                    try:
                        lons.append(float(row[lon_idx]))
                        lats.append(float(row[lat_idx]))
                    except (ValueError, IndexError):
                        # Skip malformed rows
                        continue
    except FileNotFoundError:
        print(f"Error: Station file not found at {station_file}")
        return None, None
    
    if not lons or not lats:
        print("No station data found in file.")
        return None, None
        
    center_lon = sum(lons) / len(lons)
    center_lat = sum(lats) / len(lats)
    
    return center_lon, center_lat


def load_station_data(station_file):
    """
    Loads station locations from the station file.
    """
    stations = []
    try:
        with open(station_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    stations.append({
                        'lon': float(row['Longitude']),
                        'lat': float(row['Latitude'])
                    })
                except (ValueError, KeyError):
                    continue
    except FileNotFoundError:
        print(f"Error: Station file not found at {station_file}")
    return stations


def plot_central_events(all_central_events, stations, output_dir):
    """
    Plots the central events and station locations.
    """
    if not all_central_events:
        print("No central events to plot.")
        return

    fig, axes = plt.subplots(1, 3, figsize=(20, 6))
    fig.suptitle('Centrally Located Events', fontsize=16)

    # Plot 1: Lat vs Lon
    ax1 = axes[0]
    scatter1 = ax1.scatter(
        [e['lon'] for e in all_central_events],
        [e['lat'] for e in all_central_events],
        c=[e['depth'] for e in all_central_events],
        cmap='viridis_r',
        label='Events',
        zorder=10
    )
    ax1.scatter([s['lon'] for s in stations], [s['lat'] for s in stations], marker='^', c='black', label='Stations')
    for event in all_central_events:
        ax1.text(event['lon'], event['lat'], f"{event['catalog'][0]}{event['eqID']}", fontsize=8)
    ax1.set_xlabel('Longitude')
    ax1.set_ylabel('Latitude')
    ax1.set_title('Map View')
    ax1.legend()
    ax1.grid(True)
    ax1.set_aspect('equal', adjustable='box')

    # Plot 2: Lon vs Depth
    ax2 = axes[1]
    ax2.scatter(
        [e['lon'] for e in all_central_events],
        [e['depth'] for e in all_central_events],
        c=[e['depth'] for e in all_central_events],
        cmap='viridis_r'
    )
    for event in all_central_events:
        ax2.text(event['lon'], event['depth'], f"{event['catalog'][0]}{event['eqID']}", fontsize=8)
    ax2.set_xlabel('Longitude')
    ax2.set_ylabel('Depth (km)')
    ax2.set_title('Lon vs Depth')
    ax2.invert_yaxis()
    ax2.grid(True)

    # Plot 3: Lat vs Depth
    ax3 = axes[2]
    ax3.scatter(
        [e['lat'] for e in all_central_events],
        [e['depth'] for e in all_central_events],
        c=[e['depth'] for e in all_central_events],
        cmap='viridis_r'
    )
    for event in all_central_events:
        ax3.text(event['lat'], event['depth'], f"{event['catalog'][0]}{event['eqID']}", fontsize=8)
    ax3.set_xlabel('Latitude')
    ax3.set_ylabel('Depth (km)')
    ax3.set_title('Lat vs Depth')
    ax3.invert_yaxis()
    ax3.grid(True)

    # Add a colorbar
    # fig.colorbar(scatter1, ax=axes, label='Depth (km)', orientation='vertical', fraction=0.02, pad=0.04)

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plot_path = os.path.join(output_dir, 'central_events_summary.png')
    plt.savefig(plot_path, dpi=300)
    print(f"\nSaved summary plot to {plot_path}")
    plt.close(fig)


def process_catalog(catalog_file, center_lon, center_lat, num_events=20):
    """
    Finds the top N most central events in a catalog file and saves them.
    """
    events_with_dist = []
    try:
        with open(catalog_file, 'r') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                parts = line.split()
                try:
                    # lon is 9th column (index 8), lat is 10th (index 9)
                    event_lon = float(parts[8])
                    event_lat = float(parts[9])
                    
                    # Calculate squared Euclidean distance for sorting purposes
                    dist_sq = (event_lon - center_lon)**2 + (event_lat - center_lat)**2
                    
                    events_with_dist.append((dist_sq, line))
                except (ValueError, IndexError):
                    print(f"Skipping malformed line in {catalog_file}: {line}")
                    continue
    except FileNotFoundError:
        print(f"Error: Catalog file not found at {catalog_file}")
        return []

    # Sort events by distance (ascending)
    events_with_dist.sort(key=lambda x: x[0])
    
    # Get the top N events
    top_events = events_with_dist[:num_events]
    
    # Define output file path
    base, ext = os.path.splitext(catalog_file)
    output_file = f"{base}.central{ext}"
    
    output_dir_plots = 'central_events_records'
    catalog_name = os.path.splitext(os.path.basename(catalog_file))[0].split('.')[0]
    
    central_events_data = []

    try:
        with open(output_file, 'w') as f:
            for _, line in top_events:
                f.write(line + '\n')

                parts = line.split()
                eqID = parts[0]
                event_lon = float(parts[8])
                event_lat = float(parts[9])
                event_depth = float(parts[10])

                central_events_data.append({
                    'eqID': eqID,
                    'lon': event_lon,
                    'lat': event_lat,
                    'depth': event_depth,
                    'catalog': catalog_name
                })

                if catalog_name == "QMigrate":
                    plot_filename = f"qm.{eqID}.pickplot.png"
                if catalog_name == "PhaseNet":
                    plot_filename = f"pn.{eqID}.pickplot.png"
                source_plot_path = os.path.join('ConvertFiles', 'RecordSectionPicks', catalog_name, plot_filename)
                dest_plot_path = os.path.join(output_dir_plots, plot_filename)

                if os.path.exists(source_plot_path):
                    shutil.copy(source_plot_path, dest_plot_path)
                else:
                    print(f"Warning: Plot file not found at {source_plot_path}")

        print(f"Saved {len(top_events)} most central events to {output_file}")
    except IOError as e:
        print(f"Error writing to output file {output_file}: {e}")
    
    return central_events_data

def main():
    """
    Main function to run the script.
    """
    station_file = 'Data/all_station_list.csv'
    catalog_files = [
        'ConvertFiles/PhaseNet.hypoDD.tbl',
        'ConvertFiles/QMigrate.hypoDD.tbl'
    ]
    output_dir = 'central_events_records'
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"Calculating station center from {station_file}...")
    center_lon, center_lat = get_station_center(station_file)
    
    if center_lon is None or center_lat is None:
        print("Could not determine station center. Aborting.")
        return
        
    print(f"Station array center: Lon={center_lon:.4f}, Lat={center_lat:.4f}")
    
    all_central_events = []
    for catalog in catalog_files:
        print(f"\nProcessing {catalog}...")
        central_events = process_catalog(catalog, center_lon, center_lat, num_events=10)
        all_central_events.extend(central_events)

    if all_central_events:
        print("\nPlotting summary figure of central events...")
        stations = load_station_data(station_file)
        plot_central_events(all_central_events, stations, output_dir)


if __name__ == '__main__':
    main()
