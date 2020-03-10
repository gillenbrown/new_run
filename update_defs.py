import sys
import os

import utils

home_dir = os.path.abspath(sys.argv[1])
defs_file = home_dir + os.sep + "defs.h"

defs_updates = [utils.CheckLine("#define num_refinement_levels", "int")]
utils.update_file(defs_file, defs_updates)

