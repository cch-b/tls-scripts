from datetime import datetime

start = datetime.now()

import sys
import os
import glob
import multiprocessing as mp
import json
import argparse

import pandas as pd
import numpy as np
import geopandas as gp
from shapely.geometry import Point

import ply_io
import pdal


def tile_data(scan_pos, args, tile_locks):
    # Get the scan name to use in log_file messages so that they are not too long:
    scan_name = os.path.basename(scan_pos)
    # Record the start time
    start_time = datetime.now()
    if args.verbose:
        with args.Lock:
            msg = f'[{datetime.now().strftime("%H:%M:%S")}] Worker started for scan: {scan_name}'
            print(msg)
            write_to_log(msg, args.log_file)

    try:
        base, scan = os.path.split(scan_pos)
        try:
            if args.test:
                rxp = sorted(
                    glob.glob(os.path.join(base, scan, 'scans' if 'SCNPOS' in scan else '', '??????_??????.mon.rxp'))
                )[-1]
            else:
                rxp = sorted(
                    glob.glob(os.path.join(base, scan, 'scans' if 'SCNPOS' in scan else '', '??????_??????.rxp'))
                )[-1]
        except:
            if args.verbose:
                with args.Lock:
                    msg = f"!!! Can't find {os.path.join(base, scan, '??????_??????.rxp')} !!!"
                    print(msg)
                    write_to_log(msg, args.log_file)
            return

        sp = int(scan.replace(args.prefix, '').replace('.SCNPOS', ''))

        if args.verbose:
            with args.Lock:
                rxp_name = os.path.basename(rxp)
                msg = f'rxp -> xyz for scan pos {scan_name}: {rxp_name}'
                print(msg)
                write_to_log(msg, args.log_file)

        fn_matrix = glob.glob(os.path.join(args.matrix_dir, f'{scan.replace(".SCNPOS", "")}.*'))
        if len(fn_matrix) == 0:
            if args.verbose:
                with args.Lock:
                    msg = f"!!! Can not find rotation matrix: {os.path.join(args.matrix_dir, scan.replace('.SCNPOS', '') + '.*')} !!!"
                    print(msg)
                    write_to_log(msg, args.log_file)
            return
        matrix = np.dot(args.global_matrix, np.loadtxt(fn_matrix[0]))
        st_matrix = ' '.join(matrix.flatten().astype(str))

        cmds = []

        # pdal commands as dictionaries
        read_in = {'type': 'readers.rxp', 'filename': rxp, 'sync_to_pps': 'false', 'reflectance_as_intensity': 'false'}
        cmds.append(read_in)

        dev_filter = {'type': 'filters.range', 'limits': 'Deviation[0:{}]'.format(args.deviation)}
        cmds.append(dev_filter)

        refl_filter = {'type': 'filters.range', 'limits': 'Reflectance[{}:{}]'.format(*args.reflectance)}
        cmds.append(refl_filter)

        transform = {'type': 'filters.transformation', 'matrix': st_matrix}
        cmds.append(transform)

        tile = {'type': 'filters.splitter', 'length': f'{args.tile}', 'origin_x': '0', 'origin_y': '0'}
        cmds.append(tile)

        # link commmands and pass to pdal
        JSON = json.dumps(cmds)
        pipeline = pdal.Pipeline(JSON)


        pipeline.execute()

        # iterate over tiled arrays
        for arr in pipeline.arrays:
            arr = pd.DataFrame(arr)
            arr = arr.rename(columns={'X': 'x', 'Y': 'y', 'Z': 'z'})
            # arr.columns = ['x', 'y', 'z', 'InternalTime', 'ReturnNumber', 'NumberOfReturns',
            #               'amp', 'refl', 'EchoRange', 'dev', 'BackgroundRadiation',
            #               'IsPpsLocked', 'EdgeOfFlightLine']
            arr.loc[:, 'sp'] = sp
            arr = arr[
                ['x', 'y', 'z', 'Reflectance', 'Deviation', 'ReturnNumber', 'NumberOfReturns', 'sp']
            ]  # save only relevant fields

            # remove points outside bbox
            arr = arr.loc[(arr.x.between(args.bbox[0], args.bbox[2])) & (arr.y.between(args.bbox[1], args.bbox[3]))]
            if len(arr) == 0:
                continue

            # identify tile number
            X, Y = (arr[['x', 'y']].min() // args.tile * args.tile).astype(int)
            tile = args.tiles.loc[(args.tiles.x == X) & (args.tiles.y == Y)]
            if len(tile) == 0:
                continue
            tile_n = str(tile.tile.item()).zfill(args.n)
            tile_number = tile.tile.item()

            # save to xyz file
            with tile_locks[tile_number]:
                if args.store_tmp_with_sp:
                    with open(os.path.join(args.odir, f'{args.plot_code}{tile_n}.{sp}.xyz'), 'ab') as fh:
                        fh.write(arr.to_records(index=False).tobytes())
                else:
                    with open(os.path.join(args.odir, f'{args.plot_code}{tile_n}.xyz'), 'ab') as fh:
                        fh.write(arr.to_records(index=False).tobytes())

        # Record the end time
        end_time = datetime.now()
        # Calculate the execution time

        if args.verbose:
            with args.Lock:
                msg1 = f'[{datetime.now().strftime("%H:%M:%S")}] Worker finished for scan: {scan_name}'
                msg2 = f'Runtime: {calculate_execution_time(start_time, end_time)}'
                print(msg1)
                print(msg2)
                write_to_log(msg1, args.log_file)
                write_to_log(msg2, args.log_file)

    except Exception as e:
        with args.Lock:
            msg1 = f'!!!! {scan_pos} !!!!'
            msg2 = f'{e}'
            print(msg1)
            print(msg2)
            write_to_log(msg1, args.log_file)
            write_to_log(msg2, args.log_file)


def xyz2ply_w_sp(xyz, args):
    start_time = datetime.now()

    xyz = str(xyz).zfill(args.n)

    if args.verbose:
        with args.Lock:
            msg = f'Worker process started for sp.xyz -> ply: {xyz}'
            print(msg)
            write_to_log(msg, args.log_file)

    tmp = pd.DataFrame()

    for fn in glob.glob(os.path.join(args.odir, f'{xyz}.*.xyz')):
        open_file = open(fn, encoding='ISO-8859-1')
        tmp = pd.concat(
            [
                tmp,
                pd.DataFrame(np.fromfile(open_file, dtype='float64,float64,float64,float32,float32,uint8,uint8,int64')),
            ]
        )
        os.unlink(fn)

    if len(tmp) > 0:
        tmp.columns = ['x', 'y', 'z', 'refl', 'dev', 'ReturnNumber', 'NumberOfReturns', 'sp']
        ply_io.write_ply(os.path.join(args.odir, f'{xyz}.ply'), tmp)

    end_time = datetime.now()
    if args.verbose:
        with args.Lock:
            msg1 = f'Worker process ended for xyz -> ply: {xyz}'
            msg2 = f'Runtime: {calculate_execution_time(start_time, end_time)}'
            print(msg1)
            print(msg2)
            write_to_log(msg1, args.log_file)
            write_to_log(msg2, args.log_file)


def xyz2ply(xyz_path, args):
    start_time = datetime.now()

    if args.verbose:
        with args.Lock:
            msg = f'Worker process started for xyz -> ply: {xyz_path}'
            print(msg)
            write_to_log(msg, args.log_file)

    open_file = open(xyz_path, encoding='ISO-8859-1')
    tmp = pd.DataFrame(np.fromfile(open_file, dtype='float64,float64,float64,float32,float32,uint8,uint8,int64'))
    tmp.columns = ['x', 'y', 'z', 'refl', 'dev', 'ReturnNumber', 'NumberOfReturns', 'sp']
    ply_io.write_ply(xyz_path.replace('.xyz', '.ply'), tmp)
    os.unlink(xyz_path)

    end_time = datetime.now()
    if args.verbose:
        with args.Lock:
            msg1 = f'Worker process ended for xyz -> ply: {xyz_path}'
            msg2 = f'Runtime: {calculate_execution_time(start_time, end_time)}'
            print(msg1)
            print(msg2)
            write_to_log(msg1, args.log_file)
            write_to_log(msg2, args.log_file)


def calculate_execution_time(start_time, end_time):
    # Calculate the execution time
    execution_time = end_time - start_time

    # Convert the execution time to HH:MM:SS format
    total_seconds = int(execution_time.total_seconds())
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    execution_time_str = f'{hours:02}:{minutes:02}:{seconds:02}'

    return execution_time_str


def write_to_log(message, log_file):
    if log_file:
        with open(log_file, 'a') as f:
            f.write(message + '\n')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', '-p', required=True, type=str, help='path to point cloud')
    parser.add_argument('--matrix-dir', '-m', type=str, default='', help='path to rotation matrices')
    parser.add_argument('--plot-code', type=str, default='', help='plot suffix')
    parser.add_argument('--odir', type=str, default='.', help='output directory')
    parser.add_argument('--deviation', type=float, default=15, help='deviation filter')
    parser.add_argument('--reflectance', type=float, nargs=2, default=[-999, 999], help='reflectance filter')
    parser.add_argument('--tile', type=float, default=10, help='length of tile')
    parser.add_argument('--num-prcs', type=int, default=10, help='number of cores to use')
    parser.add_argument('--prefix', type=str, default='ScanPos', help='file name prefix, deafult:ScanPos')
    parser.add_argument('--buffer', type=float, default=10.0, help='size of buffer')
    parser.add_argument('--bbox', type=int, nargs=4, default=[], help='bounding box format xmin ymin xmax ymax')
    parser.add_argument('--bbox-only', action='store_true', help='generate bounding box only, do not process tiles')
    parser.add_argument('--bounding-geometry', type=str, default=False, help='a bounding geometry')
    parser.add_argument('--convex-hull', action='store_true', help='fits a convex hull geometry around scan positions')
    parser.add_argument(
        '--rotate-bbox', action='store_true', help='rotate bounding geometry to best fit scan positions'
    )
    parser.add_argument(
        '--save-bounding-geometry', type=str, default=False, help='file where to save bounding geometry'
    )
    parser.add_argument('--global-matrix', type=str, default=False, help='path to global rotation matrix')
    parser.add_argument('--pos', default=[], nargs='*', help='process using specific scan positions')
    parser.add_argument('--test', action='store_true', help='test using the .mon.rxp')
    parser.add_argument(
        '--store-tmp-with-sp', action='store_true', help='spits out individual tmp files for tiles _and_ scan position'
    )
    parser.add_argument('--log-file', type=str, default='', help='log file')
    parser.add_argument('--verbose', action='store_true', help='print something')

    args = parser.parse_args()
    args.project = os.path.abspath(args.project)

    # global rotation matrix
    if args.global_matrix:
        args.global_matrix = np.loadtxt(args.global_matrix)
    else:
        args.global_matrix = np.identity(4)

    # find scans
    args.ScanPos = sorted(glob.glob(os.path.join(args.project, f'{args.prefix}*')))
    if len(args.ScanPos) == 0:
        raise Exception('no scan positions found')
    if args.plot_code != '':
        args.plot_code += '_'

    # find and read rotation matrix
    if not os.path.isdir(args.matrix_dir):
        raise Exception(f'no such directory: {args.matrix_dir}')
    M = glob.glob(os.path.join(args.matrix_dir, f'{args.prefix}*.*'))
    if len(M) == 0:
        raise Exception('no matrix files found, ensure they are named correctly')
    matrix_arr = np.zeros((len(M), 3))
    for i, m in enumerate(M):
        matrix_arr[i, :] = np.loadtxt(m)[:3, 3]

    # bbox [xmin, ymin, xmax, ymax]
    if args.bounding_geometry and len(args.bbox) > 0:
        raise Exception('a bounding geometry and bounding box have been specified')
    if args.bbox:
        geometry = Polygon(
            (
                (args.bbox[0], args.bbox[1]),
                (args.bbox[0], args.bbox[3]),
                (args.bbox[2], args.bbox[3]),
                (args.bbox[2], args.bbox[1]),
                (args.bbox[0], args.bbox[1]),
            )
        )
        extent = gp.GeoDataFrame([0], geometry=[geometry], columns=['id'])
    elif args.bounding_geometry:
        extent = gp.read_file(args.bounding_geometry)  # .buffer(args.buffer, join_style='mitre')
    elif args.rotate_bbox:
        extent = gp.GeoDataFrame(data=np.arange(len(matrix_arr)), geometry=[Point(r[0], r[1]) for r in matrix_arr])
        extent = gp.GeoDataFrame(
            [0],
            columns=['id'],
            geometry=[extent.unary_union.minimum_rotated_rectangle.buffer(args.tile + args.buffer, join_style='mitre')],
        )
    elif args.convex_hull:
        extent = gp.GeoDataFrame(data=np.arange(len(matrix_arr)), geometry=[Point(r[0], r[1]) for r in matrix_arr])
        extent = gp.GeoDataFrame(
            [0], columns=['id'], geometry=[extent.unary_union.convex_hull.buffer(args.tile + args.buffer)]
        )
    else:
        extent = gp.GeoDataFrame(data=np.arange(len(matrix_arr)), geometry=[Point(r[0], r[1]) for r in matrix_arr])
        extent = gp.GeoDataFrame(
            [0],
            columns=['id'],
            geometry=[extent.unary_union.envelope.buffer(args.tile + args.buffer, join_style='mitre')],
        )
    args.bbox = (extent.exterior.bounds.values[0] // args.tile) * args.tile
    if args.verbose:
        print('bounding box:', args.bbox)
    if args.save_bounding_geometry:
        extent.to_file(args.save_bounding_geometry)
        if args.verbose:
            msg = f'bounding geometry saved to {args.save_bounding_geometry}'
            print(msg)
            write_to_log(msg, args.log_file)

    # create tile db
    X, Y = np.meshgrid(
        np.arange(args.bbox[0], args.bbox[2], args.tile), np.arange(args.bbox[1], args.bbox[3], args.tile)
    )
    XY = np.vstack([X.flatten(), Y.flatten()]).T.astype(int)
    args.tiles = gp.GeoDataFrame(data=XY, columns=['x', 'y'], geometry=[Point(r[0], r[1]) for r in XY])
    args.tiles = gp.sjoin(args.tiles, extent, how='inner')

    args.tiles.loc[:, 'tile'] = range(len(args.tiles))
    args.tiles = args.tiles[['x', 'y', 'tile', 'geometry']]
    args.n = len(str(len(args.tiles)))
    if args.n < 3:
        args.n = 3
    args.tile_count = len(args.tiles)

    if len(args.pos) > 0:
        args.pos = [os.path.abspath(p[:-1]) if p.endswith(os.pathsep) else os.path.abspath(p) for p in args.pos]
        if args.verbose:
            msg = f'processing only: {args.pos}'
            print(msg)
            write_to_log(msg, args.log_file)

        args.ScanPos = list(args.pos) if len(args.pos) == 1 else args.pos
        # args.ScanPos = [os.path.join(args.project, p) for p in args.pos]

    # write tile index
    args.tiles[['tile', 'x', 'y']].to_csv(os.path.join(args.odir, 'tile_index.dat'), sep=' ', index=False, header=False)
    if args.bbox_only:
        sys.exit()

    # read in and tile scans
    mp.set_start_method('spawn')
    m = mp.Manager()
    # Create an array of locks, one per tile, number of tiles is args.n
    tile_locks = [m.Lock() for _ in range(args.tile_count + 1)]

    args.Lock = m.Lock()
    # [tile_data(sp, args) for sp in np.sort(args.ScanPos)]

    with mp.Pool(processes=args.num_prcs, maxtasksperchild=1) as pool:
        tile_args = [(sp, args, tile_locks) for sp in np.sort(args.ScanPos)]

        async_results = pool.starmap_async(tile_data, tile_args, error_callback=lambda e: print(e))
        async_results.wait()

        if args.verbose:
            with args.Lock:
                msg = 'Finished processing all scan positions'
                print(msg)
                write_to_log(msg, args.log_file)

        # write to ply - reusing Pool
        if args.store_tmp_with_sp:
            pool.starmap_async(xyz2ply_w_sp, [(xyz, args) for xyz in np.sort(args.tiles.tile)])
        else:
            xyz = glob.glob(os.path.join(args.odir, '*.xyz'))
            pool.starmap_async(xyz2ply, [(xyz, args) for xyz in np.sort(xyz)])

        pool.close()
        pool.join()

    end = datetime.now()
    msg = f'Total rxp2ply runtime: {calculate_execution_time(start, end)}'
    print(msg)


if __name__ == '__main__':
    main()