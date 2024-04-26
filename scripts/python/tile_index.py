import os
import glob
import multiprocessing
import json
import argparse
from datetime import datetime


import pdal

start = datetime.now()

def tile_index(ply, args):
    ply_name = os.path.basename(ply)
    start_time = datetime.now()
    if args.verbose:
        with args.Lock:
            msg = f'[{datetime.now().strftime("%H:%M:%S")}] Worker started processing: {ply_name}'
            print(msg)
            write_to_log(msg, args.log_file)

    reader = {"type":f"readers{os.path.splitext(ply)[1]}",
              "filename":ply}
    stats =  {"type":"filters.stats",
              "dimensions":"X,Y,Z"}
    JSON = json.dumps([reader, stats])
    pipeline = pdal.Pipeline(JSON)
    pipeline.execute()
    JSON = pipeline.metadata
    X = JSON['metadata']['filters.stats']['statistic'][0]['average']
    Y = JSON['metadata']['filters.stats']['statistic'][1]['average']
    Z = JSON['metadata']['filters.stats']['statistic'][2]['minimum']
    T = os.path.split(ply)[1].split('.')[0]
    P = os.path.abspath(ply)
    
    with args.Lock:
        with open(args.tile_index, 'a') as fh:
            fh.write(f'{T} {X} {Y} {Z} {P}\n')
            
    end_time = datetime.now()
    if args.verbose:
        msg1 = f'Worker ended processingg : {ply_name}'
        msg2 = f'Runtime: {calculate_execution_time(start_time, end_time)}'
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

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-i','--pc', type=str, required=True, help='input tiles')
    parser.add_argument('-t','--tile-index', default='tile_index.dat', help='tile index file')
    parser.add_argument('--num-prcs', type=int, default=10, help='number of cores to use')
    parser.add_argument('--log-file', type=str, default='', help='log file')
    parser.add_argument('--verbose', action='store_true', help='print something')
    args = parser.parse_args()

    clouds = glob.glob(os.path.join(args.pc, '*.ply'))

    m = multiprocessing.Manager()
    args.Lock = m.Lock()
    pool = multiprocessing.Pool(args.num_prcs)
    pool.starmap_async(tile_index, [(ply, args) for ply in clouds])
    pool.close()
    pool.join()

    end = datetime.now()
    msg = f'Total tile index runtime: {calculate_execution_time(start, end)}'
    print(msg)
