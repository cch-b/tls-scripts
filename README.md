# TLS Tree Processing Scripts

A collection of scripts to make processing TLS tree data easier.

- [TLS Tree Processing Scripts](#tls-tree-processing-scripts)
- [Setup](#setup)
- [Task scripts](#task-scripts)
- [Script Running Order](#script-running-order)

It is assumed that the appropriate conda (pdal and orchid) environments have been created and all data is located in the correct directories.

See the [documentation](documentation.md) for a detailed description.

## Setup

Perform the following steps:
1. Create a directory to hold the scripts, if needed, for example `mkdir -p ~/dev`
2. Clone the repository, for example `git clone https://github.com/petervines/ucltrees.git`
3. Change to the scripts directory, for example `cd ucltrees/scripts`
4. Make the .sh files executable, for example `chmod u+x *.sh`. and `chmod u+x utils/*.sh`
5. Edit ucltrees_config.txt in ucltrees/config to set the project names and the location of the project directories. 
   Each line contains the name of the project and the location of the project directory separated by a comma.
6. Edit setup.sh to set the location of the scratch directory. The default location is scratch_root="/work/scratch-pw3/$USER". If the scratch root directory 
   does not exist, it will be created when the make_scratch_dirs.sh script is run.
7. Edit setup.sh to change or add any directories that should be created in the project scratch directory. 
8. Run update_bashrc.sh, for example `./setup.sh`. If you wish to create the scratch directories enter y when prompted. Note this is none destructive and will not overwrite any existing directories.
9. Source the .bashrc file, for example `source ~/.bashrc`

As a result of the above, the following will be done:
- A ucltrees_env file will be created in the ucltrees/config directory. This file will define aliases and 
  environmental variables that will be used by the scripts.
- The users .bashrc file will be updated to source the ucltrees_env file 
- The script directory will be prepended to the users PATH. This means that all the ucltrees scripts 
  can be called from any directory.
- An environmental variable will be set that points to the root of the scratch directory for the user. Enter `echo 
  $SCRATCH_ROOT` to see the value of this variable.
- An environmental variable will be set that points to the location of the scripts directory. Enter `echo $SCRIPTS_ROOT` to see the value of this variable.
- Aliases will be created for each project that will allow the user to change to a project directory by entering 
  `cd_<project_name>`. 
- An alias will be created for each project that will allow the user to change to the project scratch directory by 
  entering `cd_<project_name>_scratch`.
- An alias will be created for each project that will allow the user to change to the project log directory by 
  entering `cd_<project_name>_log`.
- An alias will be created to change to the scripts directory by entering `cd_scripts`.
- An alias will be created to change to the scratch root directory by entering `cd_scratch`.
- Enter `alias` to see the list of aliases that have been created.

## Task scripts

Task scripts are designed to allow each step in the processing pipeline to be performed in one step from the command 
line. The scripts are located in the ucltrees/scripts directory.
The scripts are designed to be run as follows:

`do_<task_name>.sh --proj <project_name> --mode [fg]/bg`

For example, `do_instance_seg.sh --proj fg5c1 --mode fg` will run the instance segmentation task for the fg5c1 project in the foreground.

To run scripts in the background, use the --mode bg option. For example, `do_instance_seg.sh --proj fg5c1 --mode bg` will run the instance segmentation task for the fg5c1 project in the background.

Where:
- <task_name> is the describes the task that the script will perform. 
- --proj <project_name> is the name of the project that the script will run on.
- --mode [fg]/bg is the mode that the script will run in. fg means that the script will run in the foreground. bg 
  means that the script will run in the background. The default mode is fg. The mode can be omitted if the script is 
  to run in the foreground.

## Script Running Order

See above to see how to call a script.

The scripts should be run in the following order:

| Order | Script                       | Description                                                        |
|:------|:-----------------------------|:-------------------------------------------------------------------|
| 1     | do_rxp2ply.sh                | Generate ply files                                                 | 
| 2     | do_downsample.sh             | Downsample the ply files                                           | 
| 3     | do_tile_index.sh             | Create a tile index file (tile_index.dat)                          |
| 4     | do_semantic_seg.sh           | Perform semantic segmentation                                      |
| 5     | do_instance_seg.sh           | Perform instance segmentation                                      |
| 6     | do_generate_inputs.sh        | Generate input files for all tileID_treeID.leafon.pl               |
| 7     | do_treeqsm.sh                | Run TreeQSM                                                        |
| 8     | do_optqsm_commands.sh        | Generate command files                                             |
| 9     | do_optqsm.sh                 | Submit jobs to run optqsm for individual trees                     |
| 10    | do_generate_results.sh       | Generates tree-attributes csv file                                 |
| 11    | do_generate_tls_tree_figs.sh | Generate TLS tree figures                                          | 
| 12    | do_copy_files.sh             | Copies files from the scratch directories to the project directory |
