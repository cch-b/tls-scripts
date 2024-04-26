#!/bin/bash
#SBATCH --partition=short-serial
#SBATCH -o /work/scratch-pw3/ucfacc2/sbatch_logs/optqsm/%x_%j_%A_%a.out
#SBATCH -e /work/scratch-pw3/ucfacc2/sbatch_logs/optqsm/%x_%j_%A_%a.err
#SBATCH --time=5:00:00
#SBATCH --job-name=optqsm
#SBATCH --mem=1024
#SBATCH -n 1

# executable
conda activate octave
echo octave --no-gui < $f
octave --no-gui < $f
