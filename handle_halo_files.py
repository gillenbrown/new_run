"""
handle_halos.py

Moves halo files from the runtime scratch directory to the analysis scratch directory,
but copies that last set of halo files back to the runtime directory to allow the next
run of halo finding to work properly.

Must be run from the halos directory, and only works for the production runs.
"""

from pathlib import Path
import shutil
from collections import defaultdict

current_dir = Path(".").resolve()

if "production" != current_dir.name:
    raise RuntimeError("Only works for production runs")
if current_dir.parts[1] != "scratch":
    raise RuntimeError("Not on scratch")
scratch = current_dir.parents[2]
analysis_dir = scratch / "art_runs" / "analysis" / "production"

# ======================================================================================
#
# convenience functions
#
# ======================================================================================
def get_scale_factor(filename):
    """
    rtype: str
    """
    if filename.startswith("halos_"):
        return filename[7:13]
    elif filename.startswith("out_"):
        return filename[5:11]
    else:
        return None


# ======================================================================================
#
# Then actually do this
#
# ======================================================================================
for run_dir in current_dir.iterdir():
    run_name = run_dir.name
    halos_dir = run_dir / "run" / "halos"
    analysis_halos_dir = analysis_dir / run_name / "run" / "halos"

    # Find all files
    groups = defaultdict(list)
    last_scale = 0
    for file in halos_dir.iterdir():
        scale = get_scale_factor(file.name)
        if scale is not None:
            groups[scale].append(file)
            # Also keep track of the last output, which will be treated specially
            if float(scale) > float(last_scale):
                last_scale = scale

    # Move files to the analysis directory
    for scale, files in groups.items():
        for f in files:
            new_file_loc = analysis_halos_dir / f.name
            # If it's the last scale factor, just copy it so that we keep the original
            # intact here
            if scale == last_scale:
                shutil.copy2(f, new_file_loc)
            # otherwise, move the files
            else:
                f.rename(new_file_loc)
