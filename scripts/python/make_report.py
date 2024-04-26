#!/usr/bin/env python
"""Generates status reports in markdown, notebooks and uploads to Google sheets"""

import argparse
import json
import os
import time
import csv
import datetime as datetime

import gspread
import gspread_formatting as gsf
import nbformat as nbf

GSPREAD_SILENCE_WARNINGS = 1


def init():
    global DEFAULT_STATUS_FILE
    global DEFAULT_LOG_FILE
    global DEFAULT_MD_FILE
    global DEFAUlT_LOG_MD_FILE
    global NOTEBOOK_DIR

    DEFAULT_STATUS_FILE = f"{os.environ['LOG_ROOT']}/status.json"
    DEFAULT_LOG_FILE = f"{os.environ['LOG_ROOT']}/commands.log"
    DEFAULT_MD_FILE = f"{os.environ['LOG_ROOT']}/status.md"
    DEFAUlT_LOG_MD_FILE = f"{os.environ['LOG_ROOT']}/commands-log.md"

    home_dir = os.path.expanduser('~')
    # Define the notebook directory
    NOTEBOOK_DIR = f"{os.environ['LOG_ROOT']}"

    # Check if the notebook directory exists
    if not os.path.exists(NOTEBOOK_DIR):
        # If it doesn't exist, create it
        os.makedirs(NOTEBOOK_DIR)


def upload(status_file, log_file) -> None:
    credentials_file, key = get_credentials_and_key()

    # If the credentials file is None, return
    if credentials_file is None:
        return

    gc = gspread.service_account(filename=credentials_file)
    sh = gc.open_by_key(key)

    status, projects = get_projects(status_file)

    upload_projects(gc, key, status, projects)

    log_data = read_log_file(log_file)
    upload_log_data(gc, key, log_data)

    print(f'The report URL is: {sh.url}')


def upload_projects(gc, key, status, projects):
    ws_name = 'Status Test' if args.debug else 'Status'
    worksheet, _ = get_worksheet(gc, key, ws_name)

    format_worksheet(worksheet)

    offset = 3
    for i, project in enumerate(projects):
        row = i + offset
        perform_operation_with_retry(lambda: worksheet.update_acell(f'A{row}', project))
        perform_operation_with_retry(
            lambda: worksheet.format(f'A{row}', {'textFormat': {'bold': True}}),
        )

        # Create a list to store rows for each step in the project
        rows = []
        for step in status[project]:
            # Add the step's values to the rows list
            rows.append(
                [
                    step['name'],
                    step['status'],
                    step['date_started'],
                    step['date_finished'],
                    step['duration'],
                ],
            )

        # Apply all rows at once
        perform_operation_with_retry(lambda: worksheet.append_rows(rows))

        # Create a list to store the formats
        formats = []

        # For each row
        for j in range(len(rows) + 1):
            # Add the format for the row to the list
            formats.append(
                {
                    'range': f'A{row + j + 1}:E{row + j + 1}',
                    'format': {'textFormat': {'bold': False}},
                },
            )

        perform_operation_with_retry(lambda: worksheet.batch_format(formats))

        n_steps = len(status[project])
        offset += n_steps + 1


def upload_log_data(gc, key, log_data):
    ws_name = 'Command Log Test' if args.debug else 'Command Log'
    worksheet, new_sheet = get_worksheet(gc, key, ws_name)

    # Format the worksheet
    if new_sheet:
        format_log_worksheet(worksheet)

    data_to_upload = []
    if new_sheet:
        for data in log_data:
            data_to_upload.append(
                [
                    data['datetime'],
                    data['message'],
                    data['project'],
                    data['step'],
                    data['status'],
                    data['date_started'],
                    data['date_finished'],
                    data['command'],
                ]
            )
    else:
        data = log_data[-1] if log_data else {}
        print(f'Last data: {data}')
        data_to_upload.append(
            [
                data['datetime'],
                data['message'],
                data['project'],
                data['step'],
                data['status'],
                data['date_started'],
                data['date_finished'],
                data['command'],
            ]
        )

    # Upload the data in one go
    perform_operation_with_retry(lambda: worksheet.append_rows(data_to_upload))


def get_worksheet(gc, key, ws_name):
    try:
        worksheet = gc.open_by_key(key).worksheet(ws_name)
        new_worksheet = False
    except gspread.exceptions.WorksheetNotFound:
        gc.open_by_key(key).add_worksheet(title=ws_name, rows=300, cols=20)
        worksheet = gc.open_by_key(key).worksheet(ws_name)
        new_worksheet = True
    return worksheet, new_worksheet


def format_worksheet(worksheet):
    worksheet.clear()
    gsf.set_frozen(worksheet, rows=1, cols=1)

    worksheet.update([['Step', 'Status', 'Date Started', 'Date Finished', 'Duration']])
    worksheet.format(
        'A1:E1',
        {
            'textFormat': {'bold': True},
            'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9},
        },
    )

    gsf.set_column_width(worksheet, 'A', 300)
    gsf.set_column_width(worksheet, 'B', 50)
    gsf.set_column_width(worksheet, 'C', 150)
    gsf.set_column_width(worksheet, 'D', 150)
    gsf.set_column_width(worksheet, 'E', 75)


def format_log_worksheet(worksheet):
    worksheet.clear()
    gsf.set_frozen(worksheet, rows=1, cols=1)

    worksheet.update([['Date', 'Source', 'Project', 'Step', 'Status', 'Date Started', 'Date Finished', 'Command']])
    worksheet.format(
        'A1:H1',
        {
            'textFormat': {'bold': True},
            'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9},
        },
    )

    gsf.set_column_width(worksheet, 'A', 150)  # Date
    gsf.set_column_width(worksheet, 'B', 75)  # Note
    gsf.set_column_width(worksheet, 'C', 75)  # Project
    gsf.set_column_width(worksheet, 'D', 200)  # Step
    gsf.set_column_width(worksheet, 'E', 75)  # Status
    gsf.set_column_width(worksheet, 'F', 150)  # Date Started
    gsf.set_column_width(worksheet, 'G', 150)  # Date Finished
    gsf.set_column_width(worksheet, 'H', 500)  # Command


def get_projects(status_file):
    with open(status_file) as f:
        status = json.load(f)

    projects = list(status.keys())
    projects.sort()

    return status, projects


def read_log_file(log_file):
    with open(log_file) as f:
        reader = csv.DictReader(f, delimiter='|')
        log_data = [row for row in reader]

    return log_data


def get_credentials_and_key():
    credentials_file = os.path.join(
        os.path.expanduser('~'),
        'dev/ucltrees/credentials',
        'googlecredentials.json',
    )

    key_file = os.path.join(
        os.path.expanduser('~'),
        'dev/ucltrees/credentials',
        'sheet.key',
    )

    # If the credentials file does not exist, return None
    if not os.path.exists(credentials_file):
        return None, None

    with open(key_file) as f:
        key = f.read().strip()

    return credentials_file, key


def perform_operation_with_retry(action):
    delay = 1
    for i in range(1, 6):
        try:
            action()
            break
        except gspread.exceptions.APIError as e:
            if e.response.status_code == 429:
                print(f'Hit rate limit. Retrying after {delay} seconds...')
                time.sleep(delay)
                delay *= 2
            else:
                raise e


def create_markdown_report(status_file):
    # Open the status.json file and load the data
    with open(status_file) as f:
        status = json.load(f)

    print(status)

    # Set the location of the report.md in $LOG_ROOT
    os.chdir(os.environ.get('LOG_ROOT', ''))
    # Open a new markdown file in write mode
    with open('status.md', 'w') as f:
        f.write('# UCL TLS Trees Status\n\n')
        f.write('| Step | Status | Date Started | Date Finished | Duration |\n')
        f.write('|------|--------|--------------|---------------|----------|\n')

        # Iterate over the projects in the status.json data
        for project in status:
            # Write the project name in bold to the markdown file
            f.write(f'|**{project}**| \n')
            # Write the headers of the report to the markdown file

            # Iterate over the steps
            for step in status[project]:
                # Write the step's details to the markdown file
                f.write(
                    f"| {step['name']} | {step['status']} | {step['date_started']} | {step['date_finished']} | {step['duration']} |\n"
                )


def create_log_markdown(log_file):
    log_data = read_log_file(log_file)

    md = '| Date| Source | Project | Step |Status | Date Started | Date Finished | Command |\n'
    md += '|-----|--------|---------|------|-------|--------------|---------------|---------|\n'

    for data in log_data:
        md += f"| {data['datetime']} | {data['message']} | {data['project']} | {data['step']} | {data['status']} | {data['date_started']} | {data['date_finished']} | {data['command']} |\n"

    write_markdown(md, DEFAUlT_LOG_MD_FILE)


def create_notebook_report(status_file):
    # Open the status.json file and load the data
    with open(status_file) as f:
        status = json.load(f)

    # Create a new notebook
    nb = nbf.v4.new_notebook()

    # Add a title cell at the top
    nb['cells'].append(nbf.v4.new_markdown_cell('# UCL TLS Trees Status'))

    # Add a code cell with the HTML style
    nb['cells'].append(
        nbf.v4.new_code_cell('%%html\n<style>\ntable {float:left}\n</style>'),
    )

    # Iterate over the projects in the status.json data
    for project in status:
        # Create a markdown string for the project
        project_md = f'## {project}\n'
        project_md += '| Step | Status | Date Started | Date Finished | Duration |\n'
        project_md += '|------|--------|--------------|---------------|----------|\n'

        # Iterate over the steps
        for step in status[project]:
            # Add the step's details to the project markdown string
            project_md += f"| {step['name']} | {step['status']} | {step['date_started']} | {step['date_finished']} | {step['duration']} |\n"

        # Add a markdown cell with the project markdown string
        nb['cells'].append(nbf.v4.new_markdown_cell(project_md))

    write_notebook(nb, 'TLS_status.ipynb')


def create_command_log_notebook(log_file):
    # Create a new notebook
    nb = nbf.v4.new_notebook()

    md = '# UCL TLS Trees Command Log\n'
    md += ' Use `display_log()` to show entries in date order.\n\n'
    md += 'If you make changes stop and rerun the cell.\n'
    nb['cells'].append(nbf.v4.new_markdown_cell(md))

    code = 'from notebook_utils import display_log \n'
    code += '%load_ext autoreload \n'
    code += '%autoreload 2'
    nb['cells'].append(nbf.v4.new_code_cell(code))
    nb['cells'].append(nbf.v4.new_code_cell('display_log(reverse=True)'))
    write_notebook(nb, 'TLS_command_log.ipynb', overwrite=False)


def write_notebook(notebook, file_name, overwrite=True):
    # Define the path to the notebook file
    notebook_file = os.path.join(NOTEBOOK_DIR, file_name)

    # If the notebook file exists and overwrite is False, return
    if os.path.exists(notebook_file) and not overwrite:
        return

    # Write the notebook to the file
    with open(notebook_file, 'w') as f:
        nbf.write(notebook, f)


def write_markdown(md, md_file_path):
    # Write the notebook to the file
    with open(md_file_path, 'w') as f:
        f.write(md)

    return md_file


def create_notebook_from_md(md_file_path):
    # Read the markdown file
    with open(md_file_path) as f:
        md_content = f.read()

    # Create a new notebook
    nb = nbf.v4.new_notebook()

    # Add a markdown cell with the content of the markdown file
    nb['cells'].append(nbf.v4.new_markdown_cell(md_content))

    # Define the path to the notebook file
    notebook_file = os.path.splitext(md_file_path)[0] + '.ipynb'

    # Write the notebook to the file
    with open(notebook_file, 'w') as f:
        nbf.write(nb, f)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--log-dir',
        '-l',
        type=str,
        default=os.environ.get('LOG_ROOT', ''),
        help=' path to log file directory',
    )
    parser.add_argument('--verbose', action='store_true', help='print detailed information')
    parser.add_argument('--upload', action='store_true', help='upload to google sheets')
    parser.add_argument('--debug', action='store_true', help='print debug information')
    args = parser.parse_args()

    # Initialize the script
    init()

    # args.debug = True  # Uncomment for testing

    status = DEFAULT_STATUS_FILE
    log_file = DEFAULT_LOG_FILE
    md_file = DEFAULT_MD_FILE
    motebook_dir = NOTEBOOK_DIR

    create_markdown_report(status)
    create_log_markdown(log_file)
    create_notebook_report(status)
    create_notebook_from_md(md_file)
    create_command_log_notebook(log_file)

    if args.upload:
        upload(status, log_file)
