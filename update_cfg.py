import sys
import os
import utils

home_dir = os.path.abspath(sys.argv[1])
defs_file = home_dir + os.sep + "defs.h"
run_dir = home_dir + os.sep + sys.argv[2]
config_file = sys.argv[3]
config_filepath = run_dir + os.sep + config_file


def edit_line_refinement(original_line, test_func, _):
    """
    Edit a line that involved refinement
    
    The extra parmater is required since we normally use it for the 
    separator, but in this case we know what to look for so its not used
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
        utils.test_integer(answer_from_level)
    # same thing with this one
    if len(answer_to_level) == 0:  # don't change anything
        answer_to_level = old_to_level
    else:
        utils.test_integer(answer_to_level)

    # Then replace the appropriate parts of the original line with the new data
    to_replace_from_level = "from-level={}".format(old_from_level)
    new_from_level        = "from-level={}".format(int(answer_from_level))
    to_replace_to_level = "to-level={}".format(old_to_level)
    new_to_level        = "to-level={}".format(int(answer_to_level))
    final_line = original_line.replace(to_replace_from_level, new_from_level)
    final_line = final_line.replace(to_replace_to_level, new_to_level)
    return final_line

# put those line editing functions into the dictionary that utils uses to 
# actually do the editing
utils.edit_line_dict["refinement"] = edit_line_refinement

# ==============================================================================
#
# The actual work is done here!!!
#
# ==============================================================================
config_updates = [utils.CheckLine("directory:outputs", "dir"),
                #   utils.CheckLine("directory:logs", "dir"),
                  utils.CheckLine("snapshot-epochs", "epochs"),
                #   utils.CheckLine("refinement", "none"),
                  utils.CheckLine("auni-stop", "float"),
                  utils.CheckLine("max-dark-matter-level", "int"),
                  utils.CheckLine("sf:min-level", "int")]
# We don't want to update the log directory because it should be automatically
# generated in the submit script, as we want fresh log directories for each 
# run.
# Refinement isn't done either, as it does not change throughoug the history
# of a given run

utils.update_file(config_filepath, config_updates)
