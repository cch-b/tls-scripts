#!/bin/bash
#
# A set of utility functions for the UCLTREES project

# config dir is in the parent of the script dir
config_dir=$CONFIG_DIR
script_dir=$SCRIPT_DIR


# Default location of ucltrees_config.txt is in the config dir
projects_file="$CONFIG_FILE"

parse_arguments() {
  # Parse command line arguments
  # If no arguments are provided, print the help message
  if [ "$#" -eq 0 ]; then
    echo "Usage: $0 --proj <project_name> [--mode <mode>]"
    echo "       --proj, -p: Project name"
    echo "       --mode, -m: Execution mode (default: fg, options: fg, bg)"
    echo "       --help, -h: Print this help message"
    exit 1
  fi

  while (( "$#" )); do
    case "$1" in
      --proj|-p)
        project_name="$2"
        shift 2
        ;;
      --mode|-m)
        mode="$2"
        shift 2
        ;;
      *)
        echo "Error: Invalid argument"
        echo "Usage: $0 --proj <project_name> [--mode <mode>]"
        echo "       --mode, -m: Execution mode (default: fg, options: fg, bg)"
        echo "       -h, --help: Print this help message"
        exit 1
    esac
  done
}

check_project_name() {
  # Check if the project name is provided
  if [ -z "$project_name" ]; then
    echo "Error: Project name is not provided"
    echo "Usage: $0 --proj <project_name>"
    exit 1
  fi
}

check_projects_file() {
  # Check if the projects file exists
  if [ ! -f "$projects_file" ]; then
    echo "Error: Projects file $projects_file does not exist."
    exit 1
  fi
}

change_directory() {
  # Change to the project directory
  # Extract the project path from the ucltrees_config.txt file
  project_path=$(awk -F',' -v project="$project_name" '$1 == project {print $2}' $projects_file)

  # Check if the project path is empty
  if [ -z "$project_path" ]; then
      echo "Error: Project $project_name not found in $projects_file."
      exit 1
  fi

  # Print the project path for debugging
#  echo "Changing to directory: $project_path"
#  ls -ld "$project_path"

  # Change to the project directory
  cd $project_path || {
      echo "Error: Failed to change to directory $project_path."
      exit 1
  }
  cd $project_path || {
    echo "Error: Failed to change to directory $project_path."
    exit 1
  }
}



generate_command() {
  # generate the command that will be passed to bash
  command="$script_dir/utils/execute_task"
  # Add the mode to the command if it's not empty
  if [ -n "$mode" ]; then
    command="$command --mode $mode"
  fi

  if [ -n "$proj" ]; then
    command="$command --project $proj"
  fi
  if [ -n "$project_path" ]; then
    command="$command --project_path $project_path"
  fi
  # Add the script_path to the command if it's not empty
  if [ -n "$script_path" ]; then
    command="$command --script_path $script_path"
  fi
  # Add the script_name to the command if it's not empty
  if [ -n "$script_name" ]; then
    command="$command --script_name $script_name"
  fi
  # Add the log_name to the command if it's not empty
  if [ -n "$log_name" ]; then
    command="$command --log_name $log_name"
  fi
  # Add the script_args to the command if it's not empty
  if [ -n "$script_args" ]; then
    command="$command --script_args $script_args"
  fi
  echo "Generated command: $command"
}

run_command() {
  # Print the command for debugging
  # echo "Generated command: $command"
  echo ""
  # run the command with bash and show an error if it fails
  source $command || {
    echo "Error: Failed to run the command"
    exit 1
  }
}
