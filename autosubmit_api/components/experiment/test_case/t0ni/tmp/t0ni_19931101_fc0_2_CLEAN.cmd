#!/bin/bash

###############################################################################
#                   CLEAN t0ni EXPERIMENT
###############################################################################
###################
# Autosubmit header
###################
set -xuve
job_name_ptrn='/gpfs/scratch/bsc32/bsc32627/t0ni/LOG_t0ni/t0ni_19931101_fc0_2_CLEAN'
echo $(date +%s) > ${job_name_ptrn}_STAT

###################
# Autosubmit job
###################

#!/usr/bin/env bash
set -xuve

########################################################################################################################
# this job not only removes files in order to free space, but also is in charge of saving all output files,
# logs and restarts to the HPC's permanent storage.
# It prepares and saves restart files.
# It saves original and cmorized outputs.
# It also does some nudging processing.
# It uses cleaning.sh, atmospheric_nudging.sh among other files plugins
# Author: J.R.Berlin (based on existing code)
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
JOBNAME=t0ni_19931101_fc0_2_CLEAN
ROOTDIR=/gpfs/scratch/bsc32/bsc32627/t0ni
TEMPLATE_NAME=ecearth3
MODEL=ecearth
PROJDEST=auto-ecearth3
RERUN=FALSE
PROJDIR=$ROOTDIR/$PROJDEST
LOGDIR=$ROOTDIR/LOG_$EXPID
CMORIZATION=TRUE
ECE3_POSTPROC=FALSE
SCRATCH_DIR=/gpfs/scratch
START_date=19931101
START_date_1=19931031
MEMBER=fc0
CMOR_MODEL_ID=EC-EARTH-AOGCM
CMOR_EXP=piControl
CMOR_ACTIVITY_ID=CMIP
CMOR_REALIZATION_INDEX=""
DTHOST=
DT_HOST=
DT_USER=
USE_DT_COMMANDS=TRUE
[[ "FALSE" == TRUE ]] && USE_INTERMEDIATE_STORAGE=TRUE || USE_INTERMEDIATE_STORAGE=FALSE
[[ "FALSE" == TRUE ]] && IS_TRANSFER=FALSE || IS_TRANSFER=TRUE
[[ "FALSE" == TRUE ]] && SAVE_RESTARTS=TRUE || SAVE_RESTARTS=FALSE

# components
IFS_resolution=T511L91
nem_grid=ORCA025L75
NEMO_RES=ORCA025L75
PISCES=FALSE
TEMPLATE_NAME=ecearth3
[[ "FALSE" == TRUE ]] && LPJG=TRUE || LPJG=FALSE
[[ "FALSE" == TRUE ]] && OSM=TRUE || OSM=FALSE
[[ "FALSE" == TRUE ]] && TM5=TRUE || TM5=FALSE

export HPCPROJ
# get the mkdir function of the platform
. ${PROJDIR}/platforms/${CURRENT_ARCH}/configure.sh

#set environment % architecture definitions
load_platform_environment

#
# Chunk Management
#
CHUNK=2
Chunk_start_date=19931201
Chunk_end_date=19931231
Chunk_first=FALSE
Chunk_last=TRUE
RUN_months=1
CHUNKSIZE=1
CHUNKSIZEUNIT=month
numchunks=2

# set the mask for padding the chunk number to three digits
chunk_zero_padded=$(printf "%03d\n" ${CHUNK})

# In months
RUN_months=1
# In days
RUN_days=31
# In hours
RUN_hours=$((RUN_days * 24))

#
# Nudging management
#
ATM_NUDGING=FALSE
ATM_refnud=
OCEAN_STORERST=FALSE
NEMO_RES=ORCA025L75
PISCES=FALSE

#
# Output management
#
[[ "FALSE" == TRUE ]] && SAVEMMA=TRUE || SAVEMMA=FALSE
[[ "FALSE" == TRUE ]] && SAVEDDA=TRUE || SAVEDDA=FALSE
[[ "FALSE" == TRUE ]] && SAVEMMO=TRUE || SAVEMMO=FALSE

[[ "FALSE" == TRUE ]] && LPJG_SAVE_ICMCL=TRUE || LPJG_SAVE_ICMCL=FALSE
[[ "TRUE" == FALSE ]] && LPJG_SAVE_RESTART=FALSE || LPJG_SAVE_RESTART=TRUE

[[ "FALSE" == TRUE ]] && DEBUG_MODE=TRUE || DEBUG_MODE=FALSE

GZIP=-6

# Check if DT commands are available in case that CLEAN is done in other platform different that DT nodes
exist_dtrsync=$(echo $(command -v dtrsync))
if [[ "${USE_INTERMEDIATE_STORAGE-}" == "TRUE" || -z "${exist_dtrsync-}" ]]; then
  USE_DT_COMMANDS=FALSE
fi

#
# Common functions
#






#####################################################################################################################
# Globals:
# RUN_dir, CHUNK, EXPID, START_date, MEMBER, Chunk_start_date, Chunk_end_date
# PATHOUT_RES, OCEAN_STORERST, IC_DIR, NEMO_RES, PATH_IC
# Arguments:
#   None
# Returns:
#   None
# Purpose: Save Ocean restart files
#
#####################################################################################################################
function save_oce_ics() {

  PATH_IC=${IC_DIR} # path for initial conditions (ic)
  # ocean
  #TODO: if file doesnt exist move_files will clearly throw an exception
  file="${EXPID}_${START_date}_${MEMBER}_${chunk_zero_padded}_${Chunk_start_date}-${Chunk_end_date}_restart.nc.gz"
  mkdir_intermediate_storage ${PATH_IC}/ocean/${NEMO_RES}/${EXPID} Earth
  move_files ${file} ${PATH_IC}/ocean/${NEMO_RES}/${EXPID} ${IS_TRANSFER}
  # ice
  file="${EXPID}_${START_date}_${MEMBER}_${chunk_zero_padded}_${Chunk_start_date}-${Chunk_end_date}_restart_ice.nc.gz"
  mkdir_intermediate_storage ${PATH_IC}/ice/$(echo ${NEMO_RES} | cut -d 'L' -f 1)_LIM3/${EXPID} Earth
  move_files ${file} ${PATH_IC}/ice/$(echo ${NEMO_RES} | cut -d 'L' -f 1)_LIM3/${EXPID} ${IS_TRANSFER}
  # PISCES
  if [[ ${PISCES} != '' ]] && [[ ${PISCES} == 'TRUE' ]]; then
    file="${EXPID}_${MEMBER}_${Chunk_end_date}_restart_trc.nc.gz"
    mkdir_intermediate_storage ${PATH_IC}/pisces/${NEMO_RES}/${EXPID} Earth
    move_files ${file} ${PATH_IC}/pisces/${NEMO_RES}/${EXPID} ${IS_TRANSFER}
  fi
}

#####################################################################################################################
# Globals:
# LOGDIR,  EXPID, START_date, MEMBER, chunk_zero_padded, Chunk_start_date, Chunk_end_date
# Arguments:
#   None
# Returns:
#   None
# Purpose: Prepare mml tar file compressed for transfer
#####################################################################################################################
function generate_mml_output() {
  tarfile="MML_${EXPID}_${START_date}_${MEMBER}_${chunk_zero_padded}_${Chunk_start_date}-${Chunk_end_date}.tar"
  # Copying the monthly means
  ls -1 MML_${EXPID}_*.gz | xargs tar --remove-files -cvf ../${tarfile}
}

#####################################################################################################################
# Globals:
# LOGDIR,  EXPID, START_date, MEMBER, chunk_zero_padded, Chunk_start_date, Chunk_end_date
# Arguments:
#   None
# Returns:
#   None
# Purpose: Prepare mma tar file compressed for transfer
#####################################################################################################################
function generate_mma_output() {
  tarfile="MMA_${EXPID}_${START_date}_${MEMBER}_${chunk_zero_padded}_${Chunk_start_date}-${Chunk_end_date}.tar"
  # Copying the monthly means
  ls -1 MMA_${EXPID}_*.nc.gz | xargs tar --remove-files -cvf ../${tarfile}
}

#####################################################################################################################
# Globals: EXPID, RUN_dir, CHUNK, IS_TRANSFER
# Chunk_start_date, MEMBER, Chunk_end_date
# PATHOUT_OUT
# Arguments:
#   None
# Returns:
#   None
# Purpose: Transfer atmosphere monthly mean (MMA) output files
#####################################################################################################################
function save_mma() {
  generate_mma_output && returncode=$? || returncode=$?
  if [[ ${returncode} -eq 0 ]]; then
    cd ..
    move_files ${tarfile} ${PATHOUT_OUT} ${IS_TRANSFER}
    cd -
  fi
}

#####################################################################################################################
# Globals: EXPID, RUN_dir, CHUNK, IS_TRANSFER , START_date, MEMBER
# Chunk_start_date, Chunk_end_date
# PATHOUT_OUT
# Arguments:
#   None
# Returns:
#   None
# Purpose: Transfer OSM (offline surface model) monthly mean (MML) output files
#####################################################################################################################
function save_mml() {
  generate_mml_output && returncode=$? || returncode=$?
  if [[ ${returncode} -eq 0 ]]; then
    cd ..
    move_files ${tarfile} ${PATHOUT_OUT} ${IS_TRANSFER}
    cd -
  fi
}

#####################################################################################################################
# Globals:
# LOGDIR,  EXPID, START_date, MEMBER, Chunk_start_date, Chunk_end_date, chunk_zero_padded
# Arguments:
#   None
# Returns:
#   None
# Purpose: Prepare dda tar file compressed for transfer
#####################################################################################################################
function generate_dda_output() {
  tarfile="DDA_${EXPID}_${START_date}_${MEMBER}_${chunk_zero_padded}_${Chunk_start_date}-${Chunk_end_date}.tar.gz"
  echo "moving tar file "
  ls -1 ICM??${EXPID}+??????.grb | xargs tar --remove-files -zcvf ${tarfile}
}

#####################################################################################################################
# Globals: None
# Arguments:
#   None
# Returns:
#   None
# Purpose: Transfer atmosphere daily data (GRIB files)
#####################################################################################################################
function save_dda() {
  local icmfiles_path=$1
  cd ${icmfiles_path}
  generate_dda_output && returncode=$? || returncode=$?
  if [[ ${returncode} -eq 0 ]]; then
    move_files ${tarfile} ${PATHOUT_OUT} ${IS_TRANSFER}
  fi
}

#####################################################################################################################
# Globals: CHUNK, PATHOUT_OUT, TEMPLATE_NAME, IS_TRANSFER, output_dir_osm, output_dir_atm
# Arguments:
#   None
# Returns:
#   None
# Purpose: Transfer ICMCL files, only generated when IFS/OSM is coupled to LPJG, depending of the type of template
# the source path will be different
#####################################################################################################################
function save_icmcl() {

  [[ "${TEMPLATE_NAME-}" == "lsm" ]] && icmcl_path=${output_dir_osm} || icmcl_path=${output_dir_atm}
  [[ "${IS_TRANSFER-}" == "TRUE" ]] && chunkpath=${PATHOUT_OUT}/icmcl || chunkpath=${PATHOUT_OUT}/osm/icmcl

  mkdir_intermediate_storage ${chunkpath} Earth

  declare -a arrFiles
  shopt -s nullglob
  arrFiles=(${icmcl_path}/icmcl*.grb)
  # check if there is any file
  if [[ ${#arrFiles[@]} -gt 0 ]]; then
    items=$(printf "%s " "${arrFiles[@]}")
    move_files "${items}" ${chunkpath} ${IS_TRANSFER}
  fi
}

#####################################################################################################################
# Globals: EXPID, RUN_dir, chunk_zero_padded, Chunk_start_date, MEMBER, Chunk_end_date, PATHOUT_OUT,
#          SAVEDDA, ECversion, PATHOUT_OUT, SAVEDDA
# Arguments:
#   None
# Returns:
#   None
# purpose: Save Ocean output files
#####################################################################################################################
function create_mmo() {
  if [[ -z ${CMORIZATION-} ]] || [[ ${CMORIZATION} == 'FALSE' ]] || [[ ${SAVEMMO} == 'TRUE' ]]; then
    tarfile="MMO_${EXPID}_${START_date}_${MEMBER}_${chunk_zero_padded}_${Chunk_start_date}-${Chunk_end_date}.tar"
    # Copying the means available
    # TODO: if file doesnt exist xargs will clearly throw an exception
    ls -1 *${EXPID}_*_${Chunk_start_date}_${Chunk_end_date}*.nc | xargs tar -cvf ../${tarfile}
    cd ..
    move_files ${tarfile} ${PATHOUT_OUT} ${IS_TRANSFER}
    cd -
  fi
}

#####################################################################################################################
# Globals: PATH_FLAGS, RUN_months, EXPID, SAVEDDA, ATM_REDUCED_OUTPUT,
# ATM_REDUCED_DAILY, ATM_SH_CODES, ATM_SH_LEVELS, ATM_GG_CODES, ATM_GG_LEVELS
#
# Arguments:
#   None
# Returns:
#   None
# Purpose:
#   The function removes the raw data from the runtime´s output and restart storage folders after the clean process has taken place.
#   for such purpose, a system of flags are created at each of the different stages of the clean, allowing the raw data to be removed
#   only after the clean process completed successfully. this allows the job to be resumed in case of error and deleting the data once the clean
#   has been executed successfully, below is explained in detail such system:

# ${PATH_FLAGS} is a folder located in the runtime where all the flags to manage the CLEAN process will be stored, the concerned flags are
# the following:

# rest_${CHUNK}: check if the clean of all the restarts have taken place for the given chunk, this one will be created if all the restart flags
# corresponding to the type of experiment (Coupled, Nemo only, IFS only or LSM) are present

# out_${CHUNK}: is the same idea as described above...but for the outputs, exactly same criteria as restarts

# resta_${CHUNK} : flag for the atm restarts
# resto_${CHUNK} : flag for the ocean restarts
# restc_${CHUNK} : flag for the coupler restarts ( Oasis )
# restv_${CHUNK} : flag for the LPJG restarts
# restl_${CHUNK} : flag for the OSM restarts

# the files mentioned above are deleted altogether and out_${CHUNK} and rest_${CHUNK} are created, to indicate that the process has been carried out
# correctly later on these are also deleted

# finished_chunk_${CHUNK}: when all outputs (out_${CHUNK}) and restarts (rest_${CHUNK}) have been processed, these flags are deleted and this one is created to indicate that
# the whole process has been completed
#####################################################################################################################
function remove_tail_chunk() {

  cd ${RUN_dir}
  if [[ -e ${PATH_FLAGS}/rest_${CHUNK} && -e ${PATH_FLAGS}/out_${CHUNK} ]]; then

      if [[ -d ${output_dir_atm} ]] ; then
        if [[ $( printf "%03d\n" ${CHUNK}) == 001 ]] ; then
          echo "We are now copying the ICM??${EXPID}+000000 files so they can be used later by CMORATM"
          cp ${RUN_dir}/output/ifs/001/ICM??${EXPID}+000000 ${RUN_dir}
          echo "We are now removing ${output_dir_atm}"
          rm -rf ${output_dir_atm}
          mkdir ${RUN_dir}/output/ifs/001
	  mv ${RUN_dir}/ICM??${EXPID}+000000 ${RUN_dir}/output/ifs/001
        else
          echo "We are now removing ${output_dir_atm}"
          rm -rf ${output_dir_atm}
        fi
      fi

    if [[ -d ${output_dir_oce} ]]; then
      echo "We are now removing ${output_dir_oce}"
      rm -rf ${output_dir_oce}
    fi

    if [[ "${LPJG-}" == "TRUE" ]]; then
      echo "We are now removing ${output_dir_lpjg}"
      rm -rf ${output_dir_lpjg}
    fi

    if [[ "${OSM-}" == "TRUE" ]]; then
      echo "We are now removing ${output_dir_osm}"
      rm -rf ${output_dir_osm}
    fi

    if [[ "${TM5-}" == "TRUE" ]]; then
      echo "We are now removing ${output_dir_tm5}"
      rm -rf ${output_dir_tm5}
    fi

  fi
}

#
# Final condition, before starting next simulation
#

#####################################################################################################################
# Globals:
# PATH_FLAGS, CHUNK
# Arguments:
#   None
# Returns:
#   None
# Purpose: check if all the clean process was carried out correctly, the function checks the existence
# of the flag files and creates finished_chunk_${CHUNK} file to indicate that everything was carried out OK
#
#####################################################################################################################
function check_final_condition() {

  cd ${RUN_dir}
  if [[ ! -e ${PATH_FLAGS}/finished_chunk_${CHUNK} ]]; then

    # LPJG restarts have a different numbering convention than other restarts,
    # so they are NOT moved to LPJG_Restart_$chunk
    # delete restart created by previous chunk, and the one from the last chunk as well
    if [[ ${CHUNK} -gt 1 ]]; then
      rm -rf restart/lpjg/$(printf "%03d\n" $((CHUNK - 1)))
      if [[ "$Chunk_last" == "TRUE" ]]; then
        rm -rf restart/lpjg/$(printf "%03d\n" ${CHUNK})
      fi
    fi

    # Handling of the logs and output traces belongs to previous chunk (if available)
    rm -rf Output_${CHUNK}
    rm -f ${PATH_FLAGS}/rest_${CHUNK} ${PATH_FLAGS}/out_${CHUNK}
    touch ${PATH_FLAGS}/finished_chunk_${CHUNK}

  fi
}

#
# Paths management
#

#####################################################################################################################
# Globals:
# PATHOUT, CURRENT_ARCH, RUN_dir, MEMBER, START_date, PATH_FLAGS, PROJDIR
# Arguments:
#   None
# Returns:
#   None
# Purpose: prepare all globals concerning paths accordingly depending of the type of experiment and
# the current architecture where the job will run, load the needed libraries for the correct execution and
# create the directories needed for the CLEAN process
#####################################################################################################################
function setup_paths() {

  # Depending of the platform, we apply the right strategy
  # setup_paths_transfer
  setup_paths_transfer_${CURRENT_ARCH}

  PATHOUT_OUT="${PATHOUT}/${START_date}/${MEMBER}/outputs"
  PATH_FLAGS=${RUN_dir}/flags

  if [[ ! -d ${PATH_FLAGS} ]]; then
    mkdir -p ${PATH_FLAGS}
  fi

  if ! test_intermediate_storage "-d ${PATHOUT_OUT}"; then
    mkdir_intermediate_storage ${PATHOUT_OUT} Earth
    if ! test_intermediate_storage "-d ${PATHOUT_OUT}"; then
      echo " OMG we have a problem!"
      echo " this directory should exist! ${PATHOUT_OUT}"
      exit
    fi
  fi

  cd ${RUN_dir}

  output_dir_atm=""
  output_dir_oce=""
  output_dir_lpjg=""
  output_dir_osm=""
  output_dir_tm5=""

  # Define paths depending of the type of experiment and some of its features
  if [ "${TEMPLATE_NAME-}" == "ifs3" ] || [ "${TEMPLATE_NAME-}" == "ecearth3" ]; then
    output_dir_atm=${RUN_dir}/output/ifs/$(printf "%03d\n" ${CHUNK})
  fi

  if [ "${TEMPLATE_NAME-}" == "nemo3" ] || [ "${TEMPLATE_NAME-}" == "ecearth3" ]; then
    output_dir_oce=${RUN_dir}/output/nemo/$(printf "%03d\n" ${CHUNK})
  fi

  if [[ "${LPJG-}" == "TRUE" ]]; then
    output_dir_lpjg=${RUN_dir}/output/lpjg/$(printf "%03d\n" ${CHUNK})
  fi

  if [[ "${OSM-}" == "TRUE" ]]; then
    output_dir_osm=${RUN_dir}/output/osm/$(printf "%03d\n" ${CHUNK})
  fi

  if [[ "${TM5-}" == "TRUE" ]]; then
    output_dir_tm5=${RUN_dir}/output/tm5/$(printf "%03d\n" ${CHUNK})
  fi

  if [[ ! -d ${RUN_dir} ]]; then
    exit
  fi

  # load CLEAN/TRANSFER supporting functions
  . ${PROJDIR}/plugins/utils.sh
  . ${PROJDIR}/plugins/transfer.sh

}

#####################################################################################################################
# Globals:
# EXPID,  START_date, MEMBER, CHUNK, Chunk_start_date, Chunk_end_date, PATHOUT_RES, IS_TRANSFER, PATH_FLAGS
# Arguments:
#   None
# Returns:
#   None
# Purpose: tar the restart files and move these files to the specified target folder, depending of the IS_TRANSFER var,
#          these files will be move to the intermediate storage or directly to esarchive ( permanent storage )
#####################################################################################################################
function save_restart() {
  local rst_prefix=$1
  local ec_component=$2
  local uppercase_rst_prefix=$(echo ${rst_prefix} | tr '[:lower:]' '[:upper:]')

  if [[ "${ec_component-}" == "LPJG" ]]; then
    # LPJG restarts for this CHUNK are used in the next CHUNK so we remove the ones from the previous CHUNK
    previous_chunk_start_date=$(date --date "$Chunk_start_date - $CHUNKSIZE $CHUNKSIZEUNIT" +%Y%m%d)
    previous_chunk_end_date=$(date --date "$Chunk_end_date - $CHUNKSIZE $CHUNKSIZEUNIT" +%Y%m%d)
    previous_chunk_zero_padded=$(printf "%03d\n" $((${CHUNK} - 1)) )
    tarfile="${uppercase_rst_prefix}_${EXPID}_${START_date}_${MEMBER}_${previous_chunk_zero_padded}_${previous_chunk_start_date}-${previous_chunk_end_date}.tar.gz"
    if [[ ! -d restart/lpjg/${previous_chunk_zero_padded} && "${Chunk_first}" != "TRUE" ]]; then
      echo "restart missing! error!"
      exit 1
    fi
    if [ ${Chunk_first} != "TRUE" ] && [[ "$SAVE_RESTARTS" == "TRUE" ]]; then
      echo "Saving the LPJG restarts"
      tar --remove-files -czvf ${tarfile} restart/lpjg/${previous_chunk_zero_padded}
    else
      echo "Not saving the LPJG restarts"
      rm -rf restart/lpjg/${previous_chunk_zero_padded}
    fi
  else
    tarfile="${uppercase_rst_prefix}_${EXPID}_${START_date}_${MEMBER}_${chunk_zero_padded}_${Chunk_start_date}-${Chunk_end_date}.tar"
    if [[ -d ${ec_component}_Restart_${CHUNK} ]]; then
      if [[ "$SAVE_RESTARTS" == "TRUE" ]]; then
        echo "Saving the ${ec_component} restarts"
        tar --remove-files -cvf ${tarfile} ${ec_component}_Restart_${CHUNK}
      else
        echo "Not saving the ${ec_component} restarts"
        rm -rf ${ec_component}_Restart_${CHUNK}
      fi
    fi
  fi
  if [[ -f ${tarfile} ]]; then
    # test for single files cases
    move_files ${tarfile} ${PATHOUT_RES} ${IS_TRANSFER}
  fi

  touch ${PATH_FLAGS}/${rst_prefix}_${CHUNK}

}

#####################################################################################################################
# Globals:
# CHUNK, RUN_dir, RERUN
# Arguments:
#   None
# Returns:
#   None
# Purpose: main function that moves restarts in case of a re-run
#        ( in case the tar files were generated and generate those that were not )
#####################################################################################################################
#
# Functions for the nudging ( Ocean and Atmosphere )
#

#####################################################################################################################
# Globals:
# ATM_NUDGING, ATM_NUDGING, EXTRA_DIR, IFS_resolution, Chunk_start_date ,start_date_mm, CHUNK
# Arguments:
#   None
# Returns:
#   None
# Purpose: prepares the atmospheric nudging in case the feature is enabled for the given experiment
#####################################################################################################################
#function setup_atm_nudging(){
function clean_atm_nudging() {

  # Atmospheric nuding - Lauriance, Omar
  # Preperation of refence files for Chunk 3
  # Ref: e007, i05g

  cd ${RUN_dir}
  if [[ "${ATM_NUDGING-}" != '' ]] && [[ "${ATM_NUDGING-}" == 'TRUE' ]]; then
    PATHNUDA=${EXTRA_DIR}/nudging/atmos/${IFS_resolution}
    start_date_mm=$(echo ${Chunk_start_date} | cut -c5-6)
    start_date_mm=${start_date_mm#0} # Cut leading '0'
    start_date_yyyy=$(echo ${Chunk_start_date} | cut -c1-4)

    . ${PROJDIR}/plugins/atmospheric_nudging.sh

    if [[ ${CHUNK} -lt $((numchunks - 2)) ]]; then
      clean_atm_nudg_chunk
      # atm_nudg_chunk 2
    fi
  fi
}

#
# Functions for saving the outputs & restarts to permanent storage
#

#####################################################################################################################
# Globals:
# RUN_dir,  PATH_FLAGS, CHUNK, START_date, MEMBER, TEMPLATE_NAME, LPJG, OSM, LPJG_SAVE_RESTART
# Arguments:
#   None
# Returns:
#   None
# Purpose: Main function to save the restarts, depending of the type of template, the handling is carried out in a different way
# a system of flags is in place to allow the job to resume without problems in case an error o problem occurs. these flags are
# deleted at the end of job
#####################################################################################################################
function save_restarts() {

  cd ${RUN_dir}
  if [[ ! -e ${PATH_FLAGS}/rest_${CHUNK} ]]; then

    PATHOUT_RES="${PATHOUT}/${START_date}/${MEMBER}/restarts"
    mkdir_intermediate_storage ${PATHOUT_RES} Earth

    #flags for each type of restart is created in save_restart method, the only exception are the ocean restarts
    # that needs to be done in a different way by invoking the function save_oce_ics

    # use a CASE for template type and we check the existence of flags to be sure we don't process the restarts again

    case "${TEMPLATE_NAME-}" in
    "ecearth3")
      # atmos
      if [[ ! -e ${PATH_FLAGS}/resta_${CHUNK} ]]; then
        save_restart "resta" "IFS"
      fi

      # ocean
      if [[ ! -e ${PATH_FLAGS}/resto_${CHUNK} ]]; then
        save_restart "resto" "NEMO"
        # Generating/Handling ocean & sea-ice initial conditions
        if [[ ${OCEAN_STORERST} != '' ]] && [[ ${OCEAN_STORERST} == 'TRUE' ]]; then
          save_oce_ics
        fi
      fi

      #coupler
      if [[ ! -e ${PATH_FLAGS}/restc_${CHUNK} ]]; then
        save_restart "restc" "OASIS"
      fi
      ;;
    "ifs3")
      # atmos
      if [[ ! -e ${PATH_FLAGS}/resta_${CHUNK} ]]; then
        save_restart "resta" "IFS"
      fi
      ;;
    "nemo3")
      # ocean
      if [[ ! -e ${PATH_FLAGS}/resto_${CHUNK} ]]; then
        save_restart "resto" "NEMO"
        # Generating/Handling ocean & sea-ice initial conditions
        if [[ ${OCEAN_STORERST} != '' ]] && [[ ${OCEAN_STORERST} == 'TRUE' ]]; then
          save_oce_ics
        fi
      fi
      ;;
    "lsm")
      if [[ "${LPJG}" == "TRUE" ]] && [[ "${OSM}" == "TRUE" ]] && [[ ! -e ${PATH_FLAGS}/restc_${CHUNK} ]]; then
        save_restart "restc" "OASIS"
      fi
      ;;
    *)
      echo "CLEAN save restarts - template / model not supported: " + "${TEMPLATE_NAME-}"
      exit 1
      ;;
    esac

    # lpjg - do not save restart if LPJG_SAVE_RESTART == FALSE (recommended for lsm runs or runs which do not end on Jan 1)
    # TODO disable this when running predictions?
    [[ "$LPJG_SAVE_RESTART" == FALSE ]] && [[ "$Chunk_last" == "TRUE" ]] && LPJG_SAVE_RESTART=TRUE
    if [[ "${LPJG}" == "TRUE" ]] && [[ "${LPJG_SAVE_RESTART-}" == "TRUE" ]] && [[ ! -e ${PATH_FLAGS}/restv_${CHUNK} ]]; then
      save_restart "restv" "LPJG"
    fi

    # osm
    if [[ "${OSM}" == "TRUE" ]] && [[ ! -e ${PATH_FLAGS}/restl_${CHUNK} ]]; then
      save_restart "restl" "OSM"
    fi

    # tm5
    if [[ "${TM5}" == "TRUE" ]] && [[ ! -e ${PATH_FLAGS}/restt_${CHUNK} ]]; then
      save_restart "restt" "TM5"
    fi

    # common
    case "${TEMPLATE_NAME-}" in
    "ecearth3")
      if [[ -e ${PATH_FLAGS}/restc_${CHUNK} && -e ${PATH_FLAGS}/resta_${CHUNK} && -e ${PATH_FLAGS}/resto_${CHUNK} ]]; then
        rm -f ${PATH_FLAGS}/restc_${CHUNK} ${PATH_FLAGS}/resta_${CHUNK} ${PATH_FLAGS}/resto_${CHUNK}
        [[ "$LPJG" == "TRUE" ]] && rm -f ${PATH_FLAGS}/restv_${CHUNK}
        [[ "$OSM" == "TRUE" ]] && rm -f ${PATH_FLAGS}/restl_${CHUNK}
        [[ "$TM5" == "TRUE" ]] && rm -f ${PATH_FLAGS}/restt_${CHUNK}
        touch ${PATH_FLAGS}/rest_${CHUNK}
      fi
      ;;
    "ifs3")
      if [[ -e ${PATH_FLAGS}/resta_${CHUNK} ]]; then
        rm -f ${PATH_FLAGS}/resta_${CHUNK}
        [[ "$LPJG" == "TRUE" ]] && rm -f ${PATH_FLAGS}/restv_${CHUNK}
        [[ "$OSM" == "TRUE" ]] && rm -f ${PATH_FLAGS}/restl_${CHUNK}
        [[ "$TM5" == "TRUE" ]] && rm -f ${PATH_FLAGS}/restt_${CHUNK}
        touch ${PATH_FLAGS}/rest_${CHUNK}
      fi
      ;;
    "nemo3")
      if [[ -e ${PATH_FLAGS}/resto_${CHUNK} ]]; then
        rm -f ${PATH_FLAGS}/resto_${CHUNK}
        [[ "$LPJG" == "TRUE" ]] && rm -f ${PATH_FLAGS}/restv_${CHUNK}
        [[ "$OSM" == "TRUE" ]] && rm -f ${PATH_FLAGS}/restl_${CHUNK}
        [[ "$TM5" == "TRUE" ]] && rm -f ${PATH_FLAGS}/restt_${CHUNK}
        touch ${PATH_FLAGS}/rest_${CHUNK}
      fi
      ;;
    "lsm")
      [[ "$LPJG" == "TRUE" ]] && [[ "$OSM" == "TRUE" ]] && rm -f ${PATH_FLAGS}/restc_${CHUNK}
      [[ "$LPJG" == "TRUE" ]] && rm -f ${PATH_FLAGS}/restv_${CHUNK}
      [[ "$OSM" == "TRUE" ]] && rm -f ${PATH_FLAGS}/restl_${CHUNK}
      touch ${PATH_FLAGS}/rest_${CHUNK}
      ;;
    *)
      echo "CLEAN - template / model not supported: " + "${TEMPLATE_NAME-}"
      exit 1
      ;;
    esac

  fi
}

#####################################################################################################################
# Globals:
# PATHOUT_LOGS, TEMPLATE_NAME, LPJG, OSM, TM5, RUN_dir, EXPID, START_date, MEMBER, CHUNK
# Arguments:
#   None
# Returns:
#   None
# Purpose: the function defines a list of log files to save, separated by spaces, these files will be compressed
# and then moved to the target destination, additionally
# the function will check the existence of Lucia logs and add it to the tar
#####################################################################################################################
function save_logs() {
  # We build the log list incrementally
  PATHOUT_LOGS="${PATHOUT}/logfiles/"
  cd ${RUN_dir}
  chunk_zero_padded=$(printf "%03d\n" ${CHUNK})
  runtime_logdir=log/${chunk_zero_padded}

  if [[ ! -d ${runtime_logdir} ]]; then
    echo "INFO: ${runtime_logdir} doesn't exits"
  else
    tarfile=LOG_${EXPID}_${START_date}_${MEMBER}_${chunk_zero_padded}_${Chunk_start_date}-${Chunk_end_date}.tar.gz
    tar --remove-files -czvf ${tarfile} ${runtime_logdir}
    # move files to the target location
    move_files ${tarfile} ${PATHOUT_LOGS} ${IS_TRANSFER}
  fi
}

#####################################################################################################################
# Globals:
# ECE3_POSTPROC , START_date, PATH_FLAGS, Chunk_end_date, CHUNK, PATHOUT, MEMBER, Chunk_start_date
# Chunk_end_date
# Arguments:
#   None
# Returns:
#   None
# Purpose: tar the ece3 postprocessed files by tarring them and moving to the specified directory, a flag is
# created at the end to indicate that it was successfully achieved
# we might have ece3post output if ECE3_POSTPROC=TRUE or if the job ECE3POST_CCYCLE is enabled
# so for simplicity we check for ece3post folder
#####################################################################################################################
function save_ece3_postproc() {

  if [[ -d ${RUN_dir}/ece3post ]] ; then
    if [[ "${START_date:4:4}" == "0101" && "${Chunk_end_date:4:4}" == "1231" ]]; then
      cd ${RUN_dir}
      if [[ ! -e ${PATH_FLAGS}/ece3post_${CHUNK} ]]; then
        PATHOUT_ECE3POST="${PATHOUT}/${START_date}/${MEMBER}/ece3post"
        mkdir_intermediate_storage ${PATHOUT_ECE3POST} Earth
        tarfile="ECE3POST_${EXPID}_${START_date}_${MEMBER}_${chunk_zero_padded}_${Chunk_start_date}-${Chunk_end_date}.tar.gz"
        tar -czvf ${tarfile} ece3post/diag/
        move_files ${tarfile} ${PATHOUT_ECE3POST} ${IS_TRANSFER}
        touch ${PATH_FLAGS}/ece3post_${CHUNK}
      fi
    fi
  fi
}

#####################################################################################################################
# Globals:
# START_date, PATH_FLAGS, Chunk_end_date, CHUNK, output_dir_atm, LPJG_SAVE_ICMCL, Chunk_start_date
# Arguments:
#   None
# Returns:
#   None
# Purpose: save the outputs of IFS3 depending of SAVEMMA and SAVEDDA proj.conf settings, and also save the icmcl
# by default these are disabled since the standard outputs for all experiments are the cmorized files
# the function creates a flag to indicate that the files were created and the transferred to the target location successfully(outa_${CHUNK})
# later this flag is checked in the save_outputs function
#####################################################################################################################
function save_outputs_atm() {

  if [[ -d ${output_dir_atm} ]]; then
    cd ${output_dir_atm}
    if [[ ! -e ${PATH_FLAGS}/out_${CHUNK} ]]; then
      if [[ ! -e ${PATH_FLAGS}/outa_${CHUNK} ]]; then
        [[ ${SAVEMMA} == 'TRUE' ]] && save_mma
        [[ ${SAVEDDA} == 'TRUE' ]] && save_dda ${output_dir_atm}
        [[ "${LPJG_SAVE_ICMCL}" == "TRUE" ]] && [[ "${Chunk_start_date:4:4}" == "0101" ]] && [[ "${Chunk_end_date:4:4}" == "1231" ]] && save_icmcl
        touch ${PATH_FLAGS}/outa_${CHUNK}
      fi
    fi
  fi

}

#####################################################################################################################
# Globals:
# output_dir_oce, PATH_FLAGS, CHUNK
# Arguments:
#   None
# Returns:
#   None
# Purpose: saves the output (MMO) for the ocean component ( NEMO ) in case the proj.conf setting is enabled,
# by default this is disabled since the standard outputs for all experiments are the cmorized files
# the function creates a flag to indicate that the files were created and the transferred to the target location successfully(outo_${CHUNK})
# later this flag is checked in the save_outputs function
#####################################################################################################################
function save_outputs_oce() {

  if [[ -d ${output_dir_oce} ]]; then
    cd ${output_dir_oce}
    if [[ ! -e ${PATH_FLAGS}/outo_${CHUNK} ]]; then
      ECversion='ecearth3'
      create_mmo
      touch ${PATH_FLAGS}/outo_${CHUNK}
    fi
  fi

}

#####################################################################################################################
# Globals:
# output_dir_lpjg, CHUNK, EXPID, START_date, MEMBER, Chunk_start_date, Chunk_end_date, PATH_FLAGS
# Arguments:
#   None
# Returns:
#   None
# Purpose: saves the output (MMV) for the LPJG component ( veg ) in case the proj.conf setting is enabled,
# by default this is disabled, if enabled the files are tarred, the function creates a flag to indicate
# that the files were created and the transferred to the target location successfully(outv_${CHUNK})
# later this flag is checked in the save_outputs function
#####################################################################################################################
function save_outputs_lpjg() {
  if [[ -d ${output_dir_lpjg} ]]; then
    cd ${output_dir_lpjg}
    if [[ ! -e ${PATH_FLAGS}/outv_${CHUNK} ]]; then
      tarfile="MMV_${EXPID}_${START_date}_${MEMBER}_${chunk_zero_padded}_${Chunk_start_date}-${Chunk_end_date}.tar"
      tar -cvf ../${tarfile} .
      cd ..
      move_files ${tarfile} ${PATHOUT_OUT} ${IS_TRANSFER}
      cd ${output_dir_lpjg}
      touch ${PATH_FLAGS}/outv_${CHUNK}
    fi
  fi
}

#####################################################################################################################
# Globals:
# SAVEMMA SAVEDDA, PATH_FLAGS, CHUNK, PATH_FLAGS
# Arguments:
#   None
# Returns:
#   None
# Purpose:saves the output for the OSM component in case the proj.conf setting is enabled,
# by default this is disabled, if enabled the outputs are generated via save_mml and save_dda
# the function creates a flag to indicate that the files were created and the transferred to the target location successfully (outl_${CHUNK})
# later this flag is checked in the save_outputs function
#####################################################################################################################
function save_outputs_osm() {

  if [[ -d ${output_dir_osm} ]]; then
    cd ${output_dir_osm}
    if [[ ! -e ${PATH_FLAGS}/outl_${CHUNK} ]]; then
      [[ ${SAVEMMA} == 'TRUE' ]] && save_mml
      [[ ${SAVEDDA} == 'TRUE' ]] && save_dda ${output_dir_osm}
      save_icmcl
      touch ${PATH_FLAGS}/outl_${CHUNK}
    fi
  fi
}

#####################################################################################################################
# Globals:
# output_dir_tm5, CHUNK, EXPID, START_date, MEMBER, Chunk_start_date, Chunk_end_date, PATH_FLAGS
# Arguments:
#   None
# Returns:
#   None
# Purpose: saves the output for the TM5 component in case the proj.conf setting is enabled,
# by default this is disabled, if enabled the outputs are tarred and moved to the target output folder
# the function creates a flag to indicate that the files were created and the transferred to the target location successfully (outt_${CHUNK})
# later this flag is checked in the save_outputs function
#####################################################################################################################
function save_outputs_tm5() {

  if [[ -d ${output_dir_tm5} ]]; then
    cd ${output_dir_tm5}
    if [[ ! -e ${PATH_FLAGS}/outt_${CHUNK} ]]; then
      tarfile="MMT_${EXPID}_${START_date}_${MEMBER}_${chunk_zero_padded}_${Chunk_start_date}-${Chunk_end_date}.tar"
      tar -cvf ../${tarfile} .
      cd ..
      move_files ${tarfile} ${PATHOUT_OUT} ${IS_TRANSFER}
      cd ${output_dir_tm5}
      touch ${PATH_FLAGS}/outt_${CHUNK}
    fi
  fi

}

#####################################################################################################################
# Globals:
# PATHOUT_CMOR
# Arguments:
#   None
# Returns:
#   None
# Purpose: removes the temporary files generated by the cmorization
#####################################################################################################################
function remove_cmor_temp_files() {
  local cmor_files_path=$1
  # remove temporary files which might have been left around (#1250)
  find ${cmor_files_path}/ -mindepth 10 -type f -name '*_gr[a-z|A-Z|0-9]*.nc'
  find ${cmor_files_path}/ -mindepth 10 -type f -name '*_gn[a-z|A-Z|0-9]*.nc'
  find ${cmor_files_path}/ -mindepth 10 -type f -name '*_gr[a-z|A-Z|0-9]*.nc' -delete
  find ${cmor_files_path}/ -mindepth 10 -type f -name '*_gn[a-z|A-Z|0-9]*.nc' -delete
}

#####################################################################################################################
# Globals:
# CMORIZATION, PATHOUT, RUN_dir, CHUNK, IS_TRANSFER
# Arguments:
#   None
# Returns:
#   None
# Purpose: saves the output of the cmorization, this is the default output by default for all type of experiments,
# these are saved by chunk, these outputs are moved to the specified target folder
#####################################################################################################################
function save_outputs_cmorization() {
  . ${PROJDIR}/plugins/cmorization.sh
  if [[ "${CMORIZATION-}" != '' ]] && [[ ${CMORIZATION} == 'TRUE' ]]; then
    #
    # Save CMORIZED output at permanent storage and clean disk
    #

    #defaults when we use intermediate storage
    PATHOUT_CMOR=${PATHOUT}/cmorfiles/${START_date}/${MEMBER}
    # for direct transfer to esarchive we adapt the paths
    if [[ "${IS_TRANSFER-}" == TRUE ]]; then
      PATHOUT_CMOR=${PATHOUT}/cmorfiles
    fi

    cmor_folder=${RUN_dir}/cmor_outputs
    cmor_folder_list=$(ls -d ${cmor_folder}/cmor_*_${CHUNK} 2>/dev/null) && returncode=$? || returncode=$?
    if [[ ! -z "${cmor_folder_list-}" && ${returncode} -eq 0 ]]; then
      # remove temporary files which might have been left around before transfer (#1250)
      for cmor_tmp_folder in ${cmor_folder_list[@]}; do
        remove_cmor_temp_files ${cmor_tmp_folder}
      done
    fi
    mkdir_intermediate_storage ${PATHOUT_CMOR} Earth
    # check if the cmor folder exists
    if [[ -d ${cmor_folder} ]]; then
      # move the files
      move_cmor_files ${cmor_folder} ${PATHOUT_CMOR} ${IS_TRANSFER}
    fi
  fi
}

#####################################################################################################################
# Globals:
# # output_dir_tm5, CHUNK, EXPID, START_date, MEMBER, Chunk_start_date, Chunk_end_date, PATH_FLAGS
#
# Arguments:
#   None
# Returns:
#   None
# Purpose: saves the initial condition files if this feature is enabled, the files are compressed and then moved to
# the specified target directory for such kind of files
#####################################################################################################################
function save_ic() {
  PATHOUT_IC=${PATHOUT}/${START_date}/${MEMBER}/ic
  mkdir_intermediate_storage ${PATHOUT_IC} Earth
  remote_ic_folder=${RUN_dir}/save_ic/ic
  if [[ -d ${remote_ic_folder} ]]; then
    cd ${remote_ic_folder}
    filelist=$(echo $(ls -1 IC_*${Chunk_start_date}-${Chunk_end_date}*))
    if [[ ! -z ${filelist} ]]; then
      echo "moving ICs files "
      move_files "${filelist}" ${PATHOUT_IC} ${IS_TRANSFER}
    fi
  fi
}

#####################################################################################################################
# Globals:
# RUN_dir, TEMPLATE_NAME, PATH_FLAGS, CHUNK, TEMPLATE_NAME
# Arguments:
#   None
# Returns:
#   None
# Purpose: main function for the save of all outputs, there is a flag system that allows to resume the saving of these
# files if an exception or error occurs, the flags are deleted at the end of the job when all outputs were processed
# successfully
#####################################################################################################################
function save_outputs() {

  cd ${RUN_dir}

  # atmos.
  save_outputs_atm

  # ocean
  save_outputs_oce

  # LPJG
  save_outputs_lpjg

  # OSM
  save_outputs_osm

  # TM5
  save_outputs_tm5

  #cmor files
  save_outputs_cmorization

  # common
  case "${TEMPLATE_NAME-}" in
  "ecearth3")
    if [[ -e ${PATH_FLAGS}/outa_${CHUNK} && -e ${PATH_FLAGS}/outo_${CHUNK} ]]; then
      touch ${PATH_FLAGS}/out_${CHUNK}
    fi
    ;;
  "ifs3")
    if [[ -e ${PATH_FLAGS}/outa_${CHUNK} ]]; then
      touch ${PATH_FLAGS}/out_${CHUNK}
    fi
    ;;
  "nemo3")
    if [[ -e ${PATH_FLAGS}/outo_${CHUNK} ]]; then
      touch ${PATH_FLAGS}/out_${CHUNK}
    fi
    ;;
  "lsm")
    touch ${PATH_FLAGS}/out_${CHUNK}
    ;;
  *)
    echo "CLEAN - template / model not supported: " + "${TEMPLATE_NAME-}"
    exit 1
    ;;
  esac
}

##########
## MAIN ##
##########

if [[ "${DEBUG_MODE-}" == "FALSE" ]]; then

  #
  # Setup paths
  #

  setup_paths

  #
  # Prepare restarts (in case, if some chunks need to be rerun or the experiment is to be extended)
  #


  #
  # Save restart files at permanent storage
  # we tar the files, removing the target files after the tar has been created and then we move the tar to the permanent
  # storage by calling the move_files function
  # Note: in all cases the .tar files are removed to avoid wasting space
  #

  save_restarts

  #
  # Save output files at permanent storage and clean disk (including ece3-postproc outputs depending of the type of experiment )
  #

  save_outputs

  #
  # Save LOGS
  #

  save_logs

  #
  # Save initial conditions files (ic) to permanent storage
  #

  save_ic

  #
  # Nudging Management
  #
  if [[ -d ${output_dir_atm} ]]; then
    clean_atm_nudging
  fi

  #
  # Tail of the chunk  (deleted all restart/output folders from scratch after all the clean process took place)
  #

  remove_tail_chunk

  #
  # Save ece3-postproc diags at permanent storage
  #

  if [ "${TEMPLATE_NAME-}" == "ifs3" ] || [ "${TEMPLATE_NAME-}" == "ecearth3" ] || [ "${TEMPLATE_NAME-}" == "lsm" ] ; then
    save_ece3_postproc
  fi

  #
  # Check Final condition, before starting next simulation
  #

  check_final_condition

fi

###################
# Autosubmit tailer
###################
set -xuve
echo $(date +%s) >> ${job_name_ptrn}_STAT
touch ${job_name_ptrn}_COMPLETED
exit 0

