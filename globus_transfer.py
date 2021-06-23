"""
globus_transfer.py

Copies one file using Globus. Takes the following command line arguments:
- path to the source to copy. This is relative to the current path.
- name of the destination endpoint. Must match one of my bookmarks!
- path to copy the item to. This is relative to the path defined in the bookmark.
- (optional) label for the transfer
"""
import sys
from pathlib import Path
import subprocess

# validate user options
if len(sys.argv) < 4:
    raise ValueError("Need 3 command line options!")
if len(sys.argv) > 5:
    raise ValueError("Too many command line options!")
# get user options
source_end_path = sys.argv[1]
destination_name = sys.argv[2]
destination_end_path = sys.argv[3]
if len(sys.argv) == 5:
    label = sys.argv[4]
else:
    label = None

# ======================================================================================
#
# Get the current directory to know what our source is
#
# ======================================================================================
working_dir = Path(".").resolve()
if str(working_dir).startswith("/scratch/06912/tg862118"):
    source_name = "stampede2_scratch"
elif str(working_dir).startswith("/work2/06912/tg862118/stampede2"):
    source_name = "stampede2_work2"
elif str(working_dir).startswith("/work/06912/tg862118/stampede2"):
    source_name = "stampede2_work"
elif str(working_dir).startswith("/home1/06912/tg862118"):
    source_name = "stampede2_home"
else:
    raise ValueError("I don't know how to transfer from here!")

# ======================================================================================
#
# Parse the Globus bookmarks to know where to transfer an item
#
# ======================================================================================
# run the bookmark command to see where I know how to transfer things
process = subprocess.run(["globus", "bookmark", "list"], stdout=subprocess.PIPE)
bookmarks_text = process.stdout.decode("utf-8")

# then parse the bookmark output. Use a class for this, for simplicity
class Bookmark(object):
    def __init__(self, bookmark_name, endpoint_id, path):
        self.name = bookmark_name
        self.endpoint_id = endpoint_id
        self.path = path


bookmarks = []
for line in bookmarks_text.split("\n"):
    # skip header, divider, and empty rows:
    if ("Bookmark ID" in line) or ("-------" in line) or (len(line.strip()) == 0):
        continue

    # get the entries, and clean them up. Vertical bars used to separate columns
    items = [l.strip() for l in line.split("|")]
    bookmarks.append(Bookmark(items[0], items[2], items[4]))

# ======================================================================================
#
# match the user's commands to a bookmark
#
# ======================================================================================
# set up dummy variables to check that the paths were found
source, destination = None, None
for b in bookmarks:
    if b.name == source_name:
        source = b
    if b.name == destination_name:
        destination = b

if source is None:
    raise ValueError(f"Source bookmark {source_name} not found!")
if destination is None:
    raise ValueError(f"Destination bookmark {destination_name} not found!")

# ======================================================================================
#
# handle paths fully
#
# ======================================================================================
# Now we can extend the paths. The source dir will be the working directory plus the
# path the user said
source_file_path = working_dir / source_end_path
# the destination is simply the bookmark path plus the user path
destination_file_path = (
    Path(destination.path) / destination_end_path / source_file_path.name
)

# ======================================================================================
#
# Then do the transfer
#
# ======================================================================================
def get_yn_input(prompt):
    answer = input(prompt + " (y/n) ")
    while answer.lower() not in ["y", "n"]:
        answer = input("Enter y or n: ")

    return answer == "y"


print(f"\n{source.name}:{str(source_file_path)}")
print("Will be transferred to")
print(f"{destination.name}:{str(destination_file_path)}")
if not get_yn_input("\nDo you want to execute this?"):
    print("exiting...")
    exit()

# piece together all the options
command = ["globus", "transfer"]
if label is not None:
    command += ["--label", label]
command += [
    f"{source.endpoint_id}:{source_file_path}",
    f"{destination.endpoint_id}:{destination_file_path}",
]

# then do it!
subprocess.run(command)
# Do not delete the file afterwards, since the transfer will be put in the background
