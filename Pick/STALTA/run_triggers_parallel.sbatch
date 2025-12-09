#!/bin/bash
#SBATCH --job-name=ps_picks
#SBATCH --partition=epyc-64           # or whatever partition: epyc-64, shared, etc.
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=40         # matches your 40-core node
#SBATCH --mem=150G                 # plenty for 25k SACs + parallelism
#SBATCH --time=08:00:00
#SBATCH --output=logs/ps_picks_%j.out
#SBATCH --error=logs/ps_picks_%j.err
#SBATCH --account=okaya_201

# ---------------- ENV SETUP ---------------- #
# Load modules / activate environment as you normally do
# (adjust to match how you start 'phasenet' env on this cluster)

#module purge
# Example – replace with your actual env loading:
#module load anaconda/2023.09 2>/dev/null || true

# If you use conda:
#source ~/miniconda3/etc/profile.d/conda.sh   # adjust path
# conda activate phasenet                     # whatever env has ObsPy etc.

# Debug info
echo "Running on host: $(hostname)"
echo "SLURM_CPUS_PER_TASK = ${SLURM_CPUS_PER_TASK}"
echo "Temp dir: $TMPDIR"

# ---------------- RUN JOBS ---------------- #
cd /project2/okaya_201/LOC-FLOW/Pick/STALTA  # adjust to your script path

echo "Starting P picker at $(date)"
python trigger_p_amp_parallel.py

# echo "Starting S picker at $(date)"
# python trigger_s_amp_parallel.py

echo "Done at $(date)"
