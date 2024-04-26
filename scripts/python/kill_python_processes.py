import os
import psutil

current_user = os.getlogin()

print(f'Current user: {current_user}')
for proc in psutil.process_iter(['pid', 'cmdline', 'username']):
    # check whether the process command line contains 'python' and the process is owned by the current user
    if any('python' in cmd for cmd in proc.info['cmdline']) and proc.info['username'] == current_user:
        print(f'Killing process {proc.info["pid"]} owned by {proc.info["username"]}')
        p = psutil.Process(proc.info['pid'])
        p.kill()
