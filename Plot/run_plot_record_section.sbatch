#!/bin/bash
#SBATCH --job-name=plot_record_sections
#SBATCH --account=okaya_201
#SBATCH --partition=epyc-64
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=30
#SBATCH --mem=70G
#SBATCH --time=12:00:00
#SBATCH --output=plot_record_sections_%j.log

# This script runs plot_record_section.py for a range of dates,
# covering all plot modes and relevant pickers.
# Output from the python script will be organized into subdirectories
# within 'record_sections/' based on the plot mode.

# Define the date range
start_date="2023-04-10"
end_date="2023-05-07"

# Ensure the python script is executable
chmod +x plot_record_section.py

# Convert dates to seconds since epoch for looping
s_date=$(date -d "$start_date" +%s)
e_date=$(date -d "$end_date" +%s)

# Loop through each day
current_date=$s_date
while [ "$current_date" -le "$e_date" ]
do
    date_str=$(date -d "@$current_date" +"%Y-%m-%d")
    echo "Processing date: $date_str"

    # Run for 'all_in_one' mode
    echo "  Running plot_mode: all_in_one"
    python3 plot_record_section.py "$date_str" --plot_mode all_in_one

    # Run for 'individual' mode
    echo "  Running plot_mode: individual"
    python3 plot_record_section.py "$date_str" --plot_mode individual

    # Run for 'picker_stages' for each picker
    for picker in STALTA PhaseNet QMigrate; do
        echo "  Running plot_mode: picker_stages for picker: $picker"
        python3 plot_record_section.py "$date_str" --plot_mode picker_stages --picker "$picker"
    done

    # Move to the next day
    current_date=$((current_date + 86400))
done

echo "All plotting tasks completed."
