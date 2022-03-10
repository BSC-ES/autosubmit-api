#!/bin/bash

###############################################################################
#                   SYNCHRONIZE t0ni EXPERIMENT
###############################################################################
###################
# Autosubmit header
###################
set -xuve
job_name_ptrn='/gpfs/scratch/bsc32/bsc32627/t0ni/LOG_t0ni/t0ni_SYNCHRONIZE'
echo $(date +%s) > ${job_name_ptrn}_STAT

###################
# Autosubmit job
###################

set -xuve

#
# Architecture
#

HPCARCH=marenostrum4
CURRENT_ARCH=transfer_node
PROJDIR=/esarchive/autosubmit/t0ni/proj/auto-ecearth3
SCRATCH_DIR=/gpfs/scratch
HPCPROJ=bsc32
HPCUSER=bsc32627
EXPID=t0ni
PROJDEST=auto-ecearth3
ROOTDIR=/gpfs/scratch/bsc32/bsc32627/t0ni
HPCHOST=mn1.bsc.es
UPDATE_MODEL=TRUE
DTHOST=
DT_HOST=
DT_USER=
USE_DT_COMMANDS=TRUE
MODEL_EXTRACT=TRUE
CURRENT_ROOTDIR=/gpfs/scratch/bsc32/bsc32627/t0ni
PROJNAME=auto-ecearth3

#By default we set to true if empty
if [[ -z "${UPDATE_MODEL}" ]]; then
  UPDATE_MODEL=TRUE
fi

#By default we set to true if empty
if [[ -z "${MODEL_EXTRACT-}" ]]; then
  MODEL_EXTRACT=TRUE
fi

#needed to reference correctly the paths and load the source needed
[ -d /gpfs/archive/bsc32 ] && PROJDIR=/gpfs/archive/bsc32/${PROJDIR}




# in the case we are running from the cluster itself, we need to retrieve the needed files first
if [[ ${CURRENT_ARCH} == ${HPCARCH} ]]; then
  #this code should be sent to the cluster if USE_DT_MACHINE=TRUE
  if [[ -z "${DT_HOST}" || -z "${DT_USER}" ]]; then
    echo "DT_HOST or DT_USER undefined, please check proj.conf and add relevant configuration or define a different PLATFORM to the job"
    exit 1
  fi

  # Since model is not present yet, copy synchoronize/utils plugins to destination in advance so main SYNC file can run
  DEST_SYNC_PLUGIN=${DT_USER}@${DT_HOST}:/gpfs/archive/bsc32/${PROJDIR}/plugins
  DEST_SYNC_PLATFORM=${DT_USER}@${DT_HOST}:/gpfs/archive/bsc32/${PROJDIR}/platforms/${CURRENT_ARCH}
  DEST_SYNC_PLATFORM_COMMON=${DT_USER}@${DT_HOST}:/gpfs/archive/bsc32/${PROJDIR}/platforms/common
  #Set proj dirr temporally
  PROJDIR=${ROOTDIR}/${PROJDEST}

  if [ ! -d "${ROOTDIR}/${PROJDEST}/plugins" ]; then
    mkdir -p ${ROOTDIR}/${PROJDEST}/plugins
  fi

  if [ ! -d "${ROOTDIR}/${PROJDEST}/platforms" ]; then
    mkdir -p ${ROOTDIR}/${PROJDEST}/platforms/common
    mkdir -p ${ROOTDIR}/${PROJDEST}/platforms/${HPCARCH}
  fi

  # Send the needed files to the HPC
  rsync --recursive --links --perms --times --owner --devices --specials --verbose ${DEST_SYNC_PLUGIN}/utils.sh ${PROJDIR}/plugins
  rsync --recursive --links --perms --times --owner --devices --specials --verbose ${DEST_SYNC_PLATFORM_COMMON}/common.filesystem.sh ${PROJDIR}/platforms/common
  rsync --recursive --links --perms --times --owner --devices --specials --verbose ${DEST_SYNC_PLATFORM_COMMON}/common.utils.sh ${PROJDIR}/platforms/common
  rsync --recursive --links --perms --times --owner --devices --specials --verbose ${DEST_SYNC_PLATFORM}/filesystem.sh ${PROJDIR}/platforms/${CURRENT_ARCH}
  rsync --recursive --links --perms --times --owner --devices --specials --verbose ${DEST_SYNC_PLATFORM}/utils.sh ${PROJDIR}/platforms/${CURRENT_ARCH}
fi

. ${PROJDIR}/platforms/${CURRENT_ARCH}/filesystem.sh
# copy ( depending of the executing machine ) the platform folder to the host
copy_platform_environment_to_host
## setup common project path & supporting files
setup_synchronize
#check if the model is present, we want to avoid the case UPDATE_MODEL=FALSE and the sources are not present
check_model_existence

if [[ "${UPDATE_MODEL}" == "TRUE" ]] || [[ "${MODEL_EXISTS}" == "FALSE" ]]; then
  #This a platform dependant function that executes the synchronization based on the underlying choosen architecture
  do_synchronize
else
  echo "UPDATE_MODEL set to false, model will not be updated in the cluster"
  echo "common.synchronize Done"
fi

###################
# Autosubmit tailer
###################
set -xuve
echo $(date +%s) >> ${job_name_ptrn}_STAT
touch ${job_name_ptrn}_COMPLETED
exit 0

