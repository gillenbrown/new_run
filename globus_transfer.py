"""
globus_transfer.py

Copies one file using Globus. Takes the following command line arguments:
- name of the source endpoint. Must match one of my bookmarks! This is assumed to be
  the current machine.
- name of the destination endpoint. Must match one of my bookmarks!
- path to the source to copy. This is relative to the current path.
- path to copy the item to. This is relative to the path defined in the bookmark.
- (optional) label for the transfer
"""
import sys
from pathlib import Path
import subprocess

# validate user options
if len(sys.argv) < 5:
    raise ValueError("Need 4 command line options!")
if len(sys.argv) > 6:
    raise ValueError("Too many command line options!")
# get user options
source_name = sys.argv[1]
destination_name = sys.argv[2]
source_end_path = sys.argv[3]
destination_end_path = sys.argv[4]
if len(sys.argv) == 6:
    label = sys.argv[5]
else:
    label = None

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
    raise ValueError("Source bookmark not found!")
if destination is None:
    raise ValueError("Destination bookmark not found!")

# ======================================================================================
#
# handle paths fully
#
# ======================================================================================
# first check that the user is on the machine they say they are
working_dir = Path(".").resolve()
# the source path can be the home directory, so we need to parse that to compare fairly
if source.path == "/~/":
    source.path = str(Path().home().resolve())
# strip ending /, it can mess with comparison below
if source.path.endswith("/"):
    source.path = source.path[:-1]
# then do the comparison
if not str(working_dir).startswith(source.path):
    print(working_dir, source.path)
    raise RuntimeError(
        "It doesn't like you're on the source machine!\n"
        f"You said you're on {source.name}."
    )

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
