#!/bin/bash

###############################################################################
#                   SIM a29z EXPERIMENT
###############################################################################
#
#SBATCH --qos=debug
#SBATCH -A bsc32
#
#
#
#SBATCH --cpus-per-task=1
#SBATCH -n 2
#SBATCH -t 00:05:00
#SBATCH -J a29z_19550501_fc1_2_SIM
#SBATCH --output=/gpfs/scratch/bsc32/bsc32985/a29z/LOG_a29z/a29z_19550501_fc1_2_SIM.cmd.out
#SBATCH --error=/gpfs/scratch/bsc32/bsc32985/a29z/LOG_a29z/a29z_19550501_fc1_2_SIM.cmd.err

#
###############################################################################
###################
# Autosubmit header
###################
set -xuve
job_name_ptrn='/gpfs/scratch/bsc32/bsc32985/a29z/LOG_a29z/a29z_19550501_fc1_2_SIM'
echo $(date +%s) > ${job_name_ptrn}_STAT

###################
# Autosubmit job
###################

sleep 30
###################
# Autosubmit tailer
###################
set -xuve
echo $(date +%s) >> ${job_name_ptrn}_STAT
touch ${job_name_ptrn}_COMPLETED
exit 0

