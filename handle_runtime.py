"""
handle_runtime.py

Moves the stdout and log files into their proper runtime directory.

Must be run from the directory where the files are.
"""

from pathlib import Path

current_dir = Path(".").resolve()

# find all the runtime directories
runtime_dirs = [d for d in current_dir.iterdir() if d.name.startswith("runtime")]

# ==============================================================================
#
# Convenience functions
#
# ==============================================================================
def get_job_name_from_submit_file(submit_file):
    with open(submit_file, "r") as submit:
        for line in submit:
            if line.startswith("#SBATCH --job-name"):
                return line.strip().split("=")[-1]
    # if we got here we didn't find the name, so this isn't a submit script
    raise ValueError("This doesn't look like a submission script.")


def get_job_name_from_runtime_dir(runtime_dir):
    base = runtime_dir.name.replace("runtime_", "")
    # then strip the numbers at the end
    return "_".join(base.split("_")[:-1])


def get_yn_input(prompt):
    answer = input(prompt + " (y/n) ")
    while answer.lower() not in ["y", "n"]:
        answer = input("Enter y or n: ")

    return answer == "y"


# ==============================================================================
#
# Go through and do the work
#
# ==============================================================================
for r_d in runtime_dirs:
    if not get_yn_input(f"Handle {r_d.name}?"):
        continue

    # get the name of the stdout file
    stdout_old_loc = current_dir / r_d.name.replace("runtime_", "stdout_")
    stdout_new_loc = r_d / "log" / "stdout.full.log"
    stdout_old_loc.rename(stdout_new_loc)

    # then find the correct submit file. Double check that there's only one
    n_moves = 0
    job_name = get_job_name_from_runtime_dir(r_d)
    for f in current_dir.iterdir():
        if f.name.startswith("submit_") and f.name.endswith(".sh"):
            this_name = get_job_name_from_submit_file(f)
            if this_name == job_name:
                f.rename(r_d / f.name)
                n_moves += 1
    if n_moves == 0:
        raise ValueError(f"No submit files found for directory: {r_d.name}")
    if n_moves > 1:
        raise ValueError(f"Too many submit files found for directory: {r_d.name}")
