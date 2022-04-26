"""
update_run_files.py
Goes through the files for submitting an ART job (defs.h, config.cfh, and submit.sh)
and modifies them given input from the user.

Takes 4 required parameters:
- Directory in which to modify things
- filename of the submission script
- filename of the config file
- Either "slurm" or "torque" to denote the structure of the submit script
"""

import sys
from pathlib import Path
import socket
import shutil
import filecmp
import re
import os

# check arguments provided
if len(sys.argv) != 2:
    raise RuntimeError("Incorrect number of arguments provided to update_run_files.py")

home_dir = Path(sys.argv[1]).resolve()
defs_file = home_dir / "defs.h"
config_file = home_dir / "run" / "config.cfg"
submit_file = home_dir / "run" / "submit.sh"

hostname = socket.gethostname()
if "stampede2" in hostname:
    machine = "stampede2"
else:
    raise RuntimeError("Machine not supported")

# ======================================================================================
#
# functions to make this process happen
#
# ======================================================================================
def print_header(file):
    print("\n" + "=" * 79)
    print("Checking {}\n".format(file.name))


# --------------------------------------------------------------------------------------
# functions to test the format of a proposed value
# --------------------------------------------------------------------------------------
def test_integer(value):
    try:
        int(value)
    except ValueError:
        raise ValueError("This must be an integer")


def test_float(value):
    try:
        float(value)
    except ValueError:
        raise ValueError("This must be a float")


def test_dir(value):
    # This will create the directory if it doesn't exist
    test_path = Path(value)
    if not test_path.is_dir():
        test_path.mkdir()  # creates full path
        print("creating {}".format(value))


def test_epochs(value):
    # \d is the decimal numbers 0-9
    pattern = re.compile("^\(0\.\d*,[01]\.\d*,0\.\d*\)\Z")
    if not pattern.match(value):
        raise ValueError("this does not match the format for epochs")


def test_name(value):
    # here we don't allow any separators
    if os.sep in value:
        raise ValueError("Slashes are not allowed here.")


def test_queue_pleiades(value):
    if value not in ["long", "normal", "devel", "debug"]:
        raise ValueError("This is not an acceptable queue")


def test_queue_stampede2(value):
    if value not in [
        "development",
        "normal",
        "large",
        "long",
        "flat-quadrant",
        "skx-dev",
        "skx-normal",
        "skx-large",
    ]:
        raise ValueError("This is not an acceptable queue")


def test_queue_frontera(value):
    if value not in [
        "development",
        "normal",
        "large",
        "long",
        "small",
    ]:
        raise ValueError("This is not an acceptable queue")


def test_queue_anvil(value):
    if value not in [
        "debug",
        "standard",
        "wide",
        "highmem",
    ]:
        raise ValueError("This is not an acceptable queue")


def test_walltime(value):
    # First we'll check that is has an hours, minutes, seconds fields
    time_segments = value.split(":")
    if len(time_segments) != 3:
        raise ValueError("Not an appropriate walltime format")
    # Then check that each are acceptable
    for segment in time_segments:
        try:
            int(segment)
        except ValueError:
            raise ValueError("Time must be a string")

    # check that seconds and minutes are correct
    for segment in time_segments[1:]:
        if not 0 <= int(segment) < 60:
            raise ValueError("Time is not valid")


# def test_refinement(value):
#     pattern = re.compile("^id=\d{1,2} weight=\d from-level=\d{1,2} to-level=\d{1,2} \d\.\d*\Z")
#     if not pattern.match(value):
#         raise ValueError("this does not match the format for refinement")

test_dict = {
    "int": test_integer,
    "float": test_float,
    "dir": test_dir,
    "epochs": test_epochs,
    "name": test_name,
    "queue_pleiades": test_queue_pleiades,
    "queue_stampede2": test_queue_stampede2,
    "walltime": test_walltime,
    "none": lambda: True,
}


# --------------------------------------------------------------------------------------
# Functions that edit a given line. They will be used in the class below
# --------------------------------------------------------------------------------------
def edit_line(original_line, separator, test_func, answer=None):
    """
    Take a generic line and edit it
    """
    # we need to get the old value
    if separator == " ":
        old_value = original_line.split()[-1]
    else:
        # here we remove the newline with strip, since it doesn't get removed
        # by split. When we replace for this in the line the newline will not
        # be replaced
        old_value = original_line.split(separator)[-1].strip()
    # then get the new value. if answer is provided, we do not need to ask
    if answer is None:
        answer = input("{}: ".format(original_line.strip()))
    # then parse the answer as usual
    if len(answer) == 0:  # don't change anything
        # if we have a directory I want to check that it exists even if we
        # aren't changing anything
        if test_func == test_dir:
            test_func(old_value)
        # then just return the old line, since we have no changes
        return original_line
    else:  # line will be changed
        test_func(answer)
        return original_line.replace(old_value, answer)


def edit_line_refinement_to_level(original_line, separator, test_func, answer=None):
    """
    Must have the same function parameters as the other, even if I don't use them all
    """
    return __edit_line_refinement_level("to", original_line, test_func, answer)


def edit_line_refinement_from_level(original_line, separator, test_func, answer=None):
    return __edit_line_refinement_level("from", original_line, test_func, answer)


def __edit_line_refinement_level(kind, original_line, test_func, answer):
    if kind == "to":
        check_str = "to-level"
    elif kind == "from":
        check_str = "from-level"
    else:
        raise ValueError("Incorrect kind passed to __edit_line_refinement_level")

    # get the original level
    line_chunks = original_line.split()
    for chunk in line_chunks:
        if check_str in chunk:
            break
    else:
        raise ValueError("not a DM lagrangian line! Shouldn't happen")
    old_value = chunk.split("=")[-1]

    # get the desired answer
    if answer is None:
        answer = input(f"DM Lagrangian Refinement to-level={old_value}: ")
        if len(answer) == 0:
            answer = old_value
    test_func(answer)

    # get everything to the right of the equals sign, and replace it with the new value
    assert chunk.count("=") == 1
    new_chunk = chunk[: chunk.index("=")] + "=" + str(answer)

    return original_line.replace(chunk, new_chunk)


def edit_line_submission_stampede2(original_line, separator, test_func, answer=None):
    """
    Edit the line in submit.sh where ART is actually called.

    Must have the same function parameters as the other, even if I don't use them all

    The only changes are the config filename and the restart file, as the
    node/core info is handled by ibrun
    """
    # first see if the user is using remora
    if original_line.split()[0] == "remora":
        remora = 1
    else:
        remora = 0

    # Then we can edit the place to start the sim
    # note that "-root" is used exclusively for initial conditions, while
    # "-r" is used when resuming from another snapshot
    old_restart = original_line.split()[3 + remora]
    answer = input("{} ->  -r=".format(old_restart))
    if len(answer) == 0:
        new_restart = old_restart
    else:
        # the answer is the scale factor of the restart
        try:
            assert 0.0 <= float(answer) <= 1.0
        except (ValueError, AssertionError):
            raise ValueError("Bad restart option.")
        new_restart = f"-r={answer}"

    # if we got here the answer is fine
    return original_line.replace(old_restart, new_restart)


# --------------------------------------------------------------------------------------
# Class that contains info on lines that can be easily modified
# --------------------------------------------------------------------------------------
class CheckLine(object):
    def __init__(self, name, dtype, answer=None, separator=" "):
        self.name = name
        self.separator = separator
        self.check_func = test_dict[dtype]
        if self.name == "dm_lagrangian_to_level":
            self.edit_line_func = edit_line_refinement_to_level
        elif self.name == "jeans_from_level":
            self.edit_line_func = edit_line_refinement_from_level
        elif self.name == "submission_stampede2":
            self.edit_line_func = edit_line_submission_stampede2
        else:
            self.edit_line_func = edit_line

        self.answer = answer
        if self.answer is not None:
            self.answer = str(self.answer)

    def check_line_match(self, line):
        if self.name == "dm_lagrangian_to_level":
            return line.startswith("refinement") and "id=0" in line
        elif self.name == "jeans_from_level":
            return line.startswith("refinement") and "id=8" in line
        elif self.name == "submission_stampede2":
            return line.startswith("ibrun ./art")
        return line.startswith(self.name)


# --------------------------------------------------------------------------------------
# master function to run this editing
# --------------------------------------------------------------------------------------
def update_file(old_file, lines_to_update):
    new_file = Path(str(old_file) + ".temp")

    with open(old_file, "r") as in_file:
        with open(new_file, "w") as out_file:
            for line in in_file:
                match = None
                for start in lines_to_update:
                    if start.check_line_match(line):
                        match = start

                if match is not None:
                    # A few of these have special formats that have to be
                    # checked separately
                    new_line = match.edit_line_func(
                        line, match.separator, match.check_func, match.answer
                    )
                    out_file.write(new_line)
                else:  # not a line of interest, don't change it
                    out_file.write(line)

    # if the files are the same delete the new one, but if they are different
    # replace the old with the new
    files_same = filecmp.cmp(old_file, new_file)
    if not files_same:
        print("\nReplacing {}".format(old_file))
        shutil.copy2(new_file, old_file)
    # remove the new one regardless, since we copied earlier
    os.remove(new_file)


# ======================================================================================
#
# Update defs.h
#
# ======================================================================================
print_header(defs_file)

defs_updates = [CheckLine("#define num_refinement_levels", "int")]
update_file(defs_file, defs_updates)

# Then go through and find the newly calculated level, so we can grab it and use it to
# calculate some other quantities of interest used later
with open(defs_file, "r") as in_file:
    for line in in_file:
        if line.startswith(defs_updates[0].name):
            num_levels = int(line.split()[-1])
            break

# ======================================================================================
#
# Update config.cfg
#
# ======================================================================================
print_header(config_file)

config_updates = [
    # CheckLine("directory:outputs", "dir"),
    # CheckLine("directory:logs", "dir"),
    # CheckLine("snapshot-epochs", "epochs"),
    CheckLine("auni-stop", "float"),
    # change levels based on the
    CheckLine("max-dark-matter-level", "int", answer=num_levels - 4),
    CheckLine("sf:min-level", "int", answer=num_levels - 3),
    CheckLine("dm_lagrangian_to_level", "int", answer=num_levels - 4),
    CheckLine("jeans_from_level", "int", answer=num_levels - 3),
    # timestep parameters
    CheckLine("reduce-timestep-factor:deep-decrement", "float"),
    CheckLine("reduce-timestep-factor:shallow-decrement", "float"),
    CheckLine("tolerance-for-timestep-increase", "float"),
    CheckLine("max-timestep-increment", "float"),
    CheckLine("min-timestep-decrement", "float"),
    CheckLine("max-dt-myr", "float"),
    CheckLine("time-refinement-factor:max", "int"),
]
# We don't want to update the log directory because it should be automatically
# generated in the submit script, as we want fresh log directories for each
# run.
update_file(config_file, config_updates)

# ======================================================================================
#
# Update submit.sh
#
# ======================================================================================
print_header(submit_file)
# We need get the number of ranks per node and therefore cores per rank
# first just go through the file and identify the current values
with open(submit_file, "r") as in_file:
    for line in in_file:
        if line.startswith("#SBATCH --"):
            data = line.split("--")[-1]
            # all these options have an "=" in their specification
            if "=" in data:
                key, old_value = data.split("=")
                old_value = old_value.strip()  # get rid of newline
                if key == "ntasks-per-node":
                    old_ranks_per_node = int(old_value)
                elif key == "partition":
                    old_partition = old_value

# Then get the new partition
answer_partition = input(f"Queue = {old_partition}: ")
if len(answer_partition) == 0:
    answer_partition = old_partition
# check the validity of this answer
try:
    if machine == "stampede2":
        test_queue_stampede2(answer_partition)
    else:
        raise RuntimeError("Machine not supported")
except ValueError:
    raise ValueError("Partition is not valid.")

# then we can ask the user whether they want to change these
answer_ranks_per_node = input(f"MPI ranks per node = {old_ranks_per_node}: ")
if len(answer_ranks_per_node) == 0:
    answer_ranks_per_node = old_ranks_per_node
# check the validity of this answer
try:
    test_integer(answer_ranks_per_node)
    answer_ranks_per_node = int(answer_ranks_per_node)
except ValueError:
    raise ValueError("Ranks per node must be an integer.")


# Then determine whether or not this evenly uses all cores on the node
if machine == "stampede2":
    if "skx" in answer_partition:
        ncpus = 48
    else:
        ncpus = 68  # KNL nodes
elif machine == "frontera":
    ncpus = 56
elif machine == "anvil":
    ncpus = 128
else:
    raise RuntimeError("Machine not recognized")

n_cpus_per_task = ncpus / answer_ranks_per_node
if int(n_cpus_per_task) != n_cpus_per_task:
    raise RuntimeError(
        f"Running {answer_ranks_per_node} MPI ranks per mode results in an "
        "uneven number of cores per rank. Choose again."
    )


# Then if everything worked, we can use these answers
submit_updates = [
    CheckLine(
        "#SBATCH --partition",
        f"queue_{machine}",
        separator="=",
        answer=answer_partition,
    ),
    CheckLine(
        "#SBATCH --ntasks-per-node",
        "int",
        separator="=",
        answer=int(answer_ranks_per_node),
    ),
    CheckLine(
        "#SBATCH --cpus-per-task", "int", separator="=", answer=int(n_cpus_per_task)
    ),
    CheckLine("#SBATCH --time", "walltime", separator="="),
    CheckLine("#SBATCH --nodes", "int", separator="="),
    CheckLine("submission_stampede2", "none"),  # other parameters not used
    # make sure the work directory in the submit script matches this directory
    CheckLine("work_dir", "dir", separator="=", answer=str(home_dir)),
]

update_file(submit_file, submit_updates)
