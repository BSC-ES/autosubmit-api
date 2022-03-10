#!/bin/bash

###############################################################################
#                   LOCAL_SETUP t0ni EXPERIMENT
###############################################################################
###################
# Autosubmit header
###################
set -xuve
job_name_ptrn='/esarchive/autosubmit/t0ni/tmp/LOG_t0ni/t0ni_LOCAL_SETUP'
echo $(date +%s) > ${job_name_ptrn}_STAT

###################
# Autosubmit job
###################

set -xuve

#
# Architecture
#
STAMP=$(date +%Y_%m_%d_%H_%M)
HPCARCH=marenostrum4
HPCPROJ=bsc32
HPCUSER=bsc32627
EXPID=t0ni
SCRATCH_DIR=/gpfs/scratch
JOBNAME=t0ni_LOCAL_SETUP
ROOTDIR=/esarchive/autosubmit/t0ni
LOGDIR=$ROOTDIR/tmp/LOG_$EXPID
PROJDEST=auto-ecearth3
PROJDIR=/esarchive/autosubmit/t0ni/proj/auto-ecearth3
CMORIZATION=TRUE
HPCHOST=mn1.bsc.es
MEMBER=None
RUN_START_DATE=""
CMOR_REALIZATION_INDEX=""
CMOR_EXP=piControl
BSC_OUTCLASS=reduced
CMIP6_OUTCLASS=
CMOR_EXP_CUSTOM=FALSE
CMOR_ADD_STARTDATE=FALSE

#
# General Paths and Conf.
#
MODEL=ecearth
VERSION=trunk
PRECOMPILED_VERSION=

if [[ -z "${RUN_START_DATE}" ]]; then
  RUN_START_DATE="None"
fi

TEMPLATE_NAME=ecearth3
NEMO_resolution=ORCA025L75
[[ "FALSE" == TRUE ]] && TM5=TRUE || TM5=FALSE
[[ "FALSE" == TRUE ]] && DEBUG_MODE=TRUE || DEBUG_MODE=FALSE

# get the mkdir function of the platform
. ${PROJDIR}/platforms/common/common.filesystem.sh

#
# run_time_variables
#

#####################################################################################################################
# Globals: BSC_OUTCLASS, CMIP6_OUTCLASS
#
# Arguments:
#   None
# Returns:
#   None
# Purpose: set the defined outclass, before running the ecconf tool
#
#####################################################################################################################
function set_outclass() {
  if [[ -n "${BSC_OUTCLASS-}" ]]; then
    outclass=/auto-ecearth3/outclass/${BSC_OUTCLASS}
  elif [[ -n "${CMIP6_OUTCLASS-}" ]]; then
    outclass=ctrl/output-control-files/cmip6/${CMIP6_OUTCLASS}
    #if the outclass isn't found on the expected path, create links to the real path on the expected one
    if [[ ! -d "${PROJDIR}/sources/runtime/classic/${outclass}" ]]; then
      cd ${PROJDIR}/sources/runtime/classic/ctrl
      mkdir output-control-files/
      cd -
      cd ${PROJDIR}/sources/runtime/classic/ctrl/output-control-files/
      ln -s ../cmip6-output-control-files-pextra/ cmip6-output-control-files-pextra
      cd -
      cd ${PROJDIR}/sources/runtime/classic/ctrl/output-control-files/
      ln -s ../cmip6-output-control-files/ cmip6
      cd -
    fi
  elif [[ -z "${BSC_OUTCLASS-}" ]] && [[ -z "${CMIP6_OUTCLASS-}" ]]; then
    outclass=ctrl
  fi
}

#####################################################################################################################
# Globals: PROJDIR, EXPID, ROOTDIR
#
# Arguments:
#   None
# Returns:
#   None
# Purpose: invoke the config validator, in order to check the correctness of several settings defined in the proj.conf
#
#####################################################################################################################
function config_validator() {
  set +xuve
  module load Python/3.7.3-foss-2015a
  echo "running Config Validator (You can check the result in the .out log file)"
  python3 $PROJDIR/plugins/config_validator/main.py $EXPID $ROOTDIR/conf $PROJDIR
  if [ $? != 0 ]; then
    get_out=true
  fi
  set -xuve
}

#####################################################################################################################
# Globals: PROJDIR, HPCARCH, SCRATCH path, Exp name, member (Optional), run_start_date (Optional)
#
# Arguments:
#   None
# Returns:
#   None
# Purpose: Runs ec-config tool for EC-Earth3 for a given architecture and path and other config data
#
#####################################################################################################################
function run_ecconfig() {

  #load the parameters
  local proj_path=$1
  local hpc_architecture=$2
  local outclass=$3

  cd ${proj_path}/sources/runtime/autosubmit

  # if the files are not removed ec-conf failed in case of change the account
  for file_name in ../classic/ctrl/tm5-config-run.rc ece-*.sh; do
    rm -f $file_name
  done

  #check loaded parameters
  local get_out=false
  if [[ -z ${proj_path} ]]; then
    echo "proj_path is empty"
    get_out="true"
  fi
  if [[ -z ${hpc_architecture} ]]; then
    echo "hpc_architecture is empty"
    get_out="true"
  fi
  if [[ -z ${outclass} ]]; then
    echo "outclass is not defined"
    get_out="true"
  fi

  if [[ "${get_out}" == "true" ]]; then exit 1; fi

  cd ${proj_path}/sources/runtime/autosubmit
  ln -sf ../classic/platform
  #call the right function based on the correct path to the platform
  . ${proj_path}/platforms/${hpc_architecture}/ecconf.sh

  # Python 2.7 is requiered by ecconfig
  set +xuve
  module load Python/2.7.9-foss-2015a
  set -xuve
  ecconfig ${proj_path} ${outclass}

  #give permissions to generated files
  chmod g+w ${proj_path}/sources/runtime/autosubmit/ece-*.sh

  #check return value of the invocation
  if [ $? != 0 ]; then
    exit 1
  fi

}

#####################################################################################################################
# Globals:
#
# Arguments:
#   None
# Returns:
#   None
# Purpose: check that the value of the cmorization realization index is correct
#
#####################################################################################################################
function check_cmor_realization_index() {
  for current_index in ${CMOR_REALIZATION_INDEX[@]}; do
    typeset -i current_index=${current_index}
    if [[ ${current_index} -eq 0 ]]; then
      echo "You defined your realization index as 0 when it should start at 1. Exiting"
      exit 1
    fi
  done
}

#####################################################################################################################
# Globals: ROOTDIR, EXPID, ROOTDIR, EXPID
#
# Arguments:
#   None
# Returns:
#   None
# Purpose: check the member realization coherency with the one defined in the CMOR_REALIZATION_INDEX variable in proj.conf
#
#####################################################################################################################
function check_member_realization_coherency() {
  nb_members=$(grep "MEMBERS = " ${ROOTDIR}/conf/expdef_${EXPID}.conf | cut -f2 -d"=" | wc -w)
  nb_cmor_realization_index=$(grep "CMOR_REALIZATION_INDEX =" ${ROOTDIR}/conf/proj_${EXPID}.conf | cut -f2 -d"=" | wc -w)
  if [[ ${nb_cmor_realization_index} != 0 ]] && [[ "${nb_members}" != "${nb_cmor_realization_index}" ]]; then
    echo "Number of members (${nb_members}) is different from the number of cmor_realization_indexes (${nb_cmor_realization_index}). Check your proj. Exiting."
    exit 1
  fi
}

#####################################################################################################################
# Globals: CMOR_ADD_STARTDATE, CMOR_EXP, CMOR_EXP_CUSTOM, EXPID
#
# Arguments:
#   None
# Returns:
#   None
# Purpose: Add start dates in CMOR CMIP6_CV.json
#
#####################################################################################################################
function add_cmor_startdates(){
  #Update CMOR_tables
  if [[ ${CMOR_EXP_CUSTOM} == "TRUE" ]]; then
    for START_date in $( cat /esarchive/autosubmit/${EXPID}/conf/expdef_${EXPID}.conf | grep "DATELIST =" | grep -v "#" | cut -f2 -d"=");do
      python ${PROJDIR}/plugins/cmor_pythonsetup.py --projdir $PROJDIR --template_name ecearth3 --expid $EXPID --cmor_exp $CMOR_EXP --cmor_add_startdate $CMOR_ADD_STARTDATE --startdate $START_date
    done
  fi
}

######################################################
#
# MAIN
#
######################################################

if [[ "${DEBUG_MODE-}" == "FALSE" ]]; then

  #
  # Copy Model Sources
  #

  get_out="false"
  cd ${PROJDIR}/sources/runtime/autosubmit
  config_validator
  check_cmor_realization_index
  check_member_realization_coherency
  add_cmor_startdates

  #
  # Create the /esarchive/exp/ecearth/$expid folder once at the beginning to avoid race conditions leading to permissions issues
  #

  mkdir_esarchive /esarchive/exp/${MODEL}/${EXPID}

  #
  # Run ec-conf
  #

  set_outclass

  run_ecconfig ${PROJDIR} ${HPCARCH} ${outclass} ${PRECOMPILED_VERSION}

  echo "common.localsetup Done"

  if [[ "${get_out}" == "true" ]]; then 
    echo "ERROR: The config checker detected errors in your configurations. Please, see the job standard output (.out log) for more details" >& 2
    exit 1
  fi

fi

###################
# Autosubmit tailer
###################
set -xuve
echo $(date +%s) >> ${job_name_ptrn}_STAT
touch ${job_name_ptrn}_COMPLETED
exit 0

