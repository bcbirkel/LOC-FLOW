#!/bin/bash
# This script copies required files and lowers depth values by a specified amount.

set -e
set -u

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <depth_change_km>"
    exit 1
fi

DEPTH_CHANGE_KM=$1

# Output directories relative to this script's location
OUTPUT_DIR="../model_files"
ORIGINAL_DIR="${OUTPUT_DIR}/original"

# Source directories relative to this script's location
DATA_DIR="../../Data"
REAL_DIR="../../REAL/runs/PhaseNet"
REAL_TT_DB_DIR="../../REAL/tt_db"
LOC_FLOW_DIR="../../LOC-FLOW/location/VELEST/PhaseNet"

echo "--- Starting depth lowering process ---"

# --- 0. Create output directories ---
echo "Creating output directories..."
mkdir -p "${OUTPUT_DIR}"
mkdir -p "${ORIGINAL_DIR}"

# --- 1. Copy files ---
echo "Copying files to ${ORIGINAL_DIR}..."
cp "${DATA_DIR}/station_full_filt.dat" "${ORIGINAL_DIR}/"
cp "${REAL_TT_DB_DIR}/mymodel_welev.nd" "${ORIGINAL_DIR}/"
cp "${LOC_FLOW_DIR}/final.CNV" "${ORIGINAL_DIR}/" 2>/dev/null || true
# The following cp commands will not error if source files don't exist
cp "${REAL_DIR}/phase_best_allday.txt" "${ORIGINAL_DIR}/" 2>/dev/null || true
cp "${REAL_DIR}/phase_allday.txt" "${ORIGINAL_DIR}/" 2>/dev/null || true
cp "${REAL_DIR}/"*.phase_sel.txt "${ORIGINAL_DIR}/" 2>/dev/null || true

echo "Files copied."

# --- 2. Process files ---
echo "Processing station.dat..."
python3 lower_station_dat.py "${ORIGINAL_DIR}/station_full_filt.dat" "${OUTPUT_DIR}/lowered_station_full.dat" "$DEPTH_CHANGE_KM"

echo "Processing mymodel_welev.nd..."
python3 lower_mymodel_nd.py "${ORIGINAL_DIR}/mymodel_welev.nd" "${OUTPUT_DIR}/lowered_mymodel.nd" "$DEPTH_CHANGE_KM"

echo "Processing phase files..."
if [ -f "${ORIGINAL_DIR}/phase_best_allday.txt" ]; then
    echo "Processing phase_best_allday.txt..."
    python3 lower_phase_files.py "${ORIGINAL_DIR}/phase_best_allday.txt" "${OUTPUT_DIR}/lowered_phase_best_allday.txt" "$DEPTH_CHANGE_KM"
fi

if [ -f "${ORIGINAL_DIR}/phase_allday.txt" ]; then
    echo "Processing phase_allday.txt..."
    python3 lower_phase_files.py "${ORIGINAL_DIR}/phase_allday.txt" "${OUTPUT_DIR}/lowered_phase_allday.txt" "$DEPTH_CHANGE_KM"
fi

for f in "${ORIGINAL_DIR}/"*.phase_sel.txt; do
    # This check handles the case where no *.phase_sel.txt files exist
    # to avoid processing the glob pattern as a filename.
    if [ -e "$f" ]; then
        fname=$(basename "$f")
        echo "Processing $fname..."
        python3 lower_phase_files.py "$f" "${OUTPUT_DIR}/lowered_$fname" "$DEPTH_CHANGE_KM"
    fi
done

if [ -f "${ORIGINAL_DIR}/final.CNV" ]; then
    echo "Processing final.CNV..."
    python3 lower_final_cnv.py "${ORIGINAL_DIR}/final.CNV" "${OUTPUT_DIR}/lowered_final.CNV" "$DEPTH_CHANGE_KM"
fi

echo "--- Depth lowering process finished ---"
echo "Original files are in ${ORIGINAL_DIR}."
echo "New files are in ${OUTPUT_DIR} and prefixed with 'lowered_'."
