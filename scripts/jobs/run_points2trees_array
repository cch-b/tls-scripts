#!/bin/bash
#SBATCH --partition=high-mem
#SBATCH --mem=192000
#SBATCH -o /work/scratch-pw3/ucfacc2/sbatch_logs/is/%x_%j_%A_%a.out
#SBATCH -e /work/scratch-pw3/ucfacc2/sbatch_logs/is/%x_%j_%A_%a.err
#SBATCH --time=24:00:00

# Note project_name and project_path passed as an argument to the script by sbatch command
# using --export=ALL,project_name=$project_name,$project_path=$project_path
# $SCRATCH_ROOT is the root directory for the scratch space
# and is part of the user's environment. This is included
# in the .bashrc file in the user's home directory and is included because
# sbatch is called with --export=ALL

# Two parameters are passed to the script by sbatch:
# 1. project_dir: The path to the project directory
# 2. scratch_dir: The path to the project scratch directory

# record the start time
start_time=$(date "+%Y-%m-%d %H:%M:%S")
echo "Script started at: $start_time"

conda activate pytorch-orchid

export N=$(printf %03d $SLURM_ARRAY_TASK_ID)
python /gws/nopw/j04/nceo_generic/nceo_ucl/TLS/tools/TLS2trees/tls2trees/instance.py \
-t "$scratch_dir/fsct/${N}.downsample.segmented.ply" --tindex "$project_dir/tile_index.dat" \
-o "$scratch_dir/clouds/" --n-tiles 7 --slice-thickness .5 --find-stems-boundary 2.5 3. \
--pandarallel --verbose --add-leaves --add-leaves-voxel-length .5 \
--graph-maximum-cumulative-gap 3 --save-diameter-class --ignore-missing-tiles

# record the end time
end_time=$(date "+%Y-%m-%d %H:%M:%S")
echo -e "Script finished at: $end_time"

# total duration time for this job
start_timestamp=$(date -d "$start_time" +%s)
end_timestamp=$(date -d "$end_time" +%s)
duration=$((end_timestamp - start_timestamp))
hours=$((duration / 3600))
minutes=$(( (duration % 3600) / 60 ))
seconds=$((duration % 60))

echo -e "Total duration: $hours:$minutes:$seconds (hh:mm:ss)"
