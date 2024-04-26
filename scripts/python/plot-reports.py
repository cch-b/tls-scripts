import os
import glob
import argparse
import numpy as np
import pandas as pd
import geopandas as gp
from shapely.geometry import Polygon, Point
from scipy.spatial import ConvexHull

import ply_io
import mat2qsm

from pandarallel import pandarallel
pandarallel.initialize(nb_workers=10, progress_bar=True)

import warnings
from shapely.errors import ShapelyDeprecationWarning
warnings.filterwarnings("ignore", category=ShapelyDeprecationWarning) 

def process_tree(row, params):
    
    t = os.path.split(row.cloud)[1].split('.')[0]#[:-11] 
    
    # point cloud
    pc = ply_io.read_ply(row.cloud)
    pc.loc[:, 'nz'] = pc.z - pc.z.min()
    pc_height = np.ptp(pc.z)
   
    hull = ConvexHull(pc.sample(min(int(1e5), len(pc)))[['x', 'y']])
    
    if 'wood' in pc.columns:
        pc = pc.loc[pc.wood == 1]
    elif 'label' in pc.columns:
        pc = pc.loc[pc.label == 3]
    else: pass
    X = pc.x.loc[pc.nz.between(1.3, 1.4)].mean()
    Y = pc.y.loc[pc.nz.between(1.3, 1.4)].mean()
    
    M = {'tree':t, 'x_m':X, 'y_m':Y, 'pc_height':pc_height, 'hull_volume':hull.volume}
    M['geometry_crown'] = Polygon(hull.points[hull.vertices])
    M['geometry_stem'] = Point([X, Y])
    
    qsmf = glob.glob(os.path.join(params.models, f'{t}.mat'))
    
    if len(qsmf) > 0:
        qsm = mat2qsm.QSM(qsmf[0])
        for k in qsm.treedata_fields:
            #if k not in df.columns:
            #    df.loc[:, k] = np.nan
            M[k] = qsm.__dict__[k].astype(float)
            if k in ['TotalVolume', 'TrunkVolume', 'BranchLength', 'BranchVolume']:
                if  f'{k}_opt' not in df.columns:
                    #df.loc[:, f'{k}_opt'] = np.nan
                    #df.loc[:, f'{k}_std'] = np.nan
                    opt, std = qsm.__dict__[f'opt_{k}'].astype(float)
                    M[f'{k}_opt'] = opt
                    M[f'{k}_std'] = std
        try:
            cyl = qsm.cyl2pd()
            DBHidx = cyl.loc[(cyl.sz > cyl.sz.min() + 1.3) & (cyl.branch == 1)].iloc[0].name
            M['DBHsec'] = cyl.loc[DBHidx].radius * 2
        except:
            pass
    
    M = pd.Series(M)
    return(M)

    
if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    # parser.add_argument('--clouds', '-c', type=str, nargs='*', required=True, help='point cloud directory')
    parser.add_argument('--clouds', '-c', type=str, required=True, help='point cloud directory')
    parser.add_argument('--models', '-m', type=str, default='../models/label/', help='path to tile index')
    parser.add_argument('--matrix', '-x', type=str, default='raw/matrix', help='path to tile index')
    parser.add_argument('--global-matrix', type=str, default=None, help='path to global rotation matrix')
    parser.add_argument('--outfile', '-o', default=False, type=str, help='location of output .csv file')
    parser.add_argument('--no-dbh-class', action='store_true', help='whether trees are in dbh class subdirectories')
    params = parser.parse_args()

    # clouds = params.clouds
    clouds = glob.glob(os.path.join(params.clouds, '' if params.no_dbh_class else '?.?',  '*on.ply'))
 
    # sanity checks
    if len(clouds) == 0:
        raise Exception(f'no .ply files in {params.clouds}')
    if len(glob.glob(os.path.join(params.models, '*.mat'))) == 0:
        raise Exception(f'no .mat files in {params.models}')
    matrix = glob.glob(os.path.join(params.matrix, '*.dat')) + glob.glob(os.path.join(params.matrix, '*.DAT'))
    if len(matrix) == 0:
        raise Exception(f'no .dat files in {params.matrix}')
        
    print(f'processing {len(clouds)} trees')
    
    trees = np.unique([os.path.splitext(c)[0].split('.')[0] for c in clouds])
    df = pd.DataFrame(data=clouds, columns=['cloud'])
#     df = df.loc[:10]
    df = df.parallel_apply(process_tree, args=[params], axis=1, )
    print(df[['tree', 'TotalVolume', 'TotalVolume_opt', 'TotalVolume_std']])
    
    # tile number
    try:
        df.loc[:, 'tile'] = [int(tree.split('_')[0]) for tree in df.tree]
    except:
        print('could not scrape tile number - prob older project')
    
    # import scan positions
    sp = pd.DataFrame(columns=['x', 'y', 'z'])

    for i, dat in enumerate(matrix):
        sp.loc[i, :] = np.loadtxt(dat)[:3, 3]

    if params.global_matrix:
        M = np.loadtxt(params.global_matrix)
        sp.loc[:, 'a'] = 1
        sp[['x', 'y', 'z', 'a']] = np.dot(M, sp[['x', 'y', 'z', 'a']].T).T

    geometry = [Point(r.x, r.y) for r in sp.itertuples()]
    sp = gp.GeoDataFrame(sp, geometry=geometry)

    area = sp.unary_union.minimum_rotated_rectangle.area
    print(f'plot area: {area / 1e4:.2f} ha')
    
    geometry = [Point(r.x_m, r.y_m) for r in df.itertuples()]
    df = gp.GeoDataFrame(df, geometry=geometry)
    df.loc[:, 'in_plot'] = df.within(sp.unary_union.minimum_rotated_rectangle)
    
    # estimate plot AGB and C
    wood_density = .5
    agb2C = .471
    PLOT = ((df.loc[df.in_plot].TotalVolume.sum() / 1000) * wood_density) 
    print('total volume:', df.loc[df.in_plot].TotalVolume.sum() / 1000)
    print('plot AGB:', PLOT, 'plot C:', PLOT * agb2C)
    print('AGB ha-1:', PLOT / (area / 1e4), 'C ha-1:', (PLOT * agb2C) / (area / 1e4)) 
   
    cols = ['tree','x_m','y_m','tile','in_plot', 
            'BranchLength','BranchLength_opt','BranchLength_std','BranchVolume','BranchVolume_opt',
            'BranchVolume_std','DBHcyl','DBHqsm','DBHsec','LengthBranchOrder','LengthCylDiam','MaxBranchOrder',
            'NumberBranchOrder','NumberBranches','StemTaper','TotalArea','TotalVolume','TotalVolume_opt',
            'TotalVolume_std','TreeHeight','TrunkLength','TrunkVolume','TrunkVolume_opt','TrunkVolume_std',
            'VolumeBranchOrder','VolumeCylDiam','distance','geometry_crown','geometry_stem','hull_volume',
            'location','pc_height']
    cols = [c for c in cols if c in df.columns]


    if params.outfile:
        df[cols].to_csv(params.outfile, index=False)     
