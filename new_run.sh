set -e
# causes the script to exit immediately if any errors are raised

# arguments
# 1 - home directory containing the defs.h file and argument 2
# 2 - directory within #1 where the config and submit files are located. Can be
#     left blank, in which case "run" will be used
# 3 - name of the config file. Can be left blank, in which case "config.cfg"
#     will be used
# 4 - name of the submission script. Can be left blank, in which case 
#     "submit.pbs" will be used

code_dir="$(dirname "$(readlink -f "$0")")" 
home_dir=$1
run_dir=${2:-run}
config=${3:-config.cfg}
submit=${4:-submit.pbs}

module load comp-intel/2018.3.222 python3/Intel_Python_3.6_2018.3.222
python $code_dir/new_run.py $home_dir $run_dir $config $submit
module unload python3/Intel_Python_3.6_2018.3.222
module load mpi-sgi/mpt
cd $home_dir
make
cp art $run_dir/
cd $run_dir
qsub $submit
