#!/bin/bash

# This script can be run in two ways:
# 1. Directly: bash ConvertFiles/run_plotting.sbatch
#    This will generate the job list and submit itself to SLURM.
# 2. By SLURM: sbatch ConvertFiles/run_plotting.sbatch
#    This will execute the job array tasks.

# --- SLURM Configuration ---
#SBATCH --partition=epyc-64
#SBATCH --account=okaya_201
#SBATCH --mem=40G
#SBATCH --job-name=plot_picks
#SBATCH --output=slurm_logs/plot_%A_%a.out
#SBATCH --error=slurm_logs/plot_%A_%a.err
#SBATCH --time=01:00:00

# File containing picker and date for each job
JOB_LIST_FILE="plot_jobs.txt"

# --- Main Logic ---

# Check if we are inside a SLURM job or running standalone
if [ -z "$SLURM_ARRAY_TASK_ID" ]; then
    # --- Standalone Mode: Generate job list and submit ---
    echo "Running in standalone mode. Generating job list and submitting to SLURM."
    
    # Create logs directory if it doesn't exist
    mkdir -p slurm_logs

    # Clear/create the job list file
    > "$JOB_LIST_FILE"

    PICKERS=('STALTA' 'PhaseNet' 'QMigrate')
    for picker in "${PICKERS[@]}"; do
        tbl_file="${picker}.hypoDD.tbl"
        if [ -f "$tbl_file" ]; then
            # Add a line "picker YYYYMMDD" for each unique day in the catalog
            awk -v p="$picker" '{printf "%s %04d%02d%02d\n", p, $2, $4, $5}' "$tbl_file" | sort -u >> "$JOB_LIST_FILE"
        else
            echo "Warning: TBL file not found for '$picker', skipping."
        fi
    done

    # Get the total number of jobs
    num_jobs=$(wc -l < "$JOB_LIST_FILE")

    if [ "$num_jobs" -eq 0 ]; then
        echo "No jobs to process. Exiting."
        exit 0
    fi

    echo "Generated $num_jobs jobs in $JOB_LIST_FILE."
    echo "Submitting job array..."

    # Submit this script to SLURM as a job array (max 10 concurrent jobs)
    sbatch --array=1-$num_jobs%10 "$0" # "$0" refers to this script itself

    echo "Submission complete."

else
    # --- SLURM Task Mode: Execute one job from the list ---
    echo "Running in SLURM task mode."
    
    # Check if job list file exists
    if [ ! -f "$JOB_LIST_FILE" ]; then
        echo "Error: Job list file '$JOB_LIST_FILE' not found."
        exit 1
    fi
    
    # Get parameters for this task from the job list file
    line=$(sed -n "${SLURM_ARRAY_TASK_ID}p" "$JOB_LIST_FILE")
    read -r picker date <<< "$line"

    echo "Task ID: $SLURM_ARRAY_TASK_ID"
    echo "Picker:  $picker"
    echo "Date:    $date"

    # Execute the python script
    python3 plot_record_sections_with_picks.py "$picker" "$date"

    echo "Task $SLURM_ARRAY_TASK_ID finished."
fi
