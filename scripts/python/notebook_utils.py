# Utility functions for Jupyter notebooks

import time
import pandas as pd
from IPython.display import display, Markdown, clear_output
import os
from subprocess import Popen, PIPE


def display_markdown(file_path='commands.log', interval=10):
    while True:
        clear_output(wait=True)
        with open(file_path, 'r') as md_file:
            content = md_file.read()
        display(Markdown(content))
        time.sleep(interval)


def display_log(file_path='commands.log', interval=10, reverse=False):
    while True:
        clear_output(wait=True)
        data = pd.read_csv(file_path, sep='|')
        data = data.fillna('')
        if reverse:
            data = data.sort_index(ascending=False)
        display(data)
        time.sleep(interval)


def display_squeue(interval=30, user='ucfacc2'):
    while True:
        cmd = f'squeue -u {user}'
        with Popen(cmd, shell=True, stdout=PIPE) as process:
            output = process.stdout.read().decode()
            lines = output.splitlines()
            data = [line.split() for line in lines]
            df = pd.DataFrame(data)
        clear_output(wait=True)
        display(df)
        time.sleep(interval)


if __name__ == '__main__':
    pass
