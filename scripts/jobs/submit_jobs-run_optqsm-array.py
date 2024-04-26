import os
import subprocess
import argparse
from glob import glob

parser = argparse.ArgumentParser()
parser.add_argument('-i', '--input', type=str, required=True,
                    help='path to models/optqsm/commands/ directory')
parser.add_argument('-o', '--output', type=str, required=True,
                    help='path to models/optqsm/results/ directory')
parser.add_argument('-j', '--job', type=str,
                    default='/gws/nopw/j04/nceo_generic/nceo_ucl/TLS/wx_test/jobs/qsm/job_scripts/run_optqsm_array.sh',
                    help='path to job script')
parser.add_argument('-u', '--user', type=str, default='ucfawya', help='username')
parser.add_argument('-p', '--project', type=str, default='', help='project name')
args = parser.parse_args()


def qsub():
    # 	# return len(subprocess.check_output(["qstat"],universal_newlines=True).split('\n'))
    return len(subprocess.check_output(["squeue", "-u", args.user], universal_newlines=True).split('\n'))


flist = glob(os.path.join(args.input, '*.m'))
print(f'Number of files: {len(flist)}')
print(f'{flist=}')

i = 0
while len(flist) > 0:
    i += 1
    if qsub() < 10:  # Jasmin allows submit 9999 files at maximum
        fn = flist[0]
        subdir_name = os.path.basename(fn)
        if args.project:
            jobname = f'{args.project}_optqsm{i}_{subdir_name}'
        else:
            jobname = f'optqsm{i}_{subdir_name}'
        # command to submit the job
        print(f'sbatch --export=f={fn} --job-name {jobname} -D {args.output} < {args.job}')
        os.system(f'sbatch --export=f={fn} --job-name {jobname} -D {args.output} < {args.job}')

        flist.remove(fn)

    else:
        time.sleep(60)
