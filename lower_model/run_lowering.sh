#!/bin/bash
# This script copies required files and lowers depth values by 5km.

set -e
set -u

# Source directories relative to this script's location
DATA_DIR="../../Data"
REAL_DIR="../../REAL"
REAL_TT_DB_DIR="${REAL_DIR}/tt_db"

echo "--- Starting depth lowering process ---"

# --- 1. Copy files ---
echo "Copying files to current directory..."
cp "${DATA_DIR}/station.dat" .
cp "${REAL_TT_DB_DIR}/mymodel.nd" .
cp "${REAL_DIR}/phase_best_allday.txt" .
cp "${REAL_DIR}/phase_allday.txt" .
# This will fail if no phase_sel files exist, which is intended if they are required.
cp "${REAL_DIR}/"*.phase_sel.txt .

echo "Files copied."

# --- 2. Process files ---
echo "Processing station.dat..."
python3 lower_station_dat.py station.dat lowered_station.dat

echo "Processing mymodel.nd..."
python3 lower_mymodel_nd.py mymodel.nd lowered_mymodel.nd

echo "Processing phase files..."
if [ -f "phase_best_allday.txt" ]; then
    echo "Processing phase_best_allday.txt..."
    python3 lower_phase_files.py phase_best_allday.txt lowered_phase_best_allday.txt
fi

if [ -f "phase_allday.txt" ]; then
    echo "Processing phase_allday.txt..."
    python3 lower_phase_files.py phase_allday.txt lowered_phase_allday.txt
fi

for f in *.phase_sel.txt; do
    # This check handles the case where no *.phase_sel.txt files exist
    # to avoid processing the glob pattern as a filename.
    if [ -e "$f" ]; then
        echo "Processing $f..."
        python3 lower_phase_files.py "$f" "lowered_$f"
    fi
done

echo "--- Depth lowering process finished ---"
echo "New files are prefixed with 'lowered_'."
