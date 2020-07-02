import tarfile
from pathlib import Path

from tqdm import tqdm

# set the maximum size of the tar file before compression is done. 
max_size = 500E9  # 500 GB, in bytes

# Directory where the output files will be located
home_dir = Path("./").absolute()

# first get a list of all the .art files, so I can make sure all files from a 
# given output stay together.
art_file_stems = []
for item in home_dir.iterdir():
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
    for other_file in home_dir.iterdir():
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

    tar_name = home_dir / tar_name
    # see if this already exists: don't want to override if not needed
    if tar_name.is_file():
        raise RuntimeError(f"File {tar_name} wants to be created, but already exists!")

    named_groups[tar_name] = group

# Inform the user of what will happen
print(f"\nAll tar files will be written to:\n{home_dir}")
for key in sorted(named_groups.keys()):
    print(f"\n{key.name} will contain:")
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
for name in tqdm(named_groups):
    tar = tarfile.open(name=name, mode="x")
    for file in tqdm(named_groups[name]):
        tar.add(file)
    tar.close()
