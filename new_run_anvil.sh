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
submit=${4:-submit.sh}

echo "Either enter the new value or just hit enter to leave it unchanged."
module load python/3.9.5
python3 $code_dir/update_defs.py $home_dir $run_dir
python3 $code_dir/update_cfg.py $home_dir $run_dir $config
python3 $code_dir/update_submit_slurm.py $home_dir $run_dir $submit $config
module reset
module load gsl intel/19.0.5.281
cd $home_dir
make

# Then copy the submission script to $SCRATCH. It will handle creating the
# directories there as appropriate
new_submit=submit_$(date +"%Y_%B_%d_%H.%M.%S").sh
cp $run_dir/submit.sh $SCRATCH/$new_submit
# Submit it from scratch, as this will reduce the file load on $WORK, as
# requested by TACC
cd $SCRATCH
sbatch $new_submit