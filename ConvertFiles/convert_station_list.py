import csv
import os

def convert_station_list(input_csv, output_dat):
    """
    Converts a station list from CSV format to a .dat format.

    The output format is: lat lon net sta comp elev
    - Elevation is converted from meters to kilometers.
    - Each station gets three entries for components DPN, DPE, and DPZ.
    - Network is hardcoded to '4W'.
    """
    network_code = "4W"
    components = ["DPN", "DPE", "DPZ"]

    try:
        with open(input_csv, 'r', encoding='utf-8-sig') as infile, open(output_dat, 'w') as outfile:
            reader = csv.DictReader(infile)
            
            for row in reader:
                try:
                    station = row['Station']
                    lon = float(row['Longitude'])
                    lat = float(row['Latitude'])
                    elev_m = float(row['Elev'])
                    elev_km = elev_m / 1000.0

                    for comp in components:
                        # Format: lat lon net sta comp elev
                        line = f"{lat} {lon} {network_code} {station} {comp} {elev_km:.5f}\n"
                        outfile.write(line)

                except (ValueError, KeyError) as e:
                    print(f"Skipping malformed row: {row}. Error: {e}")
                    continue
        
        print(f"Successfully created {output_dat}")

    except FileNotFoundError:
        print(f"Error: Input file not found at {input_csv}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def main():
    """
    Main function to define file paths and run the conversion.
    """
    input_file = 'Data/all_station_list.csv'
    output_file = 'Data/all_stations.dat'
    
    print(f"Converting {input_file} to {output_file}...")
    convert_station_list(input_file, output_file)

if __name__ == '__main__':
    main()
