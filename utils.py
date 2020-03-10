import os
import shutil
import filecmp
import subprocess
from collections import defaultdict
import re

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

def test_queue_pleiades(value):
    if value not in ["long", "normal", "devel", "debug"]:
        raise ValueError("This is not an acceptable queue")

def test_queue_stampede2(value):
    if value not in ["development", "normal", "large", "long", "flat-quadrant", 
                     "skx-dev", "skx-normal", "skx-large"]:
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

test_dict = {"int": test_integer,
             "float": test_float,
             "dir": test_dir,
             "epochs": test_epochs,
             "name": test_name,
             "queue_pleiades": test_queue_pleiades,
             "queue_stampede2": test_queue_stampede2,
             "walltime": test_walltime,
             "none": lambda: True}

# ==============================================================================
#
# Class that contains info on lines that can be easily modified
#
# ==============================================================================
class CheckLine(object):
    def __init__(self, name, dtype, separator=" "):
        self.name = name
        self.check_func = test_dict[dtype]
        self.edit_line_func = edit_line_dict[name]
        self.separator = separator

# ==============================================================================
#
# Main function that edits a given line
#
# ==============================================================================
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


# put those line editing functions into a dictionary so that I can call them
# more easily later. In files that have more complex needs, this dictionary
# can be appended to
edit_line_dict = defaultdict(lambda: edit_line)


# ==============================================================================
#
# function to actually do the writing of the files
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


# ==============================================================================
#
# master function that can be called from outside this file
#
# ==============================================================================
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
                    # A few of these have special formats that have to be 
                    # checked separately
                    new_line = match.edit_line_func(line, match.separator, 
                                                    match.check_func)
                    out_file.write(new_line)
                else:  # not a line of interest, don't change it
                    out_file.write(line)

    replace_files(old_file, new_file)
