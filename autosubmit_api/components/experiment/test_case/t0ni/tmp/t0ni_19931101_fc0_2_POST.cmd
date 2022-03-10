#!/bin/bash

###############################################################################
#                   POST t0ni EXPERIMENT
###############################################################################
#
#SBATCH --qos=debug
#SBATCH -A bsc32
#
#
#SBATCH --cpus-per-task=1
#0
#SBATCH -n 1
#SBATCH -t 01:00:00
#SBATCH -J t0ni_19931101_fc0_2_POST
#SBATCH --output=/gpfs/scratch/bsc32/bsc32627/t0ni/LOG_t0ni/t0ni_19931101_fc0_2_POST.cmd.out
#SBATCH --error=/gpfs/scratch/bsc32/bsc32627/t0ni/LOG_t0ni/t0ni_19931101_fc0_2_POST.cmd.err

#
###############################################################################
###################
# Autosubmit header
###################
set -xuve
job_name_ptrn='/gpfs/scratch/bsc32/bsc32627/t0ni/LOG_t0ni/t0ni_19931101_fc0_2_POST'
echo $(date +%s) > ${job_name_ptrn}_STAT

###################
# Autosubmit job
###################

#!/usr/bin/env bash
set -xuve

# This job performs the postprocessing of the simulation(s) output files.
# Saves last CHUNK's restart files.
# Saves output files to an outputs subdirectory, and rebuilds NEMO output.
# Postprocesses Ocean and Atmosphere files and performs the cmorization.
# It uses postprocessing.sh and atmospheric_nudging.sh plugins.

#
# Var instantiation & architecture
#

STAMP=$(date +%Y_%m_%d_%H_%M)
CURRENT_ARCH=marenostrum4
HPCARCH=marenostrum4
HPCPROJ=bsc32
HPCUSER=bsc32627
EXPID=t0ni
JOBNAME=t0ni_19931101_fc0_2_POST
ROOTDIR=/gpfs/scratch/bsc32/bsc32627/t0ni
TEMPLATE_NAME=ecearth3
TASKTYPE=POST

PROJDEST=auto-ecearth3

PROJ_TYPE=STANDARD
CMORIZATION=TRUE
CMOR_MODEL_ID=EC-EARTH-AOGCM
CMOR_EXP=piControl
ECE3_POSTPROC=FALSE
BSC_OUTCLASS=reduced
CMIP6_OUTCLASS=
PISCES=FALSE
OCEAN_STORERST=FALSE
NEMO_resolution=ORCA025L75
MODEL=ecearth
VERSION=trunk
START_date=19931101
START_date_1=19931031
MEMBER=fc0
SCRATCH_DIR=/gpfs/scratch
MODEL_RES=HR
SAVEMMA=FALSE
if [[ -z ${SAVEMMA-} ]]; then SAVEMMA="FALSE"; fi
SAVEDDA=FALSE
if [[ -z ${SAVEDDA-} ]]; then SAVEDDA="FALSE"; fi
ATM_REDUCED_OUTPUT=FALSE
ATM_SH_CODES=""
ATM_SH_LEVELS=""
ATM_GG_CODES=""
ATM_GG_LEVELS=""
NUMPROC=1
PROJDIR=${ROOTDIR}/${PROJDEST}

#
# Chunk Management
#
CHUNK=2
Chunk_start_date=19931201
Chunk_end_date=19931231
Chunk_last=TRUE
CHUNKSIZEUNIT=month
numchunks=2
# In months
RUN_months=1
# In days
RUN_days=31

# Nudging management
ATM_NUDGING=FALSE
ATM_refnud=

[[ "FALSE" == TRUE ]] && LPJG=TRUE || LPJG=FALSE
[[ "FALSE" == TRUE ]] && LPJG_SAVE_ICMCL=TRUE || LPJG_SAVE_ICMCL=FALSE

[[ "FALSE" == TRUE ]] && OSM=TRUE || OSM=FALSE
OSM_CONFIG="osm:post_all"
[[ -z $OSM_CONFIG ]] && OSM_CONFIG="osm"

[[ "FALSE" == TRUE ]] && TM5=TRUE || TM5=FALSE
TM5_EMISS_FIXYEAR=0
[[ "FALSE" == TRUE ]] && DEBUG_MODE=TRUE || DEBUG_MODE=FALSE

HPCROOTDIR=/gpfs/scratch/bsc32/bsc32627/t0ni
#
# PERFORMANCE METRICS
#
# Sum the output of the current SIM (stat date and member) in bytes needed to compute the Data intensity
#
total_output=$(du -s ${HPCROOTDIR}/${START_date}/${MEMBER}/runtime/output/*/*/ | awk '{print $1}' | paste -sd+ | bc)
echo "total output ${START_date} ${MEMBER}" ${total_output}

#
# Common (exports & imports)
#

export HPCPROJ

. ${PROJDIR}/platforms/${CURRENT_ARCH}/configure.sh
. ${PROJDIR}/plugins/postprocessing.sh

#####################################################################################################################
# Globals:  START_date, RUN_months, EXPID, SAVEDDA, ATM_REDUCED_OUTPUT, ATM_REDUCED_DAILY, ATM_SH_CODES,
# ATM_SH_LEVELS, ATM_GG_CODES, ATM_GG_LEVELS, PROJ_TYPE, CURRENT_ARCH
#
# Arguments:
#   version
# Returns:
#   None
# Purpose:  Postprocessing of atmos. component (common for ece3)
#####################################################################################################################
function create_mma() {
  dir=$(pwd)
  [[ -z ${PROJ_TYPE} ]] && PROJ_TYPE="STANDARD"
  set +xuve
  [ ${CURRENT_ARCH} == 'marenostrum4' ] && module load CDO/1.8.2
  set -xuve
  nmonthini=$(echo ${START_date} | cut -c5-6)
  nyearini=$(echo ${START_date} | cut -c1-4)
  nmon=1
  year=${nyearini}
  while [[ $nmon -le ${RUN_months} ]]; do
    nmonthini=${nmonthini#0}
    month=$((nmonthini + (CHUNK - 1) * RUN_months + nmon - 1))
    year=$((nyearini + ((month - 1) / 12)))
    month=$((month - ((month - 1) / 12) * 12))
    month=$(printf '%02d' ${month})
    types="SH GG"
    if [[ "${PROJ_TYPE}" == "PRIMAVERA" ]] || [[ -f ${RUN_dir}/postins/pptdddddd0300 ]]; then
      freq_list=(3 6)
    elif [[ -f ${RUN_dir}/postins/pptdddddd0300 ]]; then
      freq_list=(3 6)
    else
      freq_list=(6)
    fi

    for freq in ${freq_list[@]}; do
      for type in SH GG; do
        prefix=ICM${type}${EXPID}
        file=${prefix}+${year}${month}
        if [[ ! -e ${file}.grb ]]; then
          if [[ $type == "SH" ]]; then
            echo "if ( time % ${freq}00 == 0 && levelType == 100 ) {" >rules_file
            echo "        write \"${file}_[param].grb\";" >>rules_file
            echo "}" >>rules_file
          else
            echo "if ( time % ${freq}00 == 0 ) {" >rules_file
            echo "        write \"${file}_[param].grb\";" >>rules_file
            echo "}" >>rules_file
          fi
          grib_filter rules_file ${file}

          for gf in $(ls ${file}_*.grb); do
            cdo -R -r -t ecmwf -f nc splitvar ${gf} ${file}_
            rm -f ${gf}
          done

          for infile in $(ls ${file}_*.nc); do
            name=$(basename $infile .nc)
            quant=$(echo $name | sed s/${prefix}+${year}${month}_//)
            outfile=IM_${quant}_${year}${month}
            # Needed because last timestep is the 00:00 hours of the next day of the month
            cdo -f nc -r -timmean ${prefix}+${year}${month}_${quant}.nc ${outfile}_mm.nc
            rm -f ${prefix}+${year}${month}_${quant}.nc
          done

          cdo -f nc -r -merge IM_*_${year}${month}_mm.nc MMA_${EXPID}_${freq}h_${type}_${year}${month}.nc
          gzip -f -9 MMA_${EXPID}_${freq}h_${type}_${year}${month}.nc
          rm -f IM_*_${year}${month}_mm.nc*
        fi # end of file.grb
      done # end of type
    done # freq
    nmon=$((nmon + 1))
  done # end of RUN_months
  cd $dir
}

#####################################################################################################################
# Globals: START_date, CHUNK, RUN_months, ATM_SH_CODES, ATM_GG_CODES, ATM_REDUCED_OUTPUT
#
# Arguments:
#   None
# Returns:
#   None
# Purpose: Saves raw IFS output, only run this if SAVEDDA=TRUE, if ATM_REDUCED_OUTPUT is enabled, the raw data will
#          not be generated and only the grib files will be present
#####################################################################################################################
function create_dda() {
  nmonthini=$(echo $START_date | cut -c5-6)
  nmonthini=${nmonthini#0}
  nyearini=$(echo $START_date | cut -c1-4)
  # when running first CHUNK take care of file with first timestep ICM??${EXPID}+000000
  [[ $CHUNK -eq 1 ]] && nmon=0 || nmon=1
  while [[ $nmon -le $RUN_months ]]; do
    if [[ $nmon -eq 0 ]]; then
      month=00
      year=0000
    else
      month=$((nmonthini + (CHUNK - 1) * RUN_months + nmon - 1))
      year=$((nyearini + ((month - 1) / 12)))
      month=$((month - ((month - 1) / 12) * 12))
      month=$(printf '%02d' ${month})
    fi
    types="SH GG"
    for type in $types; do
      prefix=ICM${type}${EXPID}
      file=${prefix}+${year}${month}
      if [[ ! -e ${file}.grb ]]; then
        # Save reduced daily output
        if [[ $ATM_REDUCED_OUTPUT == 'TRUE' ]]; then
          case $type in
          SH)
            params=$ATM_SH_CODES
            levels=$ATM_SH_LEVELS
            ;;
          GG)
            params=$ATM_GG_CODES
            levels=$ATM_GG_LEVELS
            ;;
          esac
          if [[ "$params" != "" ]]; then
            # create empty $file.grb to append each variable
            touch ${file}.grb
            rm -f ${file}_*
            grib_copy_params=""
            for param in ${params}; do grib_copy_params+=${param}"/"; done
            grib_copy_params=${grib_copy_params:0:-1}
            grib_copy -w param=$grib_copy_params $file ${file}_[param]
            for param in ${params}; do
              #grib_copy -w param=$param $file ${file}_${param}
              if [[ ! -f ${file}_${param} ]]; then
                echo "WARNING: param ${param} not found in ${file}!!!"
                echo "disable the exit statement in post.tmpl.sh to continue..."
                exit 1
              else
                # filter by levels - this was not tested for 3h and 6h output,
                # a grib_filter might be needed instead
                case $type in
                SH)
                  if [[ $ATM_SH_LEVELS != '' ]]; then
                    cdo sellevel,$levels ${file}_${param} ${file}_${param}_tmp
                    mv ${file}_${param}_tmp ${file}_${param}
                  fi
                  ;;
                GG) # store levels against the following GG params only
                  case $param in
                  133.128)
                    cdo sellevel,$levels ${file}_${param} ${file}_${param}_tmp
                    mv ${file}_${param}_tmp ${file}_${param}
                    ;;
                  246.128)
                    cdo sellevel,$levels ${file}_${param} ${file}_${param}_tmp
                    mv ${file}_${param}_tmp ${file}_${param}
                    ;;
                  247.128)
                    cdo sellevel,$levels ${file}_${param} ${file}_${param}_tmp
                    mv ${file}_${param}_tmp ${file}_${param}
                    ;;
                  248.128)
                    cdo sellevel,$levels ${file}_${param} ${file}_${param}_tmp
                    mv ${file}_${param}_tmp ${file}_${param}
                    ;;
                  esac #param
                  ;;
                esac #type
                #append file to $file.grb
                cat ${file}_${param} >>${file}.grb
                rm -f ${file}_${param}
              fi # ! -f ${file}_${param}
            done #for param in ${params}
            #sort by date to make cdo happy and create a file similar to the original one
            grib_copy -B "date:i asc, time asc, paramId:i asc" ${file}.grb ${file}.grb_tmp
            mv ${file}.grb_tmp ${file}.grb
            #cdo -s merge ${file}_* $file.grb3
          fi # end of  "$params" != ""
        else
          # copy entire file to $file.grb
          cp $file ${file}.grb
        fi # end of ATM_REDUCED_OUTPUT
      else
        mv $file ${file}.grb
      fi # end of file.grb
    done # end of type
    nmon=$((nmon + 1))
  done # end of RUN_months
}

#####################################################################################################################
# Globals:
#   CHUNKSIZEUNIT, RUN_months, Chunk_start_date, Chunk_end_date , CURRENT_ARCH, EXPID,
# Arguments:
#   output_dir
# Returns:
#   None
# Purpose: Save icmcl files containing vegetation state
#          These files are similar to the "era20c vegetation from an off-line LPJ-Guess run forced with ERA20C"
#          files used in the EC-Earth runscript. This is only only useful for LPJG runs, in which vegetation is transient
#####################################################################################################################
function create_icmcl() {
  # sanity checks
  # only support 12 monthly chunks
  [ "${CHUNKSIZEUNIT}" != "month" ] && echo "INFO in create_icmcl, only CHUNKSIZEUNIT=month is supported!" && return
  [[ "${RUN_months}" != "12" ]] && echo "INFO in create_icmcl, only 12 month chunks are supported!" && return
  # current CHUNK must start on Jan. 1 and end on Dec. 31
  [ "${Chunk_start_date:4:4}" != "0101" ] && echo "INFO in create_icmcl, only Chunk_start_date=yyyy0101 is supported!" && return
  [ "${Chunk_end_date:4:4}" != "1231" ] && echo "INFO in create_icmcl, only Chunk_end_date=yyyy1231 is supported!" && return

  vars="var66,var67,var27,var28,var29,var30"
  vars_grib="66/67/27/28/29/30"
  vars_mean="var66,var67,var27,var28"
  vars_type="var29,var30"
  year=${Chunk_start_date:0:4}
  set +xuve
  [ ${CURRENT_ARCH} == 'marenostrum4' ] && module load CDO/1.8.2
  set -xuve
  nmonthini=$(echo $START_date | cut -c5-6)
  nyearini=$(echo $START_date | cut -c1-4)
  nmon=1

  while [[ $nmon -le $RUN_months ]]; do
    nmonthini=${nmonthini#0}
    month=$((nmonthini + (CHUNK - 1) * RUN_months + nmon - 1))
    year=$((nyearini + ((month - 1) / 12)))
    month=$((month - ((month - 1) / 12) * 12))
    month=$(printf '%02d' ${month})
    prefix=ICMGG${EXPID}
    rm -f icmcl_${year}${month}.grb icmcl_${year}${month}_{mean,type}.grb tmp.grb
    grib_copy -w paramId=${vars_grib},dataTime=0000 ${prefix}+${year}${month} tmp.grb
    cdo -O settaxis,${year}-${month}-15,00:00:00 -timmean -selvar,${vars_mean} tmp.grb icmcl_${year}${month}_mean.grb
    cdo -O seldate,${year}-${month}-15T00:00:00 -selvar,${vars_type} tmp.grb icmcl_${year}${month}_type.grb
    cdo -O merge icmcl_${year}${month}_*.grb icmcl_${year}${month}.grb
    rm -f icmcl_${year}${month}_{mean,type}.grb tmp.grb
    nmon=$((nmon + 1))
  done # end of RUN_months

  year=${Chunk_start_date:0:4}

  # merge all monthly files into one file
  cdo -O mergetime icmcl_${year}??.grb icmcl_${year}.grb
  rm -f icmcl_${year}??.grb

  # re-order them in the same order as era20c files
  cdo -O splitname icmcl_${year}.grb icmcl_${year}_
  ifiles=""
  IFS=","
  for v in $vars; do ifiles+=" icmcl_${year}_${v}.grb "; done
  unset IFS
  cdo -O merge $ifiles icmcl_${year}.grb
  # fix wrong metadata
  grib_set -s gridType=reduced_gg,timeRangeIndicator=10 icmcl_${year}.grb tmp.grb
  mv tmp.grb icmcl_${year}.grb
  rm -f icmcl_${year}_* tmp.grb

  # rename final file
  #mv icmcl_${year}.grb ICMCL${EXPID}+${year}00.grb
}

load_platform_environment

#
# General Paths and Conf and common functionality.
#
#

#these variables are instantiated by the load_platform_environment
MODEL_DIR=${MODELS_DIR}/${MODEL}/${VERSION}
LOGDIR=${ROOTDIR}/LOG_${EXPID}

#####################################################################################################################
# Globals:
#   None
# Arguments:
#   None
# Returns:
#   None
# Purpose: Post-process lucia logs if they exist, later CLEAN will transfer it to intermediate storage or esarchive
#####################################################################################################################
function post_process_logs() {
  post_process_lucia_logs
}

#####################################################################################################################
# Globals: CHUNK
#
# Arguments:
#   restart prefix ( it can be ifs, nemo, oasis, lpjg )
# Returns:
#   None
# Purpose: moves the restarts depending of the prefix passed as parameter to a location that will be used
# as a target for compressing the restart files, for the first chunk this is omitted, same if it is a osm experiment
#####################################################################################################################
function save_restarts() {
  local prefix=$1
  local uppercase_prefix=$(echo ${prefix} | tr '[:lower:]' '[:upper:]')
  mkdir -p ${uppercase_prefix}_Restart_${CHUNK}
  [[ ${prefix} == 'ifs' ]] && cat rcf
  if [[ ${CHUNK} != 1 ]] || [[ ${prefix} == 'osm' ]]; then
    # check if the folder has any file inside
    if [ "$(ls -A restart/${prefix}/$(printf %03d $((CHUNK))))" ]; then
      [[ -d restart/${prefix}/$(printf %03d $((CHUNK))) ]] && [[ ! -z $(ls restart/${prefix}/$(printf %03d $((CHUNK)))/*) ]] && mv restart/${prefix}/$(printf %03d $((CHUNK)))/* ${uppercase_prefix}_Restart_${CHUNK}
    fi
  fi
}

#####################################################################################################################
# Globals: PROJDIR, CHUNK
#
# Arguments:
#   None
# Returns:
#   None
# Purpose: post process lucia logs ( related to performance metrics )
#####################################################################################################################
function post_process_lucia_logs() {

  runsh_logdir=log/$(printf %03d $((CHUNK)))
  #check if there are Lucia logs present
  if ls ${runsh_logdir}/lucia.??.?????? >/dev/null 2>&1; then
    lucia_log=lucia.log
    ${PROJDIR}/sources/sources/oasis3-mct/util/lucia/lucia >${lucia_log}
    tar -czf lucia.tgz -C ${runsh_logdir} .
    rm -f ${runsh_logdir}/lucia.??.??????
  fi
}

#####################################################################################################################
# Globals:
#  LPJG_SAVE_ICMCL, output_dir_atm, Chunk_start_date, Chunk_end_date
# Arguments:
#   None
# Returns:
#   None
# Purpose: save ICMCL files containing vegetation maps if LPJG_SAVE_ICMCL == TRUE
#         (used to be active if this was an LPJG run and outclass was not piControl or reduced)
#          and if current chunk starts on Jan. 1st and ends on Dec. 31st
#          do this before create_mma which renames the grib files
#####################################################################################################################
function postprocess_icmcl() {
  if [[ "${LPJG_SAVE_ICMCL}" == "TRUE" ]] && [[ ! -e ${output_dir_atm}/post_icmcl ]] && [[ "${Chunk_start_date:4:4}" == "0101" ]] && [[ "${Chunk_end_date:4:4}" == "1231" ]]; then
    cd ${output_dir_atm}
    create_icmcl
    touch ${output_dir_atm}/post_icmcl
  fi
}

#####################################################################################################################
# Globals:
#   ROOTDIR, START_date, MEMBER, SCRATCH_TMP_DIR, HPCUSER, JOBNAME, MODEL_DIR
# Arguments:
#   None
# Returns:
#   None
# Purpose: prepare the paths for the postprocessing job
#####################################################################################################################
function setup_paths() {

  RUN_dir=${ROOTDIR}/${START_date}/${MEMBER}/runtime
  INIPATH=${ROOTDIR}/${START_date}/${MEMBER}/inidata
  rm -rf ${SCRATCH_TMP_DIR}
  mkdir -p ${SCRATCH_TMP_DIR}
  ini_data_dir=${MODEL_DIR}/inidata
}

#####################################################################################################################
# Globals:
#   RUN_days, TEMPLATE_NAME, RUN_dir, CHUNK, LPJG, OSM, TM5,
# Arguments:
#   None
# Returns:
#   None
# Purpose: Prepare the paths for the chunk to be executed of the ongoing simulation
#####################################################################################################################
function setup_chunks() {

  # In hours
  RUN_hours=$((RUN_days * 24))
  #default values for unbounded vars that will be used later
  output_dir_atm=""

  # Model output path w.r.t chunk number
  if [ "${TEMPLATE_NAME}" == "ifs3" ] || [ "${TEMPLATE_NAME}" == "ecearth3" ]; then
    output_dir_atm=${RUN_dir}/output/ifs/$(printf "%03d\n" ${CHUNK})
  fi

  if [[ "${LPJG}" == TRUE ]]; then output_dir_lpjg=${RUN_dir}/output/lpjg/$(printf "%03d\n" ${CHUNK}); fi
  if [[ "${OSM}" == TRUE ]]; then output_dir_osm=${RUN_dir}/output/osm/$(printf "%03d\n" ${CHUNK}); fi
  if [[ "${TM5}" == TRUE ]]; then output_dir_tm5=${RUN_dir}/output/tm5/$(printf "%03d\n" ${CHUNK}); fi

  cd ${RUN_dir}

}

#
# IFS3
#

#####################################################################################################################
# Globals: CHUNK
# Arguments:
#   None
# Returns:
#   None
# Purpose: Check either simulation completed successfully or not
#####################################################################################################################
function check_simulation_ifs3() {
  if [[ ${CHUNK} == 1 ]]; then
    if [[ ! -e restart/ifs ]]; then
      echo "failed chunk"
      exit 1
    fi
  else
    if [[ ! -e restart/ifs/$(printf %03d $((CHUNK))) ]]; then
      echo "failed chunk"
      exit 1
    fi
  fi
}

#####################################################################################################################
# Globals:
#
# Arguments:
#   None
# Returns:
#   None
# Purpose:  Save IFS restart files
#####################################################################################################################
function save_restarts_ifs3() {
  save_restarts "ifs"
}

#####################################################################################################################
# Globals: CREATE_ATM_NUDGING, EXTRA_DIR, EXPID ,PROJDIR, IFS_resolution, output_dir_atm
# Chunk_start_date, start_date_mm
# Arguments:
#   None
# Returns:
#   None
# Purpose: Create atmospheric nudging - Omar, preparation of reference files for Chunk 1+2 (currently disabled)
#####################################################################################################################
function setup_atm_nudging() {

  # Atmospheric nuding - Lauriance, Omar
  # Preperation of refence files for Chunk 3
  # Ref: e007, i05g

  cd ${RUN_dir}
  if [[ "${ATM_NUDGING-}" != '' ]] && [[ "${ATM_NUDGING-}" == 'TRUE' ]]; then
    PATHNUDA=${EXTRA_DIR}/nudging/atmos/T511L91
    start_date_mm=$(echo ${Chunk_start_date} | cut -c5-6)
    start_date_mm=${start_date_mm#0} # Cut leading '0'
    start_date_yyyy=$(echo ${Chunk_start_date} | cut -c1-4)

    . ${PROJDIR}/plugins/atmospheric_nudging.sh

    if [[ ${CHUNK} -le $((numchunks - 3)) ]]; then
      atm_nudg_chunk_lnk 3
    fi
  fi
}

function create_atm_nudging() {

  # Create atmospheric nudging - Omar
  # Preperation of refence files for Chunk 1+2
  #
  # Ref: xxxx
  CREATE_ATM_NUDGING=FALSE # To be added to exp conf (with this this is never being used)
  if [[ ${CREATE_ATM_NUDGING} != '' ]] && [[ ${CREATE_ATM_NUDGING} == 'TRUE' ]] && [[ ! -e ${output_dir_atm}/atm_nudging ]]; then
    PATHNUDA=${EXTRA_DIR}/nudging/atmos/T511L91
    if [ ! -d "${PATHNUDA}/${EXPID}" ]; then
      mkdir -p ${PATHNUDA}/${EXPID}
    fi
    #these var are already declared above at the beginning
    start_date_mm=$(echo $Chunk_start_date | cut -c5-6)
    start_date_mm=${start_date_mm#0} # Cut leading '0'
    start_date_yyyy=$(echo $Chunk_start_date | cut -c1-4)
    #load nudging plugin
    . $PROJDIR/plugins/atmospheric_nudging.sh

    # Create reference files from output
    create_atm_nudg_chunk
    touch ${output_dir_atm}/atm_nudging
  fi
}

#
# Postprocessing
#

#####################################################################################################################
# Globals: SAVEDDA, output_dir_atm, SAVEDDA
#
# Arguments:
#   None
# Returns:
#   None
# Purpose: postprocess dda and mma files for the atmosphere component
#####################################################################################################################
function postprocess_output_ifs3() {
  cd ${output_dir_atm}
  if [[ ${SAVEMMA} == 'TRUE' ]] && [[ ! -e ${output_dir_atm}/post_mma ]]; then
    create_mma
    touch ${output_dir_atm}/post_mma
  fi
  if [[ ${SAVEDDA} == 'TRUE' ]] && [[ ! -e ${output_dir_atm}/post_dda ]]; then
    create_dda
    touch ${output_dir_atm}/post_dda
  fi
}

#
# NEMO3
#

#####################################################################################################################
# Globals: CHUNK
#
# Arguments:
#   None
# Returns:
#   None
# Purpose: Check either simulation completed successfully or not
#####################################################################################################################
function check_simulation_nemo3() {
  if [[ ${CHUNK} == 1 ]]; then
    #check that the number of ice and oce restarts are the same and that the last one has the same processor number
    num_ice=$(ls | grep -E "${EXPID}_[[:digit:]]{1,}_restart_ice_[[:digit:]]{4}\.nc" | wc -l)
    num_oce=$(ls | grep -E "${EXPID}_[[:digit:]]{1,}_restart_oce_[[:digit:]]{4}\.nc" | wc -l)
    last_ice=$(ls | grep -E "${EXPID}_[[:digit:]]{1,}_restart_ice_[[:digit:]]{4}\.nc" | tail -1 | grep -o ....\.nc | cut -c1-4)
    last_oce=$(ls | grep -E "${EXPID}_[[:digit:]]{1,}_restart_oce_[[:digit:]]{4}\.nc" | tail -1 | grep -o ....\.nc | cut -c1-4)
    if [[ "$last_oce" != "$last_ice" || "$num_ice" != "$num_oce" ]]; then
      echo "failed chunk"
      exit 1
    fi
  else
    if [[ ! -e restart/nemo/$(printf %03d $((CHUNK))) ]]; then
      echo "failed chunk"
      exit 1
    fi
  fi

}

#####################################################################################################################
# Globals:
#
# Arguments:
#   None
# Returns:
#   None
# Purpose: saves the nemo3 restarts
#####################################################################################################################
function save_restarts_nemo3() {
  save_restarts "nemo"
}

#
# LPJ-GUESS
#

#####################################################################################################################
# Globals: CHUNK
#
# Arguments:
#   None
# Returns:
#   None
# Purpose: Check either simulation completed successfully or not
#####################################################################################################################
function check_simulation_lpjg() {
  # TODO check chunk 1
  if [[ ! -e log/$(printf %03d $((CHUNK)))/guess.log ]]; then
    echo "failed chunk (LPJG)"
    exit 1
  fi
}

#####################################################################################################################
# Globals: output_dir_lpjg
#
# Arguments:
#   None
# Returns:
#   None
# Purpose: compress the lpjg files
#####################################################################################################################
function postprocess_output_lpjg() {
  cd ${output_dir_lpjg}
  find *.out -type f | xargs -I % gzip %
}

#
# OSM - Offline Surface Model
#

#####################################################################################################################
# Globals: CHUNK
#
# Arguments:
#   None
# Returns:
#   None
# Purpose: Check either simulation completed successfully or not
#####################################################################################################################
function check_simulation_osm() {
  # TODO check chunk 1
  if [[ ! -e log/$(printf %03d $((CHUNK))) ]]; then
    echo "failed chunk (OSM)"
    exit 1
  fi
}

#####################################################################################################################
# Globals: ROOTDIR, OSM_CONFIG, RUN_dir, EXPID, CHUNK, output_dir_osm, osm ( config object )
#
# Arguments:
#   None
# Returns:
#   None
# Purpose: postprocess for a osm experiment, icmcl files will be fixed and lpjg forcings will be generated,
#          also era-land surface fields will be generated
#####################################################################################################################
function postprocess_output_osm() {

  # check which extra post actions to do based on the OSM_CONFIG variable
  source $ROOTDIR/librunscript.sh

  config="${OSM_CONFIG}"

  # run osm post script which was generated in the SIM by osm_post_gen_script in libosm.sh
  #   this script is created during the SIM job
  #   if has_config osm_post_all then land_param and lpjg_forcing are done (so no need to run them below)
  if ! has_config osm:post_none; then
    . ${RUN_dir}/${EXPID}_osm_post_${CHUNK}.sh
  fi

  # save icmcl files - already done with osm:post_all
  if ! has_config osm:post_all && has_config osm:post_icmcl; then
    osm_post_icmcl $out_dir
  fi

  # fix icmcl files (implemented in EC-Earth just after 3.3.2 release, so might not be needed)
  if has_config osm:post_all || has_config osm:post_icmcl; then
    cd $output_dir_osm
    for ((year = leg_start_date_yyyy; year <= leg_end_date_yyyy_full; year += 1)); do
      cdo setmisstoc,0. icmcl_${year}.grb tmp.grb
      grib_set -s gridType=reduced_gg,timeRangeIndicator=10 tmp.grb icmcl_${year}.grb
    done
  fi

  # save era-land surface fields - already done with osm:post_all
  if ! has_config osm:post_all && has_config osm:post_land_param; then
    mkdir -p ${land_param_dir}
    osm_post_land_param $out_dir ${land_param_dir}
  fi

  # generate lpjg_forcing - already done with osm:post_all
  if ! has_config osm:post_all && has_config osm:post_lpjg_forcing; then
    config=lpjg_forcing,gen_forcing
    mkdir -p ${lpjg_forcing_dir}
    has_config lpjg_forcing && lpjg_gen_forcing $leg_start_date_yyyy $leg_end_date_yyyy_full
  fi

  touch $output_dir_osm/post_osm
}

#
# TM5
#

#####################################################################################################################
# Globals:
#
# Arguments:
#   None
# Returns:
#   None
# Purpose: Check either simulation completed successfully or not
#####################################################################################################################
function check_simulation_tm5() {
  if [[ ! -e tm5.ok ]]; then
    echo "failed chunk (TM5)"
    exit 1
  fi
}

#
# EC-Earth3
#

#####################################################################################################################
# Globals:
#
# Arguments:
#   None
# Returns:
#   None
# Purpose: check if the simulation was carried out successfully
#####################################################################################################################
function check_simulation_ecearth3() {
  check_simulation_ifs3
  check_simulation_nemo3
}

#####################################################################################################################
# Globals:
#
# Arguments:
#   None
# Returns:
#   None
# Purpose: Save OASIS, IFS and NEMO restart files
#####################################################################################################################
function save_restarts_ecearth3() {
  save_restarts "oasis"
  save_restarts "ifs"
  save_restarts "nemo"
}

#
# LSM (Land Surface Model)
#

#####################################################################################################################
# Globals: OSM
#
# Arguments:
#   None
# Returns:
#   None
# Purpose: check if the simulation was carried out successfully for a lsm experiment
#####################################################################################################################
function check_simulation_lsm() {
  [[ "${OSM}" == TRUE ]] && check_simulation_osm || true
}

#####################################################################################################################
# Globals: OSM, LPJG
#
# Arguments:
#   None
# Returns:
#   None
# Purpose: saves the restarts for a lsm experiment
#####################################################################################################################
function save_restarts_lsm() {
  [[ "${OSM-}" == TRUE ]] && save_restarts "osm" || true
  if [[ "${LPJG-}" == "TRUE" ]] && [[ "${OSM-}" == "TRUE" ]]; then
    save_restarts "oasis"
  fi
}

if [[ "${DEBUG_MODE-}" == "FALSE" ]]; then

  ######################################################
  #
  # MAIN Postproccessing (Common to all models)
  #
  ######################################################
  #
  # Prepare paths & chunks to be checked
  #
  setup_paths

  setup_chunks

  #
  # Check if it was a successful simulation
  #

  check_simulation_${TEMPLATE_NAME}
  if [[ "${LPJG}" == TRUE ]]; then check_simulation_lpjg; fi
  if [[ "${TM5}" == TRUE ]]; then check_simulation_tm5; fi

  #
  # Move restart, log and output files
  #

  #
  # Save restart files
  #
  save_restarts_${TEMPLATE_NAME}

  # LPJG restarts stay in their original folder
  # LPJG restarts have a different numbering convention than other restarts,
  # so they are NOT moved to LPJG_Restart_$chunk
  # OSM restarts stay in their original folder
  if [[ "$TM5" == TRUE ]]; then save_restarts "tm5"; fi

  #
  # Postprocessing - logs
  #

  post_process_logs

  #
  # Postprocessing
  #

  # ifs
  if [ "${TEMPLATE_NAME}" == "ifs3" ] || [ "${TEMPLATE_NAME}" == "ecearth3" ]; then

    if [[ ! -z "${output_dir_atm}" ]]; then
      mkdir -p ${output_dir_atm}
      # check if the folder was created correctly
      if [[ ! -d ${output_dir_atm} ]]; then
        echo "The folder "${output_dir_atm}" doesn´t exists, exiting..."
        exit 1
      fi
    fi

    cd ${output_dir_atm}

    setup_atm_nudging
    create_atm_nudging

    postprocess_output_ifs3

    [[ "${ECE3_POSTPROC-}" != 'FALSE' ]] && postprocess_output_ece3_postproc

    postprocess_icmcl

  fi

  # lsm stuff

  if [ "${TEMPLATE_NAME}" == "lsm" ]; then
    if [[ "${LPJG}" == TRUE ]] && [[ "${ECE3_POSTPROC-}" != 'FALSE' ]]; then
      postprocess_output_ece3_postproc
    fi
  fi

  if [[ "${LPJG}" == TRUE ]]; then postprocess_output_lpjg; fi

  if [[ "${OSM}" == TRUE ]]; then postprocess_output_osm; fi

  # nemo - nothing to do
  echo "common.post Done"

fi

###################
# Autosubmit tailer
###################
set -xuve
echo $(date +%s) >> ${job_name_ptrn}_STAT
touch ${job_name_ptrn}_COMPLETED
exit 0

