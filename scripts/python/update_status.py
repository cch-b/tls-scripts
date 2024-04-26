import argparse
import json
import os
import os.path
import csv
from dataclasses import asdict, dataclass
from datetime import datetime

# Updates the status of a project in status.json

DEFAULT_STATUS_FILE = f"{os.environ['LOG_ROOT']}/status.json"
RUNNING_STATUS = "running"
COMPLETED_STATUS = "done"
DEFAULT_LOG_FILE = f"{os.environ['LOG_ROOT']}/commands.log"


@dataclass
class Step:
    name: str
    status: str = ""
    date_started: str = ""
    date_finished: str = ""
    duration: str = ""

    def calculate_duration(self):
        if self.date_started and self.date_finished:
            self.duration = calculate_duration(self.date_started, self.date_finished)


def load_status(status_file):
    try:
        with open(status_file) as f:
            return json.load(f)
    except FileNotFoundError:
        write_to_log(f"Status file {status_file} not found.")
    except json.JSONDecodeError:
        write_to_log(f"Error decoding JSON from {status_file}.")
    return {}


def save_status(data, status_file):
    for project in data:
        data[project].sort(key=lambda step: step["name"])
    with open(status_file, "w") as f:
        json.dump(data, f, indent=4)


def calculate_duration(start_date, end_date):
    date_formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S",
        "%m-%d-%Y %H:%M:%S",
        "%m-%d-%YT%H:%M:%S",
    ]
    for fmt in date_formats:
        try:
            date_started = datetime.strptime(start_date, fmt)
            break
        except ValueError:
            pass
    else:
        print(
            f"Error calculating duration: time data '{start_date}' does not match formats {date_formats}"
        )
        return ""

    for fmt in date_formats:
        try:
            date_finished = datetime.strptime(end_date, fmt)
            break
        except ValueError:
            pass
    else:
        print(
            f"Error calculating duration: time data '{end_date}' does not match formats {date_formats}"
        )
        return ""

    return str(date_finished - date_started)


def clear_project_steps(project, status_file=DEFAULT_STATUS_FILE):
    # Load the current status
    data = load_status(status_file)

    # Check if the project exists in the status
    if project in data:
        # Clear the steps for the project
        data[project] = []

        # Save the updated status
        save_status(data, status_file)


def update_status(project, step, status_file=DEFAULT_STATUS_FILE):
    data = load_status(status_file)
    data.setdefault(project, [])

    for existing_step in data[project]:
        if existing_step["name"] == step.name:
            # Only overwrite the start_date if the status is running

            if step.status == RUNNING_STATUS:
                existing_step["date_started"] = step.date_started
            elif step.status == COMPLETED_STATUS:
                step.date_started = existing_step[
                    "date_started"
                ]  # Keep the original start date
                step.calculate_duration()
            existing_step.update(asdict(step))
            break
    else:
        step.calculate_duration()
        data[project].append(asdict(step))

    save_status(data, status_file)


def get_project_status(project, status_file=DEFAULT_STATUS_FILE):
    data = load_status(status_file)
    if project in data:
        project_data = data[project]
        return json.dumps(project_data, indent=4)
    else:
        return json.dumps({"error": "Project not found in the status file."})


def get_date_from_line(line, prefix):
    date_str = line.split(prefix)[1].strip()
    for fmt in (
        "%a %b %d %H:%M:%S %Z %Y",
        "%Y-%m-%d %H:%M:%S",
        "%a %d %b %H:%M:%S %Z %Y",
    ):
        try:
            return datetime.strptime(date_str, fmt)
        except ValueError:
            pass
    raise ValueError(f"No valid date format found for date string: {date_str}")


def update_status_from_logs(project, log_dir):
    if project:
        # If a project name is given, only iterate over the log files in that project's directory
        projects = [project]
    else:
        # If no project name is given, iterate over all project directories
        projects = [
            dir
            for dir in os.listdir(log_dir)
            if os.path.isdir(os.path.join(log_dir, dir))
        ]

    for project in projects:
        clear_project_steps(project)
        project_dir = os.path.join(log_dir, project)
        # Check if there are any log files in the project directory
        log_files = [file for file in os.listdir(project_dir) if file.endswith(".log")]
        if not log_files:
            # If there are no log files, skip to the next project directory
            continue
        # Iterate over all log files in the project directory
        for log_file in log_files:
            if log_file.endswith(".log"):
                # Check if the log file name contains 'DONE'
                step_status = COMPLETED_STATUS if "DONE" in log_file else RUNNING_STATUS
                if "DONE" not in log_file:
                    step_name = log_file.replace("_", " ").replace(".log", "")
                else:
                    step_name = (
                        log_file.replace("_DONE_", " ")
                        .replace(".log", "")
                        .replace("_", " ")
                    )

                date_started = None
                date_finished = None
                # Open the log file and read its contents
                with open(os.path.join(project_dir, log_file)) as f:
                    for line in f:
                        # Look for the line that starts with 'Date Run:'
                        if line.startswith("Date Run:"):
                            date_started = get_date_from_line(line, "Date Run:")
                        # Look for the line that starts with 'End time:'
                        elif line.startswith("End time:"):
                            date_finished = get_date_from_line(line, "End time:")
                if date_finished is None:
                    date_finished = datetime.fromtimestamp(
                        os.path.getmtime(os.path.join(project_dir, log_file))
                    )

                # Format date_started and date_finished in the '%Y-%m-%d %H:%M:%S' format if they are not None
                date_started = (
                    date_started.strftime("%Y-%m-%d %H:%M:%S") if date_started else None
                )
                date_finished = (
                    date_finished.strftime("%Y-%m-%d %H:%M:%S")
                    if date_finished
                    else None
                )

            step = Step(
                name=step_name,
                status=step_status,
                date_started=date_started,
                date_finished=date_finished,
            )
            # Only update the step there is a project and a step name.
            if project and step.name:
                update_status(project, step, args.status_file)


def write_to_log(msg='Update: ', data={}, log_file=DEFAULT_LOG_FILE):
    fieldnames = ['datetime', 'message', 'project', 'step', 'status', 'date_started', 'date_finished', 'command']

    # Extract the required data
    row_data = {
        'datetime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'message': msg,
        'project': data.get('project_name'),
        'step': data.get('step_name'),
        'status': data.get('step_status'),
        'date_started': data.get('step_date_started'),
        'date_finished': data.get('step_date_finished'),
        'command': ' '.join(data.get('command', []))
    }

    # Check if the log file exists
    file_exists = os.path.isfile(log_file)
    print(log_file)

    with open(log_file, 'a') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter='|')

        # If the file didn't exist before, write the header
        if not file_exists:
            writer.writeheader()

        # Write the data
        writer.writerow(row_data)
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--project-name", "-p", default="", type=str, help="name of the project"
    )
    parser.add_argument("--step-name", type=str, help="name of the step")
    parser.add_argument(
        "--step-status", type=str, help="status of the step, running or done"
    )
    parser.add_argument("--step-date-started", type=str, help="date the step started")
    parser.add_argument("--step-date-finished", type=str, help="date the step finished")
    parser.add_argument(
        "--status-file",
        default=DEFAULT_STATUS_FILE,
        type=str,
        help="path to the status file",
    )
    parser.add_argument(
        "--update-from-logs", action="store_true", help="update status from log files"
    )
    parser.add_argument("--command", nargs='+', default='', help='command that was run')
    args = parser.parse_args()
    
    # Set the dates if the arguments are not given
    # Set date_started to the current date time if the status is running and date_started is None
    if args.step_date_started is None and args.step_status == RUNNING_STATUS:
        # Set the date_finished to the current date time
        args.step_date_started = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Set date_finished to the current date time if the status is done and date_finished is None
    if args.step_date_finished is None and args.step_status == COMPLETED_STATUS:
        # Set the date_finished to the current date time
        args.step_date_finished = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if args.step_date_finished is None:
        args.step_date_finished = ''

    # Write the args to a status.log file in LOG_ROOT with a timestamp
    write_to_log(msg="Update", data=vars(args))

    if args.update_from_logs:
        update_status_from_logs(
            args.project_name, f"{os.environ['LOG_ROOT']}/{args.project_name}"
        )
    else:
        step = Step(
            name=args.step_name,
            status=args.step_status,
            date_started=args.step_date_started,
            date_finished=args.step_date_finished,
        )
        update_status(args.project_name, step, args.status_file)
