import sys
import os
import utils
import socket

home_dir = os.path.abspath(sys.argv[1])
defs_file = home_dir + os.sep + "defs.h"
run_dir = home_dir + os.sep + sys.argv[2]
submit_file = sys.argv[3]
config_file = sys.argv[4]
submit_filepath = run_dir + os.sep + submit_file

hostname = socket.gethostname()


def edit_line_submission(original_line):
    """
    Edit the line in submit.sh where ART is actually called.

    The only changes are the config filename and the restart file, as the
    node/core info is handled by ibrun
    """
    # first see if the user is using remora
    if original_line.split()[0] == "remora":
        remora = 1
    else:
        remora = 0
    # Make sure the config file specified is what the user wants
    old_config = original_line.split()[2 + remora]
    new_line = original_line.replace(old_config, config_file)

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
    new_line = new_line.replace(old_restart, new_restart)

    return new_line


def edit_line_copy_config(original_line):
    # account for config files that have paths, as they do on stampede2
    old_config = original_line.split()[1].split("/")[-1]
    return original_line.replace(old_config, config_file)


# ==============================================================================
#
# The actual work is done here!!!
#
# ==============================================================================
submit_updates = [
    utils.CheckLine("#SBATCH --job-name", "name", "="),
    utils.CheckLine("#SBATCH --time", "walltime", "="),
    utils.CheckLine("#SBATCH --nodes", "int", "="),
    utils.CheckLine("export REMORA_PERIOD", "int", "="),
]
# In addition I check the combination of tasks_per_node, queue (for the
# processor type), and cpus_per_task
print("\n" + "=" * 79)
print("Checking {}\n".format(os.path.basename(submit_filepath)))

new_file = submit_filepath + ".temp"

# Here there are some consistency checks I want to make sure the number of
# nodes and MPI ranks, etc, are consistent
# first just go through the file and identify these things
with open(submit_filepath, "r") as in_file:
    for line in in_file:
        if line.startswith("#SBATCH --"):
            data = line.split("--")[-1]
            # all these options have an "=" in their specification
            if "=" in data:
                key, old_value = data.split("=")
                old_value = old_value.strip()  # get rid of newline
                if key == "ntasks-per-node":
                    ranks_per_node = old_value
                elif key == "cpus-per-task":
                    cpus_per_task = old_value
                elif key == "partition":
                    partition = old_value

# then we can ask the user whether they want to change these things
answer_partition = input("queue = {}: ".format(partition))
answer_ranks_per_node = input("MPI ranks per node = {}: ".format(ranks_per_node))
# we don't ask about cpus per task, we calculate that ourself

# check for places where the user wants to keep it the same
if len(answer_partition) == 0:
    answer_partition = partition
if len(answer_ranks_per_node) == 0:
    answer_ranks_per_node = ranks_per_node

# then validate these answers for type
try:
    utils.test_integer(answer_ranks_per_node)
    if "frontera" in hostname:
        test_queue = utils.test_queue_frontera
    elif "stampede2" in hostname:
        test_queue = utils.test_queue_stampede2
    elif "anvil" in hostname:
        test_queue = utils.test_queue_anvil
    else:
        raise ValueError("Machine not recognized")
    test_queue(answer_partition)

except ValueError:
    raise ValueError("These answers are not valid.")

# Turn the node model into the number of CPUs on those nodes
if "skx" in answer_partition:
    ncpus = "48"
else:
    if "frontera" in hostname:
        ncpus = "56"
    elif "stampede2" in hostname:
        ncpus = "68"
    elif "anvil" in hostname:
        ncpus = "128"

# Then check whether the use picked an appropriate number of mpi tasks
# per node. It must evenly divide the number of cpus on the node
n_cpus_per_task = float(ncpus) / float(answer_ranks_per_node)
if int(n_cpus_per_task) != n_cpus_per_task:
    raise ValueError(
        "Running {} MPI ranks per mode results in an "
        "uneven number of cores per rank. Choose again."
        "".format(answer_ranks_per_node)
    )
n_cpus_per_task = str(int(n_cpus_per_task))

# Then we can go through and change things. We'll change things that we
# need as we go, whether that's with the submit line or ones in the original
# list passed in here
with open(submit_filepath, "r") as in_file:
    with open(new_file, "w") as out_file:
        for line in in_file:
            # fix the things that are easily identified
            match = None
            for start in submit_updates:
                if line.startswith(start.name):
                    match = start

            if match is not None:
                new_line = match.edit_line_func(line, match.separator, match.check_func)
            # there are also a few things we know we need to change
            # There are a few lines where we know the answer already
            elif line.startswith("#SBATCH --partition"):
                new_line = utils.edit_line(line, "=", test_queue, answer_partition)
            elif line.startswith("#SBATCH --ntasks-per-node"):
                new_line = utils.edit_line(
                    line, "=", utils.test_integer, answer_ranks_per_node
                )
            elif line.startswith("#SBATCH --cpus-per-task"):
                new_line = utils.edit_line(
                    line, "=", utils.test_integer, n_cpus_per_task
                )
            elif line.startswith("cp") and ".cfg" in line:
                new_line = edit_line_copy_config(line)
            elif "ibrun" in line and not line.startswith("#"):
                new_line = edit_line_submission(line)
            else:  # not a line of interest, don't change it
                new_line = line
            out_file.write(new_line)

utils.replace_files(submit_filepath, new_file)
