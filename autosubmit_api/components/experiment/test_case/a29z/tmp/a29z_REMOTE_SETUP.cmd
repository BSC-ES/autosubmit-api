#!/bin/bash

###############################################################################
#                   REMOTE_SETUP a29z EXPERIMENT
###############################################################################
###################
# Autosubmit header
###################
set -xuve
job_name_ptrn='/esarchive/scratch/Earth/wuruchi/a29z/LOG_a29z/a29z_REMOTE_SETUP'
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
