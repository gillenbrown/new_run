"""
tar_log.py - move a log directory from scratch to the correct directory on Ranch

This only takes one parameter: the name of the directory to copy.

The script must be run from SCRATCH, and the log directory must be here. This works
for production runs only.
"""
import sys
from pathlib import Path
import subprocess

# get the directory the user suggested
log_dir = Path(sys.argv[1]).resolve()

# validate that we're on scratch
if not str(log_dir.parent) == "/scratch/06912/tg862118":
    print(log_dir.parent)
    raise ValueError("Not on scratch")
# validate that this is a production run
if not log_dir.name.startswith("runtime_production_"):
    raise ValueError("Not a log directory from the production runs!")
# validate that this directory is here
if not log_dir.is_dir():
    raise ValueError("This directory does not exist!")

# Now we can figure out where to put this directory on Ranch. We don't need the full
# intro of the Ranch directory since the other script handles that.
path_ranch = "art_runs/runs/production/"
# use the name of the run to put this in the right directory
name_split = log_dir.name.split("_")
if "fboost" in log_dir.name:
    dir_name = "_".join(name_split[2:6])
else:
    dir_name = "_".join(name_split[2:5])
path_ranch += dir_name
# then go to the log directory
path_ranch += "/run/log/"
# I don't need the filename since the copy script automatically does that

# Then we can execute this!
# I can't get aliases to work, so we have to use the full name of the directory here.
command = f"python3 $HOME/code/new_run/tar_directory.py "
# Since we're in the same parent directory as the copy directory we can just pass
# its name. We also pass the other parameters to delete the original directory,
# do not include the date, and to show where it should be on ranch
command += f"{log_dir.name} {path_ranch} no-date delete"
subprocess.call(command, shell=True)
