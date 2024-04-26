#!/bin/bash 
#SBATCH --partition=short-serial
#SBATCH --time=12:00:00
#SBATCH --job-name=TreeQSM
#SBATCH --mem=1024
#SBATCH --array=0-124
#SBATCH -o /work/scratch-pw3/ucfacc2/sbatch_logs/treeqsm/%x_%j_%A_%a.out
#SBATCH -e /work/scratch-pw3/ucfacc2/sbatch_logs/treeqsm/%x_%j_%A_%a.err
#SBATCH -o /dev/null
#SBATCH -e /dev/null

# executable 
source ~/.bashrc
conda activate octave

# submit_job-run_qsm-array.py passes one arguments via sbatch:
# 1. T: subdirectory in the intermediate/results directory

echo octave --no-gui ${T}/*_${SLURM_ARRAY_TASK_ID}.m
octave --no-gui < ${T}/*_${SLURM_ARRAY_TASK_ID}.m
