import os
import time
import subprocess
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('-i', '--input', type=str, required=True, 
                    help='path to models/intermediate/inputs/ directory')
parser.add_argument('-j', '--job', type=str, 
                    default='/gws/nopw/j04/nceo_generic/nceo_ucl/TLS/wx_test/jobs/qsm/job_scripts/run_qsm_array.sh', 
                    help='path to job script')
parser.add_argument('-u', '--user', type=str, default='ucfawya', help='username')
parser.add_argument('-p', '--project', type=str, default='', help='project name')
args = parser.parse_args()

def qsub():
# 	# return len(subprocess.check_output(["qstat"],universal_newlines=True).split('\n'))
    return len(subprocess.check_output(["squeue", "-u", args.user], universal_newlines=True).split('\n'))

# find all subdirs under input_path
subdirs = [x[0] for x in os.walk(args.input)][1:]

i = 0
while len(subdirs) > 0:
    i += 1
    if qsub() < 1000:  # Limit the number of jobs to 1000
        subdir = subdirs[0]
        subdir_name = os.path.basename(subdir)
        
        if args.project:
            jobname = f'{args.project}_treeqsm{i}_{subdir_name}'
        else:
            jobname = f'treeqsm{i}_{subdir_name}'

        # command to submit the job
        print(f'sbatch --export=T={subdir} --job-name {jobname} < {args.job}')
        os.system(f'sbatch --export=T={subdir} --job-name {jobname} < {args.job}')
        
        subdirs.remove(subdir)
    else:
        time.sleep(60)
