"""
tar.py - Copies files to Ranch from Stampede2, in tars of ~300GB size

This only works on Stampede2 right now, as it uses the $ARCHIVE environment variable.

This should be run from the directory where the outputs are. It will copy them to
the same path on Ranch, so this directory needs to exist. 
"""

import tarfile
from pathlib import Path
import subprocess
import shlex

from tqdm import tqdm

# set the maximum size of the tar file before compression is done. 
max_size = 300E9  # 500 GB, in bytes

# Directory where the output files will be located
this_dir = Path("./").absolute()
# Directory on the remote machine where the files will be located will be the same
# as the directory here (other than the home directory, obviously). Identifying the
# home directory on stampede scratch is a bit tricky, since Path.home() goes to the
# $HOME partition, not scratch
stampede_username = "tg862118/"
non_home_path = str(this_dir).partition(stampede_username)[-1]

# first get a list of all the .art files, so I can make sure all files from a 
# given output stay together.
art_file_stems = []
for item in this_dir.iterdir():
    if item.suffix == ".art":
        art_file_stems.append(item.stem)
# sort them, so I can group similar outputs in the same tar file
art_file_stems = sorted(art_file_stems)

# then group them. We want tar files around the size of max_size above. What we
# do is to go through the sorted outputs, adding them to a group one by one, 
# keeping track of the size as we go. If it gets above 500GB, we make a new
# group. Each of these individual groups will be turned into a tar file later.
accumulated_size = 0
file_groups = [[]]
for stem in art_file_stems:
    # check if we need to start a new set of outputs
    if accumulated_size > max_size:
        accumulated_size = 0
        file_groups.append([])

    # add the outputs to the tar file.
    for other_file in this_dir.iterdir():
        if other_file.stem == stem:
            accumulated_size += other_file.stat().st_size
            file_groups[-1].append(other_file.name)

# Make the filenames of the tar files. I'll name the tar file based on the 
# outputs that it contains.
def file_to_scale(file_name):
    suffix = file_name.split(".")[-1]
    file_name = file_name.replace("." + suffix, "")
    return file_name.split("_")[-1]

named_groups = dict()
for group in file_groups:
    # get the range of scale factors included in this tar file.
    min_scale = file_to_scale(min(group))
    max_scale = file_to_scale(max(group))

    if min_scale == max_scale:
        tar_name = f"outputs_{min_scale}.tar"
    else:
        tar_name = f"outputs_{min_scale}_to_{max_scale}.tar"

    named_groups[tar_name] = sorted(group)

# Inform the user of what will happen
for key in sorted(named_groups.keys()):
    print(f"\n{key} will contain:")
    for file in named_groups[key]:
        print(f"    - {file}")
# Then ask them if they want to do this
answer = input("\nDo you want to execute this? (y/n) ")
while answer.lower() not in ["y", "n"]:
    answer = input("Enter y or n: ")

if answer == "n":
    print("exiting...")
    exit()

# Then we can make the tar files themselves.
# for name in tqdm(named_groups):
#     tar = tarfile.open(name=this_dir / name, mode="x")
#     for file in tqdm(named_groups[name]):
#         tar.add(file)
#     tar.close()

for name in tqdm(named_groups):
    command = "tar cf - "
    for file in named_groups[name]:
        command += file
        command += " "
    # Use Stampede2 variables to point to Ranch
    command += '| ssh ${ARCHIVER} "cat > ${ARCHIVE}/' + f'{non_home_path}/{name}"'
    command = shlex.split(shlex.quote(command))
    print(command)
    # subprocess.run(command, shell=True)