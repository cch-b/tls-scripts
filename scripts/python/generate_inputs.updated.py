import os
import glob
import sys
import numpy as np
import argparse
from tqdm.auto import tqdm

def generate_inputs(flist, output_path, n_models=5, verbose=False):
    # path to save .mat results
    parent_dir = os.path.dirname(output_path)
    print(f'parent_dir: \n{parent_dir}\n')
    results_dir = os.path.join(parent_dir, 'results')
    print(f'results_dir: \n{results_dir}')
    if not os.path.isdir(results_dir): os.mkdir(results_dir)

    for tree in tqdm(flist, total=len(flist)):
        if not os.path.isfile(tree):
            raise Exception(f'{tree} does not exist!')

        name = os.path.basename(tree).split('.')[0]
        ntree = name.split('_')[-1]
        ftype = os.path.basename(tree).split('.')[-1]
        # make a subdir for each tree
        subdir = os.path.join(output_path, name)
        if not os.path.isdir(subdir): os.mkdir(subdir)

        i = 0

        for j in np.linspace(.2, .302, 5): # PatchDiam1
            for k in np.linspace(.05, .152, 5): # PatchDiam2Min
                for l in np.linspace(.15, .252, 5): # PatchDiam2Max
    #                for m in [4, 6, 8]:
                    fn = int(0 if i == 0 else i / n_models) # file number
                    ofn = os.path.join(subdir, f'{name}_{fn}.m') # output file name
                    with open(ofn, 'w') as fh:
                        fh.write("pkg load statistics;\n")
                        fh.write("addpath(genpath('/gws/nopw/j04/nceo_generic/nceo_ucl/TLS/tools/TreeQSM_2.3.0/src/'));\n")
                        fh.write("addpath('/gws/nopw/j04/nceo_generic/nceo_ucl/TLS/tools/optqsm/src/');\n")
                        fh.write('input.PatchDiam1 = {};\n'.format(j))
                        fh.write('input.PatchDiam2Min = {};\n'.format(k))
                        fh.write('input.PatchDiam2Max = {};\n'.format(l))
                        fh.write('input.lcyl = 4;\n')
                        fh.write('input.FilRad = 3.5;\n')
                        fh.write('input.BallRad1 = {} * 1.1;\n'.format(j))
                        fh.write('input.BallRad2 = {} * 1.1;\n'.format(l))
                        fh.write('input.nmin1 = 3;\n')
                        fh.write('input.nmin2 = 1;\n')
                        fh.write('input.OnlyTree = 1;\n')
                        fh.write('input.Tria = 0;\n')
                        fh.write('input.Dist = 1;\n')
                        fh.write('input.MinCylRad = 0.0025;\n')
                        fh.write('input.ParentCor = 1;\n')
                        fh.write('input.TaperCor = 1;\n')
                        fh.write('input.GrowthVolCor = 0;\n')
                        fh.write('input.GrowthVolFrac = 2.5;\n')
                        fh.write("input.tree = 1\n")
                        fh.write('input.model = 1;\n')
                        fh.write('input.savemat = 1;\n')
                        fh.write('input.savetxt = 0;\n')
                        fh.write('input.plot = 0;\n')
                        fh.write('input.disp = 0;\n')
                        fh.write("input.out = '.';\n") 

                        if ftype == 'ply':
                            fh.write("cloud = read_ply('{}');\n".format(os.path.abspath(tree)))
                            fh.write("idx = (cloud(:, 4) == 3);\n")
                            fh.write("cloud = cloud(idx, 1:3);\n")
                        elif ftype == 'txt':
                            fh.write(f"fn = '{os.path.abspath(tree)}';\n")
                            fh.write("data = dlmread(fn, ' ', 0, 0);\n")
                            fh.write("cloud = data(:, 1:3);\n")
                            
                        fh.write("for i = {}:{}\n".format(i, i + (n_models) - 1))
                        fh.write('input.model = i\n')

                        # path to save run_qsm results (.mat files)
                        rdir = os.path.join(results_dir, name)
                        if not os.path.isdir(rdir): os.mkdir(rdir)
                        fh.write("input.name = char(strcat('{}/{}-', num2str(i), '.mat'));\n".format(rdir, name))
                        fh.write("\ttry\n")
                        fh.write('\t\ttreeqsm_mod(cloud, input);\n')
                        fh.write('\tcatch\n')
                        fh.write('\tend\n')
                        fh.write('end\n')
                        fh.write('exit')

                        i += n_models
                    
                    if verbose:
                        print(f'\nGenerated: {ofn}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate input files for QSM.')
    parser.add_argument('-i', '--input_path', type=str, help='Path to point clouds of individual trees.')
    parser.add_argument('-o', '--output_path', type=str, help='Path to save input parameters files for treeqsm_mod().')
    parser.add_argument('-n', '--n_models', type=int, default=5, help='Number of QSM models generated with a same input combination.')
    parser.add_argument('-v', '--verbose', action='store_true', help='Print generated filename.')
    args = parser.parse_args()

    flist = glob.glob(os.path.join(args.input_path, '?.?', '*on.ply'))

    print(f'\ninput path: \n{args.input_path}\n')
    print(f'total number of files: {len(flist)}\n') 
    print(f'output path: \n{args.output_path}\n')
    print(f'number of models per input combination: {args.n_models}\n')


    generate_inputs(flist, args.output_path, 
                    n_models=args.n_models, verbose=args.verbose)
