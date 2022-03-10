#!/bin/bash

###############################################################################
#                   CLEAN_EXPERIMENT t0ni EXPERIMENT
###############################################################################
###################
# Autosubmit header
###################
set -xuve
job_name_ptrn='/gpfs/scratch/bsc32/bsc32627/t0ni/LOG_t0ni/t0ni_CLEAN_EXPERIMENT'
echo $(date +%s) > ${job_name_ptrn}_STAT

###################
# Autosubmit job
###################

#!/usr/bin/env bash
set -xuve

########################################################################################################################
# this job removes all remaining experiment folders from scratch and intermediate storage
# intended to be executed from DT/bscearth000 machines
# Author: J.R.Berlin
########################################################################################################################

#
# Var instantiation & architecture
#

STAMP=$(date +%Y_%m_%d_%H_%M)
CURRENT_ARCH=transfer_node
HPCPROJ=bsc32
HPCARCH=marenostrum4
HPCUSER=bsc32627
HPCHOST=mn1.bsc.es
EXPID=t0ni
JOBNAME=t0ni_CLEAN_EXPERIMENT
ROOTDIR=/gpfs/scratch/bsc32/bsc32627/t0ni
TEMPLATE_NAME=ecearth3
MODEL=ecearth
PROJDEST=auto-ecearth3
LOGDIR=${ROOTDIR}/LOG_${EXPID}
SCRATCH_DIR=/gpfs/scratch
PROJDIR=${ROOTDIR}/${PROJDEST}
START_date=
MEMBER=None
DT_USER=
DT_HOST=
# For moving logs we dont need to use intermeadiate storage in this case
USE_INTERMEDIATE_STORAGE=FALSE
USE_DT_COMMANDS=TRUE
# get the mkdir function of the platform
. ${PROJDIR}/plugins/utils.sh
. ${PROJDIR}/platforms/${CURRENT_ARCH}/configure.sh

#set environment % architecture definitions
load_platform_environment

# Check if DT commands are available in case that CLEAN is done in other platform different that DT nodes
exist_dtrsync=$(echo $(command -v dtrsync))
if [[ "${USE_INTERMEDIATE_STORAGE-}" == "TRUE" || -z "${exist_dtrsync-}" ]]; then
  USE_DT_COMMANDS=FALSE
fi


#####################################################################################################################
# Globals:
# LOGDIR,  EXPID, CHUNK, START_date, MEMBER
# Arguments:
#   None
# Returns:
#   None
# Purpose: Prepare log files for transferring in TRANSFER_MEMBER, basically the whole folder is compressed
# user later in clean_member_store_logs
#####################################################################################################################
function prepare_logs() {
  cd ${LOGDIR}
  logfiles_ptrn="${EXPID}_"
  ls -1 *${logfiles_ptrn}* | xargs tar -cvf ../${logs_tarfile}
}

#general
setup_paths
#transfer related (esarchive)
setup_paths_transfer_${CURRENT_ARCH}
#for the intermediate storage
setup_paths_localtrans
#save all logs of the experiment in a tar.gz file
save_logs
#clean up folders
remove_experiment_folders

###################
# Autosubmit tailer
###################
set -xuve
echo $(date +%s) >> ${job_name_ptrn}_STAT
touch ${job_name_ptrn}_COMPLETED
exit 0

