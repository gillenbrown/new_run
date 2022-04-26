set -e
# causes the script to exit immediately if any errors are raised

# arguments
# 1 - home directory containing the defs.h file and argument 2

code_dir="$(dirname "$(readlink -f "$0")")" 
home_dir=$1

module load python3
echo "Either enter the new value or just hit enter to leave it unchanged."
python3 $code_dir/update_run_files.py $home_dir
module reset
module load gsl
cd $home_dir
make

# Then copy the submission script to $SCRATCH. It will handle creating the
# directories there as appropriate
new_submit=submit_$(date +"%Y_%B_%d_%H.%M.%S").sh
cp run/submit.sh $SCRATCH/$new_submit
# Submit it from scratch, as this will reduce the file load on $WORK, as
# requested by TACC
cd $SCRATCH
sbatch $new_submit
