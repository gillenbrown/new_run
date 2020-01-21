import sys
import os
import shutil
import filecmp
import subprocess
from collections import defaultdict
import re

home_dir = os.path.abspath(sys.argv[1])
defs_file = home_dir + os.sep + "defs.h"
run_dir = home_dir + os.sep + sys.argv[2]
config_file = sys.argv[3]
submit_file = sys.argv[4]
config_filepath = run_dir + os.sep + config_file
submit_filepath = run_dir + os.sep + submit_file

print("\nEither enter the new value or just hit enter to leave it unchanged.")

def edit_line(original_line, test_func):
    """
    Take a generic line from defs.h or config.cfg and edit a given line
    """
    # we need to get the old value
    old_value = original_line.split()[-1]
    # then get the new value
    answer = input("{}: ".format(original_line.strip()))
    if len(answer) == 0:  # don't change anything
        # if we have a directory I want to check that it exists even if we 
        # aren't changing anything
        if test_func == test_dir:
            test_func(old_value)
        # then just return the old line, since we have no changes
        return original_line
    else:
        test_func(answer)
        return original_line.replace(old_value, answer)

def edit_line_refinement(original_line, test_func):
    """
    Edit a line that involved refinement
    """
    # note that here test_func is not used, but will be kept in the argument
    # list to retain consistency with the other functions

    # here the only things we'll allow the user to modify are from-level and 
    # to-level. So we'll get those two things
    old_from_level = original_line.split()[3].split("=")[1]
    old_to_level   = original_line.split()[4].split("=")[1]
    
    print(original_line.strip())
    answer_from_level = input("\tfrom-level={}: ".format(old_from_level))
    answer_to_level   = input("\tto-level={}: ".format(old_to_level))
    
    # then do the checking to see what to change. If we don't need to change
    # anything, we'll store the original answer, since later we'll want to 
    # reconstruct the whole original string anyway
    if len(answer_from_level) == 0:  # don't change anything
        answer_from_level = old_from_level
    else:
        test_integer(answer_from_level)
    # same thing with this one
    if len(answer_to_level) == 0:  # don't change anything
        answer_to_level = old_to_level
    else:
        test_integer(answer_to_level)

    # Then replace the appropriate parts of the original line with the new data
    to_replace_from_level = "from-level={}".format(old_from_level)
    new_from_level        = "from-level={}".format(int(answer_from_level))
    to_replace_to_level = "to-level={}".format(old_to_level)
    new_to_level        = "to-level={}".format(int(answer_to_level))
    final_line = original_line.replace(to_replace_from_level, new_from_level)
    final_line = final_line.replace(to_replace_to_level, new_to_level)
    return final_line

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

def edit_line_walltime(original_line, test_func):
    """
    Edit the line in submit.pbs where the walltime is selected
    """
    # here we have to do a bit of checking on the walltime
    old_walltime = original_line.split("=")[-1].strip()
    # then get the new value
    answer = input("{}: ".format(original_line.strip()))

    # check that they added anything at all
    if len(answer) == 0:
        answer = old_walltime

    # then we have to check it. First we'll check that is has an hours, minutes,
    # seconds fields
    time_segments = answer.split(":")
    if len(time_segments) != 3:
        raise ValueError("Not an appropriate walltime format")
    # Then check that each are acceptable
    for value in time_segments:
        try:
            int(value)
        except ValueError:
            raise ValueError("Time must be a string")

    # check that seconds and minutes are correct
    for value in time_segments[1:]:
        if not 0 <= int(value) < 60:
            raise ValueError("Time is not valid")

    return original_line.replace(old_walltime, answer)

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

# put those line editing functions into a dictionary so that I can call them
# more easily later
edit_line_dict = defaultdict(lambda: edit_line)
edit_line_dict["refinement"] = edit_line_refinement
edit_line_dict["#PBS -l select"] = edit_line_select
edit_line_dict["#PBS -l walltime"] = edit_line_walltime
edit_line_dict["mpiexec"] = edit_line_mpiexec

# ==============================================================================
#
# functions to test the format of a proposed value
#
# ==============================================================================
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
    if not os.path.exists(value):
        os.makedirs(value)  # creates full path
        print("creating {}".format(value))

def test_epochs(value):
    #\d is the decimal numbers 0-9
    pattern = re.compile("^\(0\.\d*,[01]\.\d*,0\.\d*\)\Z")
    if not pattern.match(value):
        raise ValueError("this does not match the format for epochs")

def test_name(value):
    # here we don't allow any separators
    if os.sep in value:
        raise ValueError("Slashes are not allowed here.")

def test_queue(value):
    if value not in ["long", "normal", "devel", "debug"]:
        raise ValueError("This is not an acceptable queue")

# def test_refinement(value):
#     pattern = re.compile("^id=\d{1,2} weight=\d from-level=\d{1,2} to-level=\d{1,2} \d\.\d*\Z")
#     if not pattern.match(value):
#         raise ValueError("this does not match the format for refinement")

test_dict = {"int": test_integer,
             "float": test_float,
             "dir": test_dir,
             "epochs": test_epochs,
             "name": test_name,
             "queue": test_queue,
             "none": lambda: True}

# ==============================================================================
#
# functions to actually do the writing of the files
#
# ==============================================================================
def replace_files(old_file, new_file):
    # if the files are the same delete the new one, but if they are different
    # replace the old with the new
    files_same = filecmp.cmp(old_file, new_file)
    if not files_same:
        print("\nReplacing {}".format(old_file))
        shutil.copy2(new_file, old_file)
    # remove the new one regardless, since we copied earlier
    os.remove(new_file)

def update_file(old_file, lines_to_update):
    print("\n" + "="*79)
    print("Checking {}\n".format(os.path.basename(old_file)))

    new_file = old_file + ".temp"

    with open(old_file, "r") as in_file:
        with open(new_file, "w") as out_file:
            for line in in_file:
                match = None
                for start in lines_to_update:
                    if line.startswith(start.name):
                        match = start

                if match is not None:
                    # A few of thiese have special formats that have to be 
                    # checked separately
                    new_line = match.edit_line_func(line, match.check_func)
                    out_file.write(new_line)
                else:  # not a line of interest, don't change it
                    out_file.write(line)

    replace_files(old_file, new_file)

def update_submit(old_file, lines_to_update):
    print("\n" + "="*79)
    print("Checking {}\n".format(os.path.basename(old_file)))

    new_file = old_file + ".temp"

    # Here there are some consistency checks I want to make sure the number of
    # nodes and MPI ranks, etc, are consistent
    # first just go through the file and identify these things
    with open(old_file, "r") as in_file:
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

    # then validate these answers for type
    try:
        test_name(answer_model)
        test_integer(answer_n_nodes)
        test_integer(answer_ranks_per_node)
    except ValueError:
        raise ValueError("These answers are not valid.")

    # Turn the node model into the number of CPUs on those nodes
    if model == "bro":
        ncpus = "28"
    else:
        raise ValueError("Model not supported yet")

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
    with open(old_file, "r") as in_file:
        with open(new_file, "w") as out_file:
            for line in in_file:
                match = None
                for start in lines_to_update:
                    if line.startswith(start.name):
                        match = start

                if match is not None:
                    # A few of thiese have special formats that have to be 
                    # checked separately
                    new_line = match.edit_line_func(line, match.check_func)
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

    replace_files(old_file, new_file)


# ==============================================================================
#
# Class that contains info on lines that can be easily modified
#
# ==============================================================================
class CheckLine(object):
    def __init__(self, name, dtype):
        self.name = name
        self.check_func = test_dict[dtype]
        self.edit_line_func = edit_line_dict[name]

defs_updates = [CheckLine("#define num_refinement_levels", "int")]
config_updates = [CheckLine("directory:outputs", "dir"),
                  CheckLine("directory:logs", "dir"),
                  CheckLine("snapshot-epochs", "epochs"),
                  CheckLine("refinement", "none"),
                  CheckLine("auni-stop", "float"),
                  CheckLine("max-dark-matter-level", "int"),
                  CheckLine("sf:min-level", "int")]
submit_updates = [CheckLine("#PBS -N", "name"),
                  CheckLine("#PBS -l walltime", "none"),
                  CheckLine("#PBS -q", "queue")]

# ==============================================================================
#
# The actual work is done here!!!
#
# ==============================================================================
update_file(defs_file, defs_updates)
update_file(config_filepath, config_updates)
update_submit(submit_filepath, submit_updates)

