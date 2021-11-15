"""
handle_out_files.py

Move out files from the working_out directory to the out directory, but keeping the
last output in working_out

Must be run from the folder containing all the runs, and only works for the
production runs.
"""

from pathlib import Path
import shutil
from collections import defaultdict

current_dir = Path(".").resolve()

if "production" != current_dir.name:
    raise RuntimeError("Only works for production runs")
if current_dir.parts[1] != "scratch":
    raise RuntimeError("Not on scratch")


# ======================================================================================
#
# convenience functions
#
# ======================================================================================
def get_scale_factor(filename):
    """
    rtype: str
    """
    if filename.startswith("continuous_a"):
        return filename[12:18]
    else:
        return None


# ======================================================================================
#
# Then actually do this
#
# ======================================================================================
for run_dir in sorted(current_dir.iterdir()):
    out_dir = run_dir / "run" / "out"
    working_out_dir = run_dir / "run" / "working_out"

    # check that the out directory is empty
    if len([f for f in out_dir.iterdir()]) > 0:
        raise RuntimeError(f"Out directory for {run_dir.name} is not empty")

    # Find all output files
    groups = defaultdict(list)
    last_scale = 0
    for file in working_out_dir.iterdir():
        scale = get_scale_factor(file.name)
        if scale is not None:
            groups[scale].append(file)
            # Also keep track of the last output, which will be treated specially
            if float(scale) > float(last_scale):
                last_scale = scale

    print(f"Last output for {run_dir.name} at a = {last_scale}")

    # Move files to the analysis directory. But if there's only one, that means that
    # the simulation didn't progress at all. So we don't need to move anything.
    if len(groups) == 1:
        continue
    for scale, files in groups.items():
        for f in files:
            new_file_loc = out_dir / f.name
            # If it's the last scale factor, just copy it so that we keep the original
            # intact here
            if scale == last_scale:
                shutil.copy2(f, new_file_loc)
            # otherwise, move the files
            else:
                f.rename(new_file_loc)
