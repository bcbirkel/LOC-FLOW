#!/usr/bin/env python3
#
# Converts hypoDD.reloc files to a .tbl catalog format.
#
import os
import datetime

def main():
    """
    Finds hypoDD.reloc files for each picker, converts them to .tbl format,
    and saves the output.
    """
    pickers = ['STALTA', 'PhaseNet', 'QMigrate']
    base_dir = 'hypoDD_dtct'

    for picker in pickers:
        picker_dir = os.path.join(base_dir, picker)
        input_file = os.path.join(picker_dir, 'hypoDD.reloc')
        output_file = os.path.join(picker_dir, f'{picker}.hypoDD.tbl')

        if not os.path.exists(input_file):
            print(f"Warning: Input file not found, skipping: {input_file}")
            continue

        print(f"Processing {input_file} -> {output_file}")

        try:
            with open(input_file, 'r') as infile, open(output_file, 'w') as outfile:
                for line in infile:
                    parts = line.split()
                    if len(parts) < 17:
                        continue

                    # Parse columns from hypoDD.reloc:
                    # eqID lat lon depth x y z err_EW err_NS err_Z year month day hour minute second mag clusterID
                    eqID = int(parts[0])
                    lat = float(parts[1])
                    lon = float(parts[2])
                    depth = float(parts[3])
                    err_EW = float(parts[7])
                    err_NS = float(parts[8])
                    err_Z = float(parts[9])
                    year = int(parts[10])
                    month = int(parts[11])
                    day = int(parts[12])
                    hour = int(parts[13])
                    minute = int(parts[14])
                    second = float(parts[15])
                    mag = float(parts[16])

                    # Apply formatting rules
                    formatted_eqID = f"{eqID:03d}"

                    # Calculate Julian day
                    julian_day = datetime.date(year, month, day).timetuple().tm_yday

                    # Adjust magnitude
                    if mag > 3:
                        mag = 0.0

                    # Assemble the output line in the specified order:
                    # eqID, year, julian day, month, day, hour, min, sec, lon, lat, depth, mag, err_NS, err_EW, err_Z
                    output_line = (
                        f"{formatted_eqID} {year} {julian_day} {month} {day} "
                        f"{hour} {minute} {second:.2f} {lon:.4f} {lat:.4f} "
                        f"{depth:.3f} {mag:.2f} {err_NS:.4f} {err_EW:.4f} {err_Z:.4f}\n"
                    )

                    outfile.write(output_line)
            print("  -> Done.")

        except Exception as e:
            print(f"Error processing file {input_file}: {e}")

if __name__ == '__main__':
    main()
