import sys
import os
import utils

home_dir = os.path.abspath(sys.argv[1])
defs_file = home_dir + os.sep + "defs.h"
run_dir = home_dir + os.sep + sys.argv[2]
submit_file = sys.argv[3]
config_file = sys.argv[4]
submit_filepath = run_dir + os.sep + submit_file

def edit_line_select(original_line, model, n_nodes, ranks_per_node, ncpus):
    """
    edit the line in submit.pbs that selects what resources are needed
    """
    # here we need to change the select line. I'll assume that the values 
    # passed in here have already been error checked
    new_line = original_line
    full_select = original_line.split()[-1]
    for item in full_select.split(":"):
        # get the old value, plus the name of the field
        key, old_value = item.split("=")

        if key == "select":
            new_value = n_nodes
        elif key == "model":
            new_value = model
        elif key == "mpiprocs":
            new_value = ranks_per_node
        elif key == "ncpus":
            new_value = ncpus
        else:
            raise ValueError("Key {} not recognized".format(key))

        # then we can use this to reconstruct the new item
        new_item = item.replace(old_value, new_value)
        # then put this back in the original
        new_line = new_line.replace(item, new_item)

    return new_line

def edit_line_mpiexec(original_line, n_nodes, 
                      ranks_per_node, n_cpus_per_task):
    """
    Edit the line in submit.pbs where ART is actually called
    """
    new_line = original_line
    # this one is a bit complicated. We know the things about the number of 
    # nodes and whatnot. The only thing we need to ask the user about is the 
    # place to restart the simulation from

    # This is hard to manage, so I'll go through things one at a time manually
    # first is the total number of MPI ranks
    old_n_tasks = original_line.split()[2]
    new_n_tasks = int(n_nodes) * int(ranks_per_node)
    new_line = new_line.replace("-np {}".format(old_n_tasks),
                                "-np {}".format(new_n_tasks))

    # Then edit the number of MPI ranks per node. In the file this is of the 
    # format "-nXXX".
    old_ranks_per_node = original_line.split()[5][2:]
    new_line = new_line.replace("-n{}".format(old_ranks_per_node),
                                "-n{}".format(ranks_per_node))

    # then the number of cpus per task. This is of the format "-tXXX"
    old_cpu_per_task = original_line.split()[6][2:]
    new_line = new_line.replace("-t{}".format(old_cpu_per_task),
                                "-t{}".format(n_cpus_per_task))

    # I'll also make sure the config file specified is what the user wants
    old_config = original_line.split()[9]
    new_line = new_line.replace(old_config, config_file)

    # Then we can edit the place to start the sim
    # note that "-root" is used exclusively for initial conditions, while 
    # "-r" is used when resuming from another snapshot
    old_restart = original_line.split()[10]
    answer = input("{}: ".format(old_restart))
    if len(answer) == 0:
        answer = old_restart
    # then do some error checking
    if answer.startswith("-r="):
        prefix, scale_factor = answer.split("=")
        try:
            assert 0.0 <= float(scale_factor) <= 1.0
        except (ValueError, AssertionError):
            raise ValueError("Bad restart option.")
    elif answer.startswith("-root="):
        prefix, location = answer.split("=")
        # here the location is a directory with "music" appended to it. this
        # checking is more work than I want to do, so I won't do it. The line
        # above will do a bit of checking, in that it will make sure two things
        # exist here
    else:
        raise ValueError("Bad restart option.")
    # if we got here the answer is fine
    new_line = new_line.replace(old_restart, answer)

    return new_line

# ==============================================================================
#
# The actual work is done here!!!
#
# ==============================================================================
submit_updates = [utils.CheckLine("#PBS -N", "name"),
                  utils.CheckLine("#PBS -l walltime", "walltime", "="),
                  utils.CheckLine("#PBS -q", "queue_pleiades")]

# note that this is quite different from the other ones, since I have to check
# for consistency of the number of nodes, cores, etc., so I don't use the 
# default function for this writing      

print("\n" + "="*79)
print("Checking {}\n".format(os.path.basename(submit_filepath)))

new_file = submit_filepath + ".temp"

# Here there are some consistency checks I want to make sure the number of
# nodes and MPI ranks, etc, are consistent
# first just go through the file and identify these things
with open(submit_filepath, "r") as in_file:
    for line in in_file:
        if line.startswith("#PBS -l select"):
            full_select = line.split()[-1]
            for item in full_select.split(":"):
                key, old_value = item.split("=")
                if key == "select":
                    n_nodes = old_value
                elif key == "model":
                    model = old_value
                elif key == "mpiprocs":
                    ranks_per_node = old_value

# then we can ask the user whether they want to change these things
answer_model = input("node model = {}: ".format(model))
answer_n_nodes = input("number of nodes = {}: ".format(n_nodes))
answer_ranks_per_node = input("MPI ranks per node = {}: ".format(ranks_per_node))

# check for places where the user wants to keep it the same
if len(answer_model) == 0:
    answer_model = model
if len(answer_n_nodes) == 0:
    answer_n_nodes = n_nodes
if len(answer_ranks_per_node) == 0:
    answer_ranks_per_node = ranks_per_node

# Turn the node model into the number of CPUs on those nodes
if answer_model == "bro":
    ncpus = "28"
else:
    raise ValueError("Model not supported yet")

# then validate these answers for type
try:
    utils.test_name(answer_model)
    utils.test_integer(answer_n_nodes)
    utils.test_integer(answer_ranks_per_node)
except ValueError:
    raise ValueError("These answers are not valid.")

# Then check whether the use picked an appropriate number of mpi tasks
# per node. It must evenly divide the number of cpus on the node
n_cpus_per_task = float(ncpus) / float(answer_ranks_per_node)
if int(n_cpus_per_task) != n_cpus_per_task:
    raise ValueError("Running {} MPI ranks per mode results in an "
                        "uneven number of cores per rank. Choose again."
                        "".format(answer_ranks_per_node))
n_cpus_per_task = str(int(n_cpus_per_task))

# Then we can go through and change things. We'll change things that we 
# need as we go, whether that's with the submit line or ones in the original
# list passed in here
with open(submit_filepath, "r") as in_file:
    with open(new_file, "w") as out_file:
        for line in in_file:
            match = None
            for start in submit_updates:
                if line.startswith(start.name):
                    match = start

            if match is not None:
                # A few of thiese have special formats that have to be 
                # checked separately
                new_line = match.edit_line_func(line, match.separator,
                                                match.check_func)
            # here we need to check for the submit and mpiexec lines 
            # separately
            elif line.startswith("#PBS -l select"):
                new_line = edit_line_select(line, answer_model, 
                                            answer_n_nodes, 
                                            answer_ranks_per_node, ncpus)
            elif line.startswith("mpiexec"):
                new_line = edit_line_mpiexec(line, answer_n_nodes, 
                                                answer_ranks_per_node, 
                                                n_cpus_per_task)
            else:  # not a line of interest, don't change it
                new_line = line
            out_file.write(new_line)

utils.replace_files(submit_filepath, new_file)
