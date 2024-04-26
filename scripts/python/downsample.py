#!/usr/bin/env python
from datetime import datetime
import os
import glob
import multiprocessing
import argparse
import json
import pdal

start = datetime.now()

def downsample(ply, args):
    
    start_time = datetime.now()
    if args.verbose:
        with args.Lock:
            msg = f'[{datetime.now().strftime("%H:%M:%S")}] Worker started to downsample: {ply}'
            print(msg)
            write_to_log(msg, args.log_file)

    reader = {"type":"readers.ply",
              "filename":ply}
    
    downsample = {"type":"filters.voxelcenternearestneighbor",
                  "cell":f"{args.length}"}
    
    writer = {'type':'writers.ply',
              'storage_mode':'little endian',
              'filename':os.path.join(args.odir, os.path.split(ply)[1].replace('.ply', '.downsample.ply'))}
            
    cmd = json.dumps([reader, downsample, writer])
    pipeline = pdal.Pipeline(cmd)
    pipeline.execute()
    
    end_time = datetime.now()
    execution_time = calculate_execution_time(start_time, end_time)
    if args.verbose:
        msg1 = f'Worker ended for downsample: {ply}'
        msg2 = f'Runtime: {execution_time}'
        print(msg1)
        print(msg2)
        write_to_log(msg, args.log_file)
        write_to_log(msg, args.log_file)

def calculate_execution_time(start_time, end_time):
    # Calculate the execution time
    execution_time = end_time - start_time

    # Convert the execution time to HH:MM:SS format
    total_seconds = int(execution_time.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    execution_time_str = f"{hours:02}:{minutes:02}:{seconds:02}"

    return execution_time_str

def write_to_log(message, log_file):
    if log_file:
        with open(log_file, 'a') as f:
            f.write(message + '\n')

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('-i','--idir', type=str, help='directory where downsampled tiles are stored')
    parser.add_argument('-o','--odir', default='.', help='directory where downsampled tiles are stored')
    parser.add_argument('-l', '--length', type=float, default=.02, help='voxel edge length')
    parser.add_argument('--num-prcs', type=int, default=10, help='number of cores to use')
    parser.add_argument('--log-file', type=str, default='', help='log file')
    parser.add_argument('--verbose', action='store_true', help='print something')
    args = parser.parse_args()
    
    m = multiprocessing.Manager()
    args.Lock = m.Lock()
    pool = multiprocessing.Pool(args.num_prcs)
    pool.starmap_async(downsample, [(ply, args) for ply in glob.glob(os.path.join(args.idir, '*.ply'))])
    pool.close()
    pool.join() 

    end = datetime.now()
    msg = f'Total downsample runtime: {calculate_execution_time(start, end)}'
    print(msg)
