#!/bin/bash
#SBATCH --job-name=pnet
#SBATCH --partition=epyc-64           # or whatever partition: epyc-64, shared, etc.
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=40        
#SBATCH --mem=150G                
#SBATCH --time=16:00:00
#SBATCH --output=logs/pn_picks_%j.out
#SBATCH --error=logs/pn_picks_%j.err
#SBATCH --account=okaya_201

# ---------------- ENV SETUP ---------------- #
# Debug info
export PATH=$PATH:/project2/okaya_201/LOC-FLOW/bin

echo "Running on host: $(hostname)"
echo "SLURM_CPUS_PER_TASK = ${SLURM_CPUS_PER_TASK}"
echo "Temp dir: $TMPDIR"

# ---------------- RUN JOBS ---------------- #
cd /project2/okaya_201/LOC-FLOW/Pick/PhaseNet  # adjust to your script path

echo "Starting PhaseNet at $(date)"
python runphasenet.py

echo "Done at $(date)"
