"""
dt_history.py

Wrapper function around the snapshot checks dt_history.py script. This also copies the
plot to my computer for convenience.

This does this on all directories in the current working directory that start with
`runtime`. It does ask the user if they want to do this.
"""
import sys, os
import subprocess
from pathlib import Path

current_dir = Path(".").resolve()


def get_yn_input(prompt):
    answer = input(prompt + " (y/n) ")
    while answer.lower() not in ["y", "n"]:
        answer = input("Enter y or n: ")

    return answer == "y"


def run_command(command):
    subprocess.call(command, shell=True)


for d in sorted(current_dir.iterdir()):
    if d.name.startswith("runtime"):
        # ask the user if they want to do this
        if not get_yn_input(f"Run dt_history on this directory: {str(d)}"):
            continue
        log_dir = d / "log"

        # I can't get aliases to work, so we have to use the full name of the
        # directory here.
        command = f"python3 $WORK/ART_snapshot_checks/dt_history.py {str(log_dir)}"
        run_command(command)

        # then copy this to my macbook. I need to get a clean name to use as the
        # filename on the macbook and for the name of the file transfer. Note that if
        # the folder on the destination doesn't exist (and it won't), it will be
        # automatically created. I need this because all plots are named
        # timestep_history.png, and I don't want to overwrite.
        run_short_name = d.name.replace("runtime_production_", "")
        # then make the arguments for the transfer script.
        command = f"python3 $HOME/code/new_run/globus_transfer.py "
        command += f"{str(log_dir)}/timestep_history.png "  # file to transfer
        command += "macbook "  # destination
        command += f"Desktop/{run_short_name} "  # location on destination
        command += f"dt_history_{run_short_name}"  # transfer name.
        run_command(command)
        print()
