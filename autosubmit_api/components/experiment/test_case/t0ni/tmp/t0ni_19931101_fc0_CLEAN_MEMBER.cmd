#!/bin/bash

###############################################################################
#                   CLEAN_MEMBER t0ni EXPERIMENT
###############################################################################
###################
# Autosubmit header
###################
set -xuve
job_name_ptrn='/gpfs/scratch/bsc32/bsc32627/t0ni/LOG_t0ni/t0ni_19931101_fc0_CLEAN_MEMBER'
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
CURRENT_ARCH=transfer_node
HPCPROJ=bsc32
HPCUSER=bsc32627
HPCHOST=mn1.bsc.es
CHUNK=1
EXPID=t0ni
JOBNAME=t0ni_19931101_fc0_CLEAN_MEMBER
ROOTDIR=/gpfs/scratch/bsc32/bsc32627/t0ni
CMORIZATION=TRUE
LOGDIR=$ROOTDIR/LOG_$EXPID
PROJDEST=auto-ecearth3
PROJDIR=$ROOTDIR/$PROJDEST
SCRATCH_DIR=/gpfs/scratch
ECE3_POSTPROC=FALSE
MODEL=ecearth
USE_DT_COMMANDS=TRUE
[[ "FALSE" == TRUE || "${CURRENT_ARCH}" == "${HPCARCH}" ]] && USE_INTERMEDIATE_STORAGE=TRUE || USE_INTERMEDIATE_STORAGE=FALSE
[[ "FALSE" == TRUE || "${CURRENT_ARCH}" == "${HPCARCH}" ]] && IS_TRANSFER=FALSE || IS_TRANSFER=TRUE

[[ "FALSE" == TRUE ]] && DEBUG_MODE=TRUE || DEBUG_MODE=FALSE

[[ "FALSE" == TRUE ]] && SAVE_RUNTIME=TRUE || SAVE_RUNTIME=FALSE
[[ "FALSE" == TRUE ]] && SAVE_INIDATA=TRUE || SAVE_INIDATA=FALSE

export ${HPCPROJ}

START_date=19931101
MEMBER=fc0
[[ "FALSE" == TRUE ]] && OSM=TRUE || OSM=FALSE
[[ "FALSE" == TRUE ]] && LPJG=TRUE || LPJG=FALSE

. ${PROJDIR}/plugins/utils.sh
. ${PROJDIR}/platforms/${CURRENT_ARCH}/configure.sh
. ${PROJDIR}/platforms/${CURRENT_ARCH}/filesystem.sh

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
function clean_member_prepare_logs() {
  cd ${LOGDIR}
  logfiles_ptrn="${EXPID}_${START_date}_${MEMBER}_"
  ls -1 *${logfiles_ptrn}* | xargs tar -cvf ../$logs_tarfile
}

#####################################################################################################################
# Globals:
# RUN_dir,  ECE3_POSTPROC, LPJG
# $PATHOUT
# Arguments:
#   None
# Returns:
#   None
# Purpose: remove files that will not needed anymore for the re-run the experiments and with the idea of
# reducing the size of the resulting tar
#####################################################################################################################
function cleanup_runtime() {

  cd ${RUN_dir}/

  # for lpjg experiments
  # remove large LPJG inidata files
  if [[ "${LPJG-}" == "TRUE" ]]; then
    echo "We are now removing large LPJG ndep and landuse files"
    rm -f ${RUN_dir}/{ndep,landuse}/*
  fi

  #before tarring the runtime directory, we remove all the post folder from ece3-postproc in case it exists
  if [[ -d ${RUN_dir}/ece3post ]]; then
    rm -rf ${RUN_dir}/ece3post/post
  fi

  # for standard experiments
  echo "We are now removing output, save_ic and LPJG run folders"
  rm -rf ${RUN_dir}/{save_ic,outputs}/*
  # remove the run1 - runn folders
  ls | grep -P "^run*[0-9]$" | xargs -d"\n" rm -rf
}
#####################################################################################################################
# Globals:
# RUN_dir,  PATH_FLAGS, CHUNK, START_date, MEMBER, TEMPLATE_NAME, LPJG, OSM, LPJG_SAVE_RESTART, ECE3_POSTPROC
# $PATHOUT
# Arguments:
#   None
# Returns:
#   None
# Purpose: compress and move the runtime for the member and then delete the directory to free up space
#####################################################################################################################
function save_runtime() {
  echo "We are now storing ${RUN_dir}"
  cd ${ROOTDIR}/${START_date}/${MEMBER}/runtime

  runtime_tarfile=runtime_${EXPID}_${START_date}_${MEMBER}.tar
  tar -cvf ../${runtime_tarfile} $(ls | grep -v output)
  cd ${ROOTDIR}/${START_date}/${MEMBER}
  [[ ! -f ${runtime_tarfile}.gz ]] && gzip -9 ${runtime_tarfile}
  local pathout_runtime="${PATHOUT}/runtime/"
  move_files ${runtime_tarfile}.gz ${pathout_runtime} ${IS_TRANSFER}
}

#####################################################################################################################
# Globals:
# ROOTDIR, START_date, MEMBER, IS_TRANSFER, PATHOUT
# Arguments:
#   None
# Returns:
#   None
# Purpose: check if some file in the inidata folder has been modified or some link points to a different file than the ones after INI job and in that case, save the inidata folder
#####################################################################################################################
function check_save_inidata() {
  echo "Generating checksum for the inidata folder to compare with the one in the INI job"
  cd ${ROOTDIR}/${START_date}/${MEMBER}
  inidata_checksum_generate clean_member
  diff_found=FALSE
  if [[ "$(cmp clean_member_tmpl_files.txt ini_tmpl_files.txt)" != "" ]]; then
    echo "Differences found in the files, printing them now:"
    echo "$(diff -u clean_member_tmpl_files.txt ini_tmpl_files.txt)"
    diff_found=TRUE
  fi
  if [[ "$(cmp clean_member_tmpl_links.txt ini_tmpl_links.txt)" != "" ]]; then
    echo "Differences found in the links paths, printing them now:"
    echo "$(diff -u clean_member_tmpl_links.txt ini_tmpl_links.txt)"
    diff_found=TRUE
  fi
  if [[ "$diff_found" == "TRUE" ]]; then
    if [[ "$SAVE_INIDATA" == "TRUE" ]]; then
      echo "Differences found in the directory, saving inidata requested, proceeding to it."
      inidata_tarfile=inidata_${EXPID}_${START_date}_${MEMBER}.tar
      tar -cvf ${inidata_tarfile} inidata/
      [[ ! -f ${inidata_tarfile}.gz ]] && gzip -9 ${inidata_tarfile}
      local pathout_inidata="${PATHOUT}/inidata/"
      move_files ${inidata_tarfile}.gz ${pathout_inidata} ${IS_TRANSFER}
    else
      echo "There are differences found but save inidata is not requested, not saving it."
    fi
  else
    echo "No differences in the inidata folder found, inidata won't be saved."
  fi
}

#####################################################################################################################
# Globals:
# RUN_dir,  PATH_FLAGS, CHUNK, START_date, MEMBER, TEMPLATE_NAME, LPJG, OSM, LPJG_SAVE_RESTART
# Arguments:
#   None
# Returns:
#   None
# Purpose: removal of the inidata folder
#####################################################################################################################
function remove_inidata() {
  echo "We are now removing ${INIPATH}"
  rm -rf ${INIPATH}
  touch dir_${EXPID}_${START_date}_${MEMBER}_REMOVED
  touch exp_${EXPID}_${START_date}_${MEMBER}_READY

  echo "We are now removing the tmp folder"
  cd ${ROOTDIR}/${START_date}/${MEMBER}
  rm -rf tmp
}

#####################################################################################################################
# Globals:
# RUN_dir,  CHUNK, START_date, MEMBER, LPJG, OSM, PATHOUT, CURRENT_ARCH
# Arguments:
#   None
# Returns:
#   None
# Purpose: transfer outputs for the OSM/LPJG experiments types
#####################################################################################################################
function move_osm_files() {

  local PATHOUT_OUT="${PATHOUT}/${START_date}/${MEMBER}/outputs"
  local OSM_PATH=${RUN_dir}/output/osm

  # move OSM special output to projects folder before tarring runtime folder
  [[ "${IS_TRANSFER-}" == TRUE ]] && OSM_PATH=${RUN_dir}/output/osm/ || OSM_PATH=${RUN_dir}/output/osm

  if [[ "${OSM-}" == "TRUE" ]]; then
    move_files "${OSM_PATH}" ${PATHOUT_OUT} ${IS_TRANSFER}
  fi

}

#####################################################################################################################
# Globals:
# RUN_dir,  PATH_FLAGS, CHUNK, START_date, MEMBER, TEMPLATE_NAME, LPJG, OSM, LPJG_SAVE_RESTART
# Arguments:
#   None
# Returns:
#   None
# Purpose: prepara the paths for the clean member job
#####################################################################################################################
function setup_paths_clean_member() {

  setup_paths_transfer_${CURRENT_ARCH}

  RUN_dir=${ROOTDIR}/${START_date}/${MEMBER}/runtime
  INIPATH=${ROOTDIR}/${START_date}/${MEMBER}/inidata
  #
  # Tail of the experiment
  #
  if [[ ! -d ${PATHOUT} ]]; then
    if [[ "$USE_INTERMEDIATE_STORAGE" == "TRUE" ]]; then
      mkdir_intermediate_storage ${PATHOUT}
    else
      mkdir -p ${PATHOUT}
    fi
  fi
}

##########
## MAIN ##
##########

if [[ "${DEBUG_MODE-}" == "FALSE" ]]; then
  # prepare running environment
  load_platform_environment
  # configure relevant paths
  setup_paths_clean_member
  #OSM/LPGJ part
  if [[ "${OSM-}" == "TRUE" ]] || [[ "${LPJG-}" == "TRUE" ]]; then
    move_osm_files
    # restore paths for the transfer of the runtime, since CLEAN+TRANSFER option sets out different target folders
  fi
  # remove garbage before tarring the runtime to save space
  cleanup_runtime
  # compress and remove runtime
  #save runtime if user requested it
  if [[ "$SAVE_RUNTIME" == "TRUE" ]]; then
    save_runtime
    echo "Now cleaning runtime directory."
  else
    echo "Not storing runtime since it is not requested, cleaning it directly."
    cd ${ROOTDIR}/${START_date}/${MEMBER}  #move to the directory expected by remove_inidata (done in save_runtime previously)
  fi
  #always clean up rundir directory for member
  rm -rf ${RUN_dir}
  # check for inidata changes during the run and save them in that case if requested
  check_save_inidata
  # remove inidata
  remove_inidata
fi

###################
# Autosubmit tailer
###################
set -xuve
echo $(date +%s) >> ${job_name_ptrn}_STAT
touch ${job_name_ptrn}_COMPLETED
exit 0

