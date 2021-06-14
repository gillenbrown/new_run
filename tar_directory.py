"""
tar_directory.py - Tars and copies this file to Ranch.

This only works on Stampede2 right now, as it uses the $ARCHIVE environment variable.

This takes the following arguments:
- Location of the directory to copy
- (optional) Directory to copy this to on Ranch. If not included, the path will be
  the same as the current path, just modified for the different machine.
"""

import sys
from pathlib import Path
import getpass
import pexpect

# store the names of the direcory to copy and where to put it
dir_to_copy = sys.argv[1]
# If the user provides a path on Ranch, use that
if len(sys.argv) > 2:
    dir_ranch_end = sys.argv[2]
else:
    # Otherwise, use the directory we're at now.
    # Directory on the remote machine where the files will be located will be the same
    # as the directory here (other than the home directory, obviously). Identifying the
    # home directory on stampede scratch is a bit tricky, since Path.home() goes to the
    # $HOME partition, not scratch
    stampede_username = "tg862118/"
    this_dir = str(Path("./").absolute())
    dir_ranch_end = str(this_dir).partition(stampede_username)[-1]
dir_ranch = "/stornext/ranch_01/ranch/projects/TG-AST200017/" + dir_ranch_end

# also make the filename
file_name = f"{Path(dir_to_copy).name}.tar"
path_ranch = str(Path(dir_ranch) / file_name)

# Ask the user for their password, will be used later
pwd = getpass.getpass(prompt="Enter Ranch password: ")

def get_yn_input(prompt):
    answer = input(prompt + " (y/n) ")
    while answer.lower() not in ["y", "n"]:
        answer = input("Enter y or n: ")

    return answer == "y"

# Inform the user of what will happen
print(f"\n{dir_to_copy}\nwill be transferred to:\n{path_ranch}")
# Then ask them if they want to do this
if not get_yn_input("\nDo you want to execute this?"):
    print("exiting...")
    exit()

command = f"tar cf - {dir_to_copy} "
# Use Stampede2 variables to point to Ranch
command += "| ssh ${ARCHIVER} "
command += f'"cat > {path_ranch}"'
# spawn the child process, and use the encoding argument to allow me to send the
# log to stdout. Set no timeout since the copying takes a while.
child = pexpect.spawn("/bin/bash", ["-c", command], encoding="utf-8", timeout=None)
# set the output to stdout (but not the input, since that has my password)
child.logfile_read = sys.stdout
# then enter the password
child.expect("Password: ")
child.sendline(pwd)
# then wait for it to complete.
child.expect(pexpect.EOF)

print("Done!")
