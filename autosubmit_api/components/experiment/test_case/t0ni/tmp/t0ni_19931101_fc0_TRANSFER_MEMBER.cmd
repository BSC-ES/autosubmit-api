#!/bin/bash

###############################################################################
#                   TRANSFER_MEMBER t0ni EXPERIMENT
###############################################################################
###################
# Autosubmit header
###################
set -xuve
job_name_ptrn='/gpfs/scratch/bsc32/bsc32627/t0ni/LOG_t0ni/t0ni_19931101_fc0_TRANSFER_MEMBER'
echo $(date +%s) > ${job_name_ptrn}_STAT

###################
# Autosubmit job
###################

#####################################################################################################################
# script for transferring files at member level such as runtime folder and logs
# HPC to local storage
# Maintainers: J.R.Berlin
#####################################################################################################################

set -v
#
# Architecture
#
CHUNK=1
Chunk_end_date=19931130
Chunk_start_date=19931101
EXPID=t0ni
HPCARCH=marenostrum4
HPCUSER=bsc32627
HPCHOST=mn1.bsc.es
CURRENT_ARCH=transfer_node
HPCPROJ=bsc32
JOBNAME=t0ni_19931101_fc0_TRANSFER_MEMBER
#members=fc0
MEMBER=fc0
MODEL=ecearth
PROJDIR=/esarchive/autosubmit/t0ni/proj/auto-ecearth3
proj=bsc32
SCRATCH_DIR=/gpfs/scratch
START_date=19931101
stamp=%Y_%m_%d_%H_%M
ROOTDIR=/gpfs/scratch/bsc32/bsc32627/t0ni
START_date=19931101
PROJDEST=auto-ecearth3
USE_DT_COMMANDS=TRUE
if [[ -z ${USE_DT_COMMANDS} ]]; then USE_DT_COMMANDS=TRUE; fi
[[ "FALSE" == TRUE ]] && USE_INTERMEDIATE_STORAGE=TRUE || USE_INTERMEDIATE_STORAGE=FALSE

if [[ ! -d /gpfs/archive/bsc32 ]]; then
  . ${PROJDIR}/platforms/${CURRENT_ARCH}/filesystem.sh
  # copy ( depending of the executing machine ) the platform folder to the host
  copy_platform_environment_to_host
fi

export HPCPROJ
PROJDIR=${ROOTDIR}/${PROJDEST}

#
# Dealing with Model Output Transferring Back to Home (plugin)
#
. ${PROJDIR}/platforms/${CURRENT_ARCH}/configure.sh

# prepare running environment
load_platform_environment

set -vx

. ${PROJDIR}/plugins/utils.sh
. ${PROJDIR}/plugins/transfer.sh

# transfer logfiles and runtime
# For IFS+LPJG or OSM, we end up with a bunch of small files in icmcl, land_param and lpjg_forcing
# for now we copy them without the dt commands since do_transfer copies them one at a time
# and this takes much longer than doing rsync directly
# This is done at the end of the experiment to avoid transfering the files in several TRANSFER jobs at the same time.
# An improvement would be to do this in the transfer.tmpl.sh, selecting the files which belong to the chunk.
output_types="logfiles runtime icmcl land_param lpjg_forcing"
transfer_output ${Chunk_start_date} ${Chunk_end_date}

###################
# Autosubmit tailer
###################
set -xuve
echo $(date +%s) >> ${job_name_ptrn}_STAT
touch ${job_name_ptrn}_COMPLETED
exit 0

