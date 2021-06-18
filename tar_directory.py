"""
tar_directory.py - Tars and copies this file to Ranch.

This only works on Stampede2 right now, as it uses the $ARCHIVE environment variable.

This takes the following arguments:
- Location of the directory to copy
- (optional) Directory to copy this to on Ranch. If not included, the path will be
  the same as the current path, just modified for the different machine.
- (optional) Whether or not to include the date in the directory name. To not include
  the date, pass 'no-date'.
Note that these last two parameters can be in any order.
"""

import datetime
import sys
from pathlib import Path
import getpass
import pexpect
import shutil

# as we parse the arguments we'll remove them, so remove the script name
sys.argv.pop(0)
# store the names of the direcory to copy and where to put it
dir_to_copy_raw = sys.argv[0]
dir_to_copy = Path(dir_to_copy_raw).resolve()
sys.argv.pop(0)
# if not specified, do add the date
add_date = True
if "no-date" in sys.argv:
    add_date = False
    sys.argv.remove("no-date")

# if not specified, do not delete
delete = False
if "delete" in sys.argv:
    delete = True
    sys.argv.remove("delete")

# there should only be one item left
if len(sys.argv) > 1:
    raise ValueError("Too many parameters!")

# anything else is the directory
dir_ranch_end = None
if len(sys.argv) == 1:
    dir_ranch_end = sys.argv[0]

if dir_ranch_end is None:
    # Otherwise, use the directory we're at now.
    # Directory on the remote machine where the files will be located will be the same
    # as the directory here (other than the home directory, obviously). Identifying the
    # home directory on stampede scratch is a bit tricky, since Path.home() goes to the
    # $HOME partition, not scratch
    stampede_username = "tg862118/"
    this_dir = str(Path("./").absolute())
    # on WORK there is an extra stampede2 term that I should remove
    this_dir = this_dir.replace("stampede2/", "")
    dir_ranch_end = this_dir.partition(stampede_username)[-1]
dir_ranch = "/stornext/ranch_01/ranch/projects/TG-AST200017/" + dir_ranch_end

# also make the filename
if add_date:
    date = datetime.date.today().strftime("%Y_%m_%d")
    file_name = f"{dir_to_copy.name}_{date}.tar"
else:
    file_name = f"{dir_to_copy.name}.tar"
path_ranch = str(Path(dir_ranch) / file_name)

def get_yn_input(prompt):
    answer = input(prompt + " (y/n) ")
    while answer.lower() not in ["y", "n"]:
        answer = input("Enter y or n: ")

    return answer == "y"

# Inform the user of what will happen
print(f"\n{dir_to_copy}\nwill be transferred to:\n{path_ranch}")
if delete:
    print("========== THEN WILL BE DELETED! ==========")
# Then ask them if they want to do this
if not get_yn_input("\nDo you want to execute this?"):
    print("exiting...")
    exit()

# Ask the user for their password, will be used later
pwd = getpass.getpass(prompt="Enter Ranch password: ")

# then copy the files
command = f"tar cf - {dir_to_copy_raw} "
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
print("Done copying!")

def delete_folder(dir_to_delete):
    for item in dir_to_delete.iterdir():
        # Have to avoid traversing symlinks and deleting their contents!
        if item.is_dir() and not item.is_symlink():
            delete_folder(item)
        else:
            item.unlink()
    dir_to_delete.rmdir()

if delete:
    delete_folder(dir_to_copy)
    print("Done deleting!")
