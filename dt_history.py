"""
dt_history.py

Wrapper function around the snapshot checks dt_history.py script. This also copies the
plot to my computer for convenience.

Takes one command line argument, which is the path to the log directory holding the
stdout file.
"""
import sys, os
import subprocess

log_dir = sys.argv[1]


def run_command(command):
    subprocess.call(command, shell=True)


# I can't get aliases to work, so we have to use the full name of the directory here.
command = f"python3 $WORK/ART_snapshot_checks/dt_history.py {log_dir}"
run_command(command)

# then copy this to my macbook. I need to get a clean name to use as the filename
# on the macbook and for the name of the file transfer. Note that if the folder on the
# destination doesn't exist (and it won't), it will be automatically created. I need
# this because all plots are named timestep_history.png, and I don't want to overwrite.
prod_dir_name = log_dir.split(os.sep)[0]
run_short_name = prod_dir_name.replace("runtime_production_", "")
# then make the arguments for the transfer script.
command = f"python3 $HOME/code/new_run/globus_transfer.py "
command += f"{log_dir}/timestep_history.png "  # file to transfer
command += "macbook "  # destination
command += f"Desktop/{run_short_name} "  # location on destination
command += f"dt_history_{run_short_name}"  # transfer name.
run_command(command)
