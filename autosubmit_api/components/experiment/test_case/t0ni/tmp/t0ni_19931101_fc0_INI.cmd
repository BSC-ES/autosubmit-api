#!/bin/bash

###############################################################################
#                   INI t0ni EXPERIMENT
###############################################################################
#
#SBATCH --qos=debug
#SBATCH -A bsc32
#
#
#SBATCH --cpus-per-task=1
#0
#SBATCH -n 1
#SBATCH -t 00:30:00
#SBATCH -J t0ni_19931101_fc0_INI
#SBATCH --output=/gpfs/scratch/bsc32/bsc32627/t0ni/LOG_t0ni/t0ni_19931101_fc0_INI.cmd.out
#SBATCH --error=/gpfs/scratch/bsc32/bsc32627/t0ni/LOG_t0ni/t0ni_19931101_fc0_INI.cmd.err

#
###############################################################################
###################
# Autosubmit header
###################
set -xuve
job_name_ptrn='/gpfs/scratch/bsc32/bsc32627/t0ni/LOG_t0ni/t0ni_19931101_fc0_INI'
echo $(date +%s) > ${job_name_ptrn}_STAT

###################
# Autosubmit job
###################

set -xuve

#
# Var instantiation
#

STAMP=$(date +%Y_%m_%d_%H_%M)
HPCARCH=marenostrum4
SCRATCH_DIR=/gpfs/scratch
HPCPROJ=bsc32
HPCUSER=bsc32627
EXPID=t0ni
exp_name=t0ni
JOBNAME=t0ni_19931101_fc0_INI
PROJDEST=auto-ecearth3
ROOTDIR=/gpfs/scratch/bsc32/bsc32627/t0ni
TEMPLATE_NAME=ecearth3
CURRENT_ARCH=marenostrum4

OASIS_ini=a2s5
OASIS_ini_date=22990101
OASIS_ini_member="fc0"
oas_numproc=

OCEAN_ini=a2s5
OCEAN_ini_date=22990101
OCEAN_ini_member="fc0"

ICE=LIM3
ICE_ini=a2s5
ICE_ini_date=22990101
ICE_ini_member="fc0"

NEMO_resolution=ORCA025L75
nem_grid_wol=$(echo ${NEMO_resolution} | cut -d 'L' -f 1) # without level (wol)
nem_res_hor=$(echo ${NEMO_resolution} | sed 's:ORCA\([0-9]\+\)L[0-9]\+:\1:')

#PISCES vars
PISCES=FALSE
PISCES_ini=
PISCES_ini_date=
PISCES_ini_member=""
PISCES_OFF=FALSE
PISCES_OFF_DYN=

ATM_ini=a2s5
ATM_ini_date=22990101
ifs_grid=T511L91
ifs_grid_wol=$(echo ${ifs_grid} | cut -d 'L' -f 1) # without level (wol)
ifs_res_hor=$(echo ${ifs_grid} | sed 's:T\([0-9]\+\)L\([0-9]\+\):\1:')
ATM_ini_member="fc0"
ATM_refnud=
ATM_ini_member_perturb=FALSE
if [[ -z "$ATM_ini_member " ]]; then ATM_ini_member_perturb=FALSE; fi
ATM_NUDGING=FALSE

[[ "FALSE" == TRUE ]] && OSM=TRUE || OSM=FALSE
[[ "FALSE" == TRUE ]] && LPJG=TRUE || LPJG=FALSE
LPJG_ini=
[ -z $LPJG_ini ] && LPJG_ini=""
LPJG_ini_date=
LPJG_ini_member=""
LPJG_STATE_DIR=
[ -z $LPJG_STATE_DIR ] && LPJG_STATE_DIR=""
LPJG_STATE_DIR_INI=TRUE
[ -z $LPJG_STATE_DIR_INI ] && LPJG_STATE_DIR_INI="TRUE"

[[ "FALSE" == TRUE ]] && TM5=TRUE || TM5=FALSE
TM5_ini=a2c0
TM5_ini_date=
TM5_ini_member="fc0"
TM5_NLEVS=34
TM5_CONFIG="tm5:chem,o3fb,ch4fb,aerfb"

#need vars for MEMBER generation/nudging
START_date=19931101
START_date_1=19931031
MEMBER=fc0
MODEL=ecearth
VERSION=trunk
PROJDIR=$ROOTDIR/$PROJDEST

#NEM_FORCING_SET=CoreII
nem_forcing_set=CoreII
nem_fixed_forcing_year=-1

#CHUNK number
CHUNK=1
#size of each CHUNK
CHUNKSIZE=1
#number of chunks of the experiment
num_chunks=2
#unit of the chuk size. Can be hour, day, month or year.
chunk_size_unit=month
Chunk_start_date=19931101
Chunk_end_date=19931130

#Ocean vars (surface regeneration)
SURF_RESTO=FALSE
SURF_RESTO_DATA=s4_surfresto
SURF_RESTO_DATA_member=all_members
SURF_RESTO_MASK=DEFAULT

OCE_NUDG=FALSE
OCE_NUDG_DATA=
OCE_NUDG_DATA_member=
OCE_NUDG_COEFF=

#Ini generation flags
DELETE_INI_DIR_ON_INI=TRUE
FORCE_RUN_FROM_SCRATCH=TRUE
USE_INTERMEDIATE_STORAGE=FALSE
DT_HOST=
DT_USER=

[ "ifs" == "" ] && ifs_veg_source="era20c" || ifs_veg_source="ifs"
[[ "FALSE" == TRUE ]] && DEBUG_MODE=TRUE || DEBUG_MODE=FALSE

export HPCPROJ

# Setup basic configuration for the choosen platform
. ${PROJDIR}/platforms/${CURRENT_ARCH}/configure.sh
# Dealing with initial conditions (plugin)
. ${PROJDIR}/plugins/utils.sh
. ${PROJDIR}/platforms/${HPCARCH}/filesystem.sh

#prepare running environment
load_platform_environment

#
# General Paths and Conf.(these lines must be ALWAYS after the load_platform_environment invocation)
#
MODEL_DIR=${MODELS_DIR}/${MODEL}/${VERSION}
ini_data_dir=${MODEL_DIR}/inidata
RUN_dir=${ROOTDIR}/${START_date}/${MEMBER}
INIPATH=${RUN_dir}/inidata

#####################################################################################################################
# Globals:
# INTERMEDIATE_EXP_DIR, EXPID, START_date, MEMBER, RUN_dir, INIPATH, DELETE_INI_DIR_ON_INI
# HPCUSER, JOBNAME, SCRATCH_TMP_DIR
# Arguments:
#   None
# Returns:
#   None
# Purpose: Prepare the folders and paths for the initialization process of the experiment
#
#####################################################################################################################
function setup_ini_folders() {
  #Create intermediate storage
  local storage_dir=${INTERMEDIATE_EXP_DIR}/${EXPID}/${START_date}/${MEMBER}
  if ! test_intermediate_storage "-d ${storage_dir}"; then
    mkdir_intermediate_storage ${storage_dir} Earth
    if ! test_intermediate_storage "-d ${storage_dir}"; then
      echo " OMG we have a problem!"
      echo " this directory should exist! ${storage_dir}"
      exit
    fi
  fi

  #Check if ini/runtime folders should be deleted and regenerated
  if [ "${DELETE_INI_DIR_ON_INI}" == "TRUE" ]; then
    rm -rf ${INIPATH}
    if [[ $(ls runtime/* >&/dev/null) ]] && [[ -z "${FORCE_RUN_FROM_SCRATCH}" ]]; then
      # let user know user of potential issues of leaving runtime folder
      echo "Runtime '${RUN_dir}/runtime' directory already existing, please remove it manually or set DELETE_RUN_DIR_ON_INI to true in [common] section in prog_EXPID.conf"
    fi
  fi

  mkdir -p ${INIPATH}

  #in DT machine this can be empty, in that case tmp folder will be the root of the experiment
  rm -rf ${SCRATCH_TMP_DIR}
  mkdir -p ${SCRATCH_TMP_DIR}

  #
  # Model Paths and Conf.
  #
  ini_data_dir=${MODEL_DIR}/inidata
}

#####################################################################################################################
# Globals:  out_member: id of the member for the component,  out_member_perturb,
# Arguments:
#   ini_member: id or list of id for the initialization of one component
# Returns:
#   None
# Purpose: Choose the member id for one given component
#
#####################################################################################################################
function calc_member() {
  ini_member=${1}
  membid=${2}
  membarr=($ini_member)
  nbmemb=${#membarr[@]}
  out_member_perturb=false
  if [[ $nbmemb == 1 ]]; then
    if [[ $ini_member == "all_members" ]]; then
      out_member=$membid
    else
      out_member=$ini_member
    fi
  else
    imemb=10#${membid/fc/}
    out_member=${membarr[$imemb]}
  fi
}

#####################################################################################################################
# Globals:
#  EXPID, ini_data_dir, START_date, IC_DIR
#  ATM_ini, ATM_ini_member, ifs_grid, ATM_ini_member_perturb
# Arguments:
#  membid: id of the member
# Returns:
#   None
# Purpose: IC's for Atmosphere Component (EC-Earth3)
#
#####################################################################################################################
function atm_ini() {
  local membid=${1}
  # use this grib_set command to make sure the date is correct
  local grib_cmd="grib_set -s dataDate=${START_date},dataTime=0"
  if [[ $ATM_ini != '' ]]; then
    # user can specify alternate date of the ATM_ini for e.g. starting from a spinup
    local ini_start_date=$([[ -z "${ATM_ini_date}" ]] && echo ${START_date} || echo ${ATM_ini_date})
    # copy IC's
    local ifile=${ATM_ini}_${ATM_ini_member}_${ini_start_date}00.tar.gz
    # ICś always are copied from intermediate storage independently of the CLEAN+TRANSFER feature
    copy_intermediate_storage ${IC_DIR}/atmos/${ifs_grid}/${ATM_ini}/${ifile} . "TRUE"
    tar -xzvf ${ifile}
    rm -f ${ifile}
    # rename IC's
    mkdir -p ifs/${ifs_grid}/${START_date}
    ${grib_cmd} ICMGG*INIT ifs/${ifs_grid}/${START_date}/ICMGGECE3INIT   #ICMGG${EXPID}INIT
    ${grib_cmd} ICMSH*INIT ifs/${ifs_grid}/${START_date}/ICMSHECE3INIT   #ICMSH${EXPID}INIT
    ${grib_cmd} ICMGG*INIUA ifs/${ifs_grid}/${START_date}/ICMGGECE3INIUA #ICMGG${EXPID}INIUA
    rm -f ICMGG*INIT ICMSH*INIT ICMGG*INIUA
  else
    mkdir -p ifs/${ifs_grid}/${START_date}/
    ${grib_cmd} ${ini_data_dir}/ifs/${ifs_grid}/${START_date}/ICMGGECE3INIT ifs/${ifs_grid}/${START_date}/ICMGGECE3INIT
    ${grib_cmd} ${ini_data_dir}/ifs/${ifs_grid}/${START_date}/ICMSHECE3INIT ifs/${ifs_grid}/${START_date}/ICMSHECE3INIT
    ${grib_cmd} ${ini_data_dir}/ifs/${ifs_grid}/${START_date}/ICMGGECE3INIUA ifs/${ifs_grid}/${START_date}/ICMGGECE3INIUA
  fi

  #if requested, perturb t field in IFS IC using the member # as seed
  if [[ "${ATM_ini_member_perturb}" == "TRUE" ]]; then
    param="t"
    seed=${membid//[!0-9]/}
    mv ifs/${ifs_grid}/${START_date}/ICMSHECE3INIT ifs/${ifs_grid}/${START_date}/ICMSHECE3INIT_ORIG
    python $PROJDIR/plugins/perturb_var.py -s $param --seed $seed ifs/${ifs_grid}/${START_date}/ICMSHECE3INIT_ORIG ifs/${ifs_grid}/${START_date}/ICMSHECE3INIT
  fi
}

#####################################################################################################################
# Globals:
#   START_date_1,  OCEAN_ini, OCEAN_ini_member,
#   NEMO_resolution, OCEAN_ini_date, OCEAN_ini_date, IC_DIR
# Arguments:
#   None
# Returns:
#   None
# Purpose: IC's for Ocean Component (EC-Earth3)
#
#####################################################################################################################
function oce_ini() {
  local ini_start_date=$([[ -z "${OCEAN_ini_date}" ]] && echo ${START_date_1} || echo $(date -d "${OCEAN_ini_date} - 1 day" +%Y%m%d))
  nemo_components_ini_ic $([[ -z "${OCEAN_ini}" ]] && echo "FALSE" || echo "${OCEAN_ini}") ${IC_DIR}/ocean/${NEMO_resolution}/${OCEAN_ini} ${OCEAN_ini}_${OCEAN_ini_member}_${ini_start_date}_restart.nc restart_oce.nc "OCE_ini"
}

#####################################################################################################################
# Globals:
#   START_date_1, ICE_ini_date, ICE_ini, ICE_ini_member, nem_grid_wol, IC_DIR
# Arguments:
#   None
# Returns:
#   None
# Purpose: IC's for Sea Ice Component (EC-Earth3)
#
#####################################################################################################################
function ice_ini() {
  local ini_start_date=$([[ -z "${ICE_ini_date}" ]] && echo ${START_date_1} || echo $(date -d "${ICE_ini_date} - 1 day" +%Y%m%d))
  nemo_components_ini_ic $([[ -z "${ICE_ini}" ]] && echo "FALSE" || echo "${ICE_ini}") ${IC_DIR}/ice/${nem_grid_wol}_LIM3/${ICE_ini} ${ICE_ini}_${ICE_ini_member}_${ini_start_date}_restart_ice.nc restart_ice.nc "ICE_ini"
}

#####################################################################################################################
# Globals:
# PISCES_ini, PISCES_ini_member, START_date_1, NEMO_resolution, ini_start_date
# Arguments:
#   None
# Returns:
#   None
# Purpose: IC's for PISCES component (EC-Earth3)
#
#####################################################################################################################
function pisces_ini() {
  local ini_start_date=$([[ -z "${PISCES_ini_date}" ]] && echo ${START_date_1} || echo $(date -d "${PISCES_ini_date} - 1 day" +%Y%m%d))
  nemo_components_ini_ic $([[ -z "${PISCES_ini}" ]] && echo "FALSE" || echo "${PISCES_ini}") ${IC_DIR}/ocnBgChem/${NEMO_resolution}/${PISCES_ini} ${PISCES_ini}_${PISCES_ini_member}_${ini_start_date}_restart_trc.nc restart_trc.nc "PISCES_ini"
}

#####################################################################################################################
# Globals:
# PISCES_OFF, PISCES_OFF_DYN, EXTRA_DIR, Chunk_start_date, INIPATH
# Arguments:
#   None
# Returns:
#   None
# Purpose:use the right forcing fields for PISCES offline - PISCES component (EC-Earth3)
#
#####################################################################################################################
function pisces_offline_forcing() {

  if [[ ! -z ${PISCES_OFF} ]]; then
    year=$(echo ${Chunk_start_date} | cut -c1-4)
  fi

  mkdir -p ${INIPATH}/nemo/pisces/pisces_dyn
  if [[ ${PISCES_OFF_DYN} == '' ]]; then
    echo "ERROR Data used to force PISCES OFFLINE not specified, precise the data with PISCES_OFF_DYN in the [pisces] section of proj_EXPID.conf"
  fi
 if [[ ${PISCES_OFF_DYN} != '' ]]; then
    for offline_pisces_forcing_file in $(ls ${EXTRA_DIR}/dynamical_fields/${PISCES_OFF_DYN}/*); do
      filename="${offline_pisces_forcing_file%.*}"
      file_postfix="${filename: -1}"
      if [[ ! -f ${INIPATH}/nemo/pisces/pisces_dyn/OfflineForcing_grid_${file_postfix}.nc ]]; then
        ln -s ${offline_pisces_forcing_file} ${INIPATH}/nemo/pisces/pisces_dyn/OfflineForcing_grid_${file_postfix}.nc
      fi
    done
  else
    echo "ERROR dynamical fields do not exist "
  fi

}

#####################################################################################################################
# Globals:
#   EXPID, ini_data_dir, START_date_1, IC_DIR
#   ICE_ini, ICE_ini_member, nem_grid_wol, ICE
# Arguments:
#   #$1 - ICs_Component, $2 - ICs_Path, $3 - ICs_Filename, $4 - ICs_output, $5 - string for msg out
# Returns:
#   None
# Purpose: Generic function to copy the IC's for the different NEMO components( Ocean, ICE amd PISCES (EC-Earth3))
#
#####################################################################################################################
function nemo_components_ini_ic() {

  #$1 - ICs_Component
  #$2 - ICs_Path
  #$3 - ICs_Filename
  #$4 - ICs_output
  #$5 - string for msg out

  if [[ "${1}" != "FALSE" ]]; then
    copy_intermediate_storage ${2}/${3}.gz . "TRUE"
    gunzip ${3}.gz
    mv ${3} ${4}
  else
    echo "Start ${5} component at rest"
  fi
}

######################################################
########################IFS3##########################
######################################################

#####################################################################################################################
# Globals:
# RUN_dir,  ATM_NUDGING, CHUNK, Chunk_start_date, CHUNKSIZE ,EXTRA_DIR
# Arguments:
#   None
# Returns:
#   None
# Purpose: Prepare the Nudging for the atmosphere component by taking into account the IFS resolution
#
#####################################################################################################################
function ifs_setup_nudging() {
  # Atmospheric nudging - Lauriane, Omar
  # Preperation of refence files for Chunk 1+2
  # Ref: e007, i05g

  PATHNUDA=${EXTRA_DIR}/nudging/atmos/T511L91
  rm -f *rlxmlgg* *rlxmlsh*

  start_date_mm=$(echo $Chunk_start_date | cut -c5-6)
  start_date_mm=${start_date_mm#0} # Cut leading '0'
  start_date_yyyy=$(echo $Chunk_start_date | cut -c1-4)
  RUN_months=${CHUNKSIZE}
  . $PROJDIR/plugins/atmospheric_nudging.sh

  # Prepare first three chunks
  atm_nudg_chunk_lnk 0
  atm_nudg_chunk_lnk 1
  atm_nudg_chunk_lnk 2

}

#####################################################################################################################
# Globals:
# RUN_dir,  ATM_ini_member, MEMBER, out_member
# Arguments:
#   None
# Returns:
#   None
# Purpose: set the member for the atmosphere component
#
#####################################################################################################################
function ifs_setup_members() {
  #
  # IFS
  #
  if [[ ${ATM_ini_member} != '' ]]; then
    calc_member "${ATM_ini_member}" ${MEMBER}
    ATM_ini_member=${out_member}
  fi
}

#####################################################################################################################
# Globals:
# RUN_dir,  SCRATCH_TMP_DIR, MEMBER, out_member
# Arguments:
#   None
# Returns:
#   None
# Purpose: Main function for initialization - ifs3
#
#####################################################################################################################
function ifs3_init() {

  #
  # IFS
  #
  ifs_setup_members

  #
  # Prepare stuff for experiment
  #
  # ifs-only experiment, atm_ini is required, but ifs_setup_nudging can be disabled, check if activated or not to load the IC's

  cd ${SCRATCH_TMP_DIR}

  atm_ini $MEMBER

  [[ "$ATM_NUDGING" == "TRUE" ]] && ifs_setup_nudging

  cd ${INIPATH}

}

#####################################################################################################################
# Globals:
# LPJG,  ifs_veg_source, EXTRA_DIR, ifs_grid, INIPATH
# Arguments:
#   None
# Returns:
#   None
# Purpose: initialization of the lpjg component ( linkinh of icmcl files in inidata folder
#
#####################################################################################################################
function ifs_veg_source_init() {

  case ${ifs_veg_source} in

  "custom_"*)
    # custom not allowed when running with LPJG, since when config=lpjg:fdbck the ifs_veg_source is not used
    if [[ $LPJG == "TRUE" ]]; then
      echo "requested IFS_VEG_SOURCE = ${ifs_veg_source} but this is not allowed when LPJG=TRUE!"
      exit 1
    fi
    # link icmcl folder
    veg_version=${ifs_veg_source:7}
    dir_veg_source=${EXTRA_DIR}/icmcl/${ifs_grid}/icmcl_${veg_version}
    if [ ! -d ${dir_veg_source} ]; then
      echo "requested IFS_VEG_SOURCE = ${ifs_veg_source} but not found in ${dir_veg_source}"
      exit 1
    else
      ln -sf ${dir_veg_source} ${INIPATH}/ifs/${ifs_grid}
    fi
    ;;

  *)
    echo "Nothing to do for ifs veg source ${ifs_veg_source}"
    ;;

  esac

}

######################################################
########################NEMO3#########################
######################################################

#####################################################################################################################
# Globals: MEMBER, EXTRA_DIR, NEMO_resolution, INIPATH,
#          OCE_NUDG_DATA, OCE_NUDG_DATA_member, OCE_NUDG_COEFF
# Arguments:
#   None
# Returns:
#   None
# Purpose: 03/2018 - Yohan Ruprich-Robert, Valentina Sicardi; 08/2021 - Vladimir Lapin
# Link ocean nudging files with salinity and temperature 3D and nudging coefficients (resto.nc).
# Note that the files to be linked are outside the inidata folder, in the repository.
#
#####################################################################################################################
function nemo_setup_nudging() {

  mkdir -p ${INIPATH}/nemo/oce_nudg

  # if ${OCE_NUDG_DATA_member} is undefined or "all_members", use the same as ${MEMBER}
  if [[ -z "${OCE_NUDG_DATA_member}" ]] || [[ "${OCE_NUDG_DATA_member}" == "all_members" ]]; then
    OCE_NUDG_DATA_member=${MEMBER}
  fi

  # if ${OCE_NUDG_COEFF} is undefined, use resto.nc from RESTO_DEFAULT
  if [[ -z "${OCE_NUDG_COEFF}" ]]; then
    OCE_NUDG_COEFF=RESTO_DEFAULT
  fi

  PATH_NUDG_FILE=${EXTRA_DIR}/nudging/ocean/${OCE_NUDG_DATA}/${NEMO_resolution}/${OCE_NUDG_DATA_member}
  PATH_NUDG_RESTO_COEFF=${EXTRA_DIR}/nudging/ocean/${OCE_NUDG_COEFF}/${NEMO_resolution}

  if [[ "${OCE_NUDG_DATA}" != '' ]] && [[ -d ${PATH_NUDG_FILE} ]]; then
    ln -fs ${PATH_NUDG_FILE}/temp_sal_*.nc ${INIPATH}/nemo/oce_nudg/
  else
    echo "ERROR The specified path for ocean nudging data is invalid: ${PATH_NUDG_FILE}"
    get_out="true"
  fi

  if [[ -d ${PATH_NUDG_RESTO_COEFF} ]]; then
    ln -fs ${PATH_NUDG_RESTO_COEFF}/resto.nc ${INIPATH}/nemo/oce_nudg/resto.nc
  else
    echo "ERROR The specified path for resto.nc is invalid: ${PATH_NUDG_RESTO_COEFF}"
    get_out="true"
  fi

}

#####################################################################################################################
# Globals: MEMBER, EXTRA_DIR, NEMO_resolution, INIPATH,
#   SURF_RESTO, SURF_RESTO_DATA, SURF_RESTO_DATA_member, SURF_RESTO_MASK
# Arguments:
#   None
# Returns:
#   None
# Purpose: 03/2018 - Yohan Ruprich-Robert, Valentina Sicardi; 08/2021 - Vladimir Lapin
# Link surface restoring files for salinity and temperature and an optional mask.
# Note that the files to be linked are outside the inidata folder, in the repository.
#
#####################################################################################################################
function nemo_surface_restoring() {

  mkdir -p ${INIPATH}/nemo/surface_restoring

  # if ${SURF_RESTO_DATA_member} is undefined or "all_members", use the same as ${MEMBER}
  if [[ -z "${SURF_RESTO_DATA_member}" ]] || [[ "${SURF_RESTO_DATA_member}" == "all_members" ]]; then
    SURF_RESTO_DATA_member=${MEMBER}
  fi

  # if ${SURF_RESTO_MASK} is undefined, use mask_restore.nc from RESTO_DEFAULT
  if [[ -z "${SURF_RESTO_MASK}" ]]; then
    SURF_RESTO_MASK=MASK_DEFAULT
  fi

  PATH_SURF_FILE=${EXTRA_DIR}/surface_restoring/ocean/${SURF_RESTO_DATA}/${NEMO_resolution}/${SURF_RESTO_DATA_member}
  PATH_SURF_MASK=${EXTRA_DIR}/surface_restoring/ocean/masks/${SURF_RESTO_MASK}/${NEMO_resolution}

  if [[ "${SURF_RESTO_DATA}" != '' ]] && [[ -d ${PATH_SURF_FILE} ]]; then
    ln -fs ${PATH_SURF_FILE}/sss_restore_data*.nc ${INIPATH}/nemo/surface_restoring/
    ln -fs ${PATH_SURF_FILE}/sst_restore_data*.nc ${INIPATH}/nemo/surface_restoring/
  else
    echo "ERROR The specified path for surface restoring data is invalid: ${PATH_SURF_FILE}"
    get_out="true"
  fi

  if [[ -d ${PATH_SURF_MASK} ]]; then
    ln -fs ${PATH_SURF_MASK}/mask_restore*.nc ${INIPATH}/nemo/surface_restoring/
  else
    echo "ERROR The specified path for surface restoring data is invalid: ${PATH_SURF_MASK}"
    get_out="true"
  fi

}

#####################################################################################################################
# Globals: OCEAN_ini_member, ICE_ini_member, PISCES_ini_member, MEMBER
#
# Arguments:
#   None
# Returns:
#   OCEAN_ini_member
# Purpose: Ocean/LIM member setup, Prepare member names and other needed ini data for members
#
#####################################################################################################################
function nemo_setup_members() {
  #
  # NEMO
  #

  if [[ "${OCEAN_ini_member}" != "" ]]; then
    calc_member "$OCEAN_ini_member" ${MEMBER}
    OCEAN_ini_member=${out_member}
  fi

  #
  # ICE
  #

  if [[ ${ICE_ini_member} != "" ]]; then
    calc_member "$ICE_ini_member" ${MEMBER}
    ICE_ini_member=${out_member}
  fi

  #
  # PISCES
  #

  if [[ ${PISCES_ini_member} != "" ]]; then
    calc_member "$PISCES_ini_member" ${MEMBER}
    PISCES_ini_member=${out_member}
  else
    PISCES_ini_member=fc0 # Warning: uses only one initial condition
  fi

}

#####################################################################################################################
# Globals: MEMBER, CHUNKSIZE, nem_forcing_set, INIPATH, ini_data_dir, PROJDIR, START_date
#
# Arguments:
#   None
# Returns:
#   None
# Purpose:  Ocean forcing setup,  Prepare the needed files for the setup for the atm forcings
# to be used only in NEMO only experiments
#
#####################################################################################################################
function nemo_setup_forcing() {

  ##############################################
  #        NEMO FORCING  WEIGHTS               #
  ##############################################
  MEMBER=${MEMBER}
  chunk_size=${CHUNKSIZE}
  if [[ -z ${nem_forcing_set-} ]]; then
    nem_forcing_set="CoreII"
  fi

  # Forcing files for salinity and temperature interpolation
  mkdir -p ${INIPATH}/nemo/forcing/weights
  ln -sf ${ini_data_dir}/nemo/forcing/weights/* ${INIPATH}/nemo/forcing/weights/

  source ${PROJDIR}/plugins/nemo_forcing.sh

  link_nemo_forcing ${START_date} ${chunk_size} ${num_chunks} ${chunk_size_unit}

}

#####################################################################################################################
# Globals: SCRATCH_TMP_DIR, OCE_NUDG
#
# Arguments:
#   None
# Returns:
#   None
# Purpose: Main function for initialization - Nemo3
#
#####################################################################################################################
function nemo3_init() {

  #
  # Prepare stuff for experiment
  # nemo-only template, nemo components are required but the rest of the components can be disabled and with this checks it is avoided to load the IC's for them when not necessary
  #

  cd ${SCRATCH_TMP_DIR}

  nemo_setup_members

  oce_ini

  [[ "${PISCES_OFF}" == "TRUE" ]] && pisces_offline_forcing

  [[ "${ICE}" == "LIM3" || "${ICE}" == "LIM2" ]] && ice_ini

  [[ "${PISCES}" == "TRUE" ]] &&  pisces_ini

  [[ "${OCE_NUDG}" == "TRUE" ]] && nemo_setup_nudging

  [[ "${SURF_RESTO}" == "TRUE" ]] && nemo_surface_restoring

  nemo_setup_forcing

  cd ${INIPATH}

}

######################################################
#######OASIS##########################################
######################################################

#####################################################################################################################
# Globals: OCEAN_ini, SCRATCH_TMP_DIR, PROJDIR
#
# Arguments:
#   None
# Returns:
#   None:
# Purpose:
# Function to execute the plugin that generates the proper OASIS restarts for IFS from the NEMO restarts when those restarts exist
####################################################################################################################
function generate_oasis_restarts() {

  . ${PROJDIR}/platforms/${CURRENT_ARCH}/configure.sh
  load_modules_oas_rsts_gen
  
  . ${PROJDIR}/platforms/common/common.ini.sh
  . ${PROJDIR}/platforms/${CURRENT_ARCH}/ini.sh
  gen_oasis_rsts
}

#####################################################################################################################
# Globals: OASIS_ini, ATM_ini, OCEAN_ini, ATM_ini_member_perturb, OASIS_ini_member, ATM_ini_member, MEMBER,
#   SCRATCH_TMP_DIR, IC_DIR, START_date, ifs_res_hor, nem_res_hor
#
# Arguments:
#   None
# Returns:
#   None
# Purpose:
#  only for coupled experiments: check which set of IC to use based in the following rules:
#  if OASIS_ini is not empty, look for the coupler restarts for that EXPID, if not found crash (IC files,
#  both flags mentioned below will be false)
#  if OASIS_ini is empty and ATM_ini = OCEAN_ini, look for the coupler restarts for ATM_ini,
#  if not found use the default ones (rst files) (use_rst_default_if_ic_not_found)
#  if OASIS_ini is empty and ATM_ini != OCEAN_ini, always use the default ones (rst files) (use_default_rst)
#  the case in which OASIS_ini has a defined value and ATM_ini = OCEAN_ini = null is abnormal thus not contemplated
#  here
#
#####################################################################################################################
function oasis_setup_ifs_nemo() {

  use_rst_default_if_ic_not_found="FALSE"
  use_default_rst="FALSE"
  if [[ -z ${OASIS_ini} ]]; then
    if [[ ${ATM_ini} == ${OCEAN_ini} ]] && [[ ! -z ${ATM_ini} ]]; then
      use_rst_default_if_ic_not_found="TRUE"
    else
      use_default_rst="TRUE"
    fi
  fi

  #for the OASIS member ini, is defined based on the following rules:
  #if OASIS_ini_member is empty -->  should match the ATM_ini_member/OCE_ini_member
  #if ATM_ini_perturb=true --> OASIS_ini_member should be ATM_ini_member

  if [[ "${ATM_ini_member_perturb}" == "TRUE" ]]; then
    OASIS_ini_member=${ATM_ini_member}
  fi

  if [[ -z "${OASIS_ini_member}" ]] && [[ ${ATM_ini_member} == ${OCEAN_ini_member} ]]; then
    #if both members are undefined , we use the default one defined in the experiment
    if [[ -z "${ATM_ini_member}" ]]; then
      OASIS_ini_member=${MEMBER}
    else
      OASIS_ini_member=${ATM_ini_member}
    fi
  fi

  #Point to the inidata folder
  cd ${SCRATCH_TMP_DIR}

  case ${nem_grid_wol} in
  ORCA1) oas_ogrd=O1t0 ;;
  ORCA025) oas_ogrd=Ot25 ;;
  *)
    echo "Unsupported horizontal resolution (NEMO): ${nem_grid_wol}"
    get_out="true"
    ;;
  esac

  # Grid definition files
  # destination path for the experiment where the ICs will stored
  # (also the sub-directory under which to find the default files in ${ini_data_dir})
  oas_sub_dir=oasis/T${ifs_res_hor}-ORCA${nem_res_hor}/rst
  # Restart files
  oasis_restart_files="rstas.nc rstos.nc"

  # location if the oasis ics
  oas_ics_dir=${IC_DIR}/coupler/T${ifs_res_hor}-ORCA${nem_res_hor}/${OASIS_ini}
  local ini_start_date=$([[ -z "${OASIS_ini_date}" ]] && echo ${START_date} || echo ${OASIS_ini_date})
  oas_ics_prefix=${OASIS_ini}_${OASIS_ini_member}_${ini_start_date}00_
  # get them from the IC folder if found ( we use these only when use_rst_default_if_ic_not_found =="FALSE" )
  if [[ "${use_rst_default_if_ic_not_found}" == "TRUE" ]]; then
    oas_ics_dir=${IC_DIR}/coupler/T${ifs_res_hor}-ORCA${nem_res_hor}/${ATM_ini}
    oas_ics_prefix=${ATM_ini}_${ATM_ini_member}_${START_date}00_
    echo "getting oasis restarts from ${oas_ics_dir}/${oas_ics_prefix}*"
  fi

  if [[ ! -d ${oas_sub_dir} ]]; then
    mkdir -p ${oas_sub_dir}
  fi

  if [[ ! -d xios/ORCA${nem_res_hor} ]]; then
    mkdir -p xios/ORCA${nem_res_hor}
  fi

  #check the condition by which the job should be aborted
  abort_if_files_not_found="FALSE"
  if [[ "${use_rst_default_if_ic_not_found}" == "FALSE" ]] && [[ "${use_default_rst}" == "FALSE" ]]; then
    abort_if_files_not_found="TRUE"
  fi

  # first iteration, check existence of OASIS_ini is defined in the proj.conf means that it should be used or crash if the files doesnt exists
  if [[ "${use_default_rst-}" == "FALSE" ]]; then
    for f in ${oasis_restart_files}; do
      #check the existence of the file
      if ! test_intermediate_storage "-f ${oas_ics_dir}/${oas_ics_prefix}${f}.gz"; then
        # Issue 811, if there are OASIS no restarts, we abort and not continue with the INI
        if [[ "${abort_if_files_not_found}" == "TRUE" ]]; then
          echo "ERROR: Oasis initial conditions not present for ${ATM_ini}, ORCA${nem_res_hor} and  ${OASIS_ini}, please check IC repository for oasis"
          echo "to use default oasis restarts please set OASIS_ini=  in proj.conf"
          get_out="true"
        else
          # at this point we know that the Oasis files for given configuration don't exist, then we use default ones in the case that
          # the job must continue and use default ones
          use_default_rst="TRUE"
        fi
      fi
    done
  fi

  # from the previous step we gather information about existence of IC for Oasis, in case they exists we use them
  # cases contemplated: (OCE_ini = ATM_ini) and OASIS_ini= empty and OASIS_ini!=empty
  for f in ${oasis_restart_files}; do
    if [[ "${use_default_rst}" == "FALSE" ]]; then
      rm -f ${oas_sub_dir}/${f}
      copy_intermediate_storage ${oas_ics_dir}/${oas_ics_prefix}${f}.gz . "TRUE"
      gunzip -c ${oas_ics_prefix}${f}.gz >${oas_sub_dir}/${f}
      rm -f ${oas_ics_prefix}${f}.gz
    else
      if [ -f ${ini_data_dir}/${oas_sub_dir}/${f} ]; then
        # only for the default case
        copy_default_restarts ${ini_data_dir}/${oas_sub_dir}/${f} ${oas_sub_dir}/${f}
      fi
    fi
  done

  #generate proper OASIS restart for IFS from the NEMO restart
  if [[ "${use_default_rst}" == "TRUE" && -f ${oas_sub_dir}/rstos.nc && ! -z ${OCEAN_ini} ]]; then
    generate_oasis_restarts
  fi
}

#####################################################################################################################
# Globals:
#   OASIS_ini, SCRATCH_TMP_DIR, ifs_res_hor, ifs_grid_wol, IC_DIR, OASIS_ini_date, START_date, ini_start_date,
#   OASIS_ini_member
# Arguments:
#   None
# Returns:
#   None
# Purpose: Setup LPJG oasis restart.
#          we handle them in a simple manner, considering OASIS_ini and OASIS_ini_member without testing
#          if the restart files exist (copy_intermediate_storage will raise an error)
#          and not considering ATM_ini/ATM_ini_member/ATM_ini_member_perturb
#
#####################################################################################################################
function oasis_setup_ifs_lpjg() {
  if [[ ! -z ${OASIS_ini} ]]; then

    #Point to the inidata folder
    cd ${SCRATCH_TMP_DIR}

    # Grid definition files

    # LPJG oasis restarts are in lpjg/oasismct/T255
    oas_sub_dir=lpjg/oasismct/T${ifs_res_hor}

    # location if the oasis ics
    oas_ics_dir=${IC_DIR}/coupler/${ifs_grid_wol}/${OASIS_ini}
    local ini_start_date=$([[ -z "${OASIS_ini_date}" ]] && echo ${START_date} || echo ${OASIS_ini_date})
    oas_ics_prefix=${OASIS_ini}_${OASIS_ini_member}_${ini_start_date}00_

    if [[ ! -d ${oas_sub_dir} ]]; then
      mkdir -p ${oas_sub_dir}
    fi

    oas_rst_ifs_lpjg="vegin.nc lpjgv.nc"

    for f in ${oas_rst_ifs_lpjg}; do
      rm -f ${oas_sub_dir}/${f}
      copy_intermediate_storage ${oas_ics_dir}/${oas_ics_prefix}${f}.gz . "TRUE"
      gunzip -c ${oas_ics_prefix}${f}.gz >${oas_sub_dir}/${f}
      rm -f ${oas_ics_prefix}${f}.gz
    done

  fi
}

#####################################################################################################################
# Globals: OASIS_ini, IC_DIR, ifs_res_hor, TM5_NLEVS, OASIS_ini_date, START_date, ini_start_date
#
# Arguments:
#   None
# Returns:
#   None
# Purpose: Setup TM5 oasis restart. Function divided to handle the case where only IFS+TM5 is run.
#
#####################################################################################################################
function oasis_setup_ifs_tm5() {
  if [[ ! -z ${OASIS_ini} ]]; then

    #Point to the inidata folder
    cd ${SCRATCH_TMP_DIR}

    # Grid definition files

    # destination path for the experiment where the ICs will stored
    # (also the sub-directory under which to find the default files in ${ini_data_dir})
    oas_sub_dir=oasis/T${ifs_res_hor}-TM5-LPJG/rst/${TM5_NLEVS}-levels

    # location if the oasis ics
    oas_ics_dir=${IC_DIR}/coupler/T${ifs_res_hor}-TM5-${TM5_NLEVS}-levels/${OASIS_ini}
    local ini_start_date=$([[ -z "${OASIS_ini_date}" ]] && echo ${START_date} || echo ${OASIS_ini_date})
    oas_ics_prefix=${OASIS_ini}_${OASIS_ini_member}_${ini_start_date}00_

    if [[ ! -d ${oas_sub_dir} ]]; then
      mkdir -p ${oas_sub_dir}
    fi

    # Get all oasis restart files in the TM5 oasis restart directory
    # Get only the nc filename (remove prefix and gz extension)
    oas_rst_ifs_tm5=$(ls ${oas_ics_dir}/${oas_ics_prefix}* | xargs -n 1 basename | sed -e 's/\.gz$//' | sed -e "s/^${oas_ics_prefix}//")

    for f in ${oas_rst_ifs_tm5}; do
      rm -f ${oas_sub_dir}/${f}
      copy_intermediate_storage ${oas_ics_dir}/${oas_ics_prefix}${f}.gz . "TRUE"
      gunzip -c ${oas_ics_prefix}${f}.gz >${oas_sub_dir}/${f}
      rm -f ${oas_ics_prefix}${f}.gz
    done
  fi
}

#####################################################################################################################
# Globals: INIPATH, START_year, ifs_grid_wol LPJG_STATE_DIR, LPJG_ini_member, SCRATCH_TMP_DIR, LPJG_ini,
#
# Arguments:
#   None
# Returns:
#   LPJG_ini_member
# Purpose: IC's for LPJG Component (EC-Earth3/lsm)
#
#####################################################################################################################
function lpjg_init() {

  if [[ $LPJG_ini != "" || $LPJG_STATE_DIR != "" ]]; then

    START_year=${START_date:0:4}
    lpjg_state_dir=lpjg/ini_state/${ifs_grid_wol}
    [[ "${START_date:4:4}" == "0101" ]] && lpjg_rst_dir=lpjg_state_${START_year} || lpjg_rst_dir=lpjg_state_${START_date}

    # first remove any existing lpjg_state folder for the START_year
    cd ${INIPATH}
    [[ -d ${lpjg_state_dir}/${lpjg_rst_dir} ]] && rm -rf ${lpjg_state_dir}/${lpjg_rst_dir}
    # make sure top-level ini_state folder exists
    mkdir -p ${lpjg_state_dir}

    if [[ $LPJG_ini != "" ]]; then

      if [[ ${LPJG_ini_member} != '' ]]; then
        calc_member "${LPJG_ini_member}" ${MEMBER}
        LPJG_ini_member=${out_member}
      fi

      lpjg_ics_dir=${IC_DIR}/lpjg/T${ifs_res_hor}/${LPJG_ini}
      local ini_start_date=$([[ -z "${LPJG_ini_date}" ]] && echo ${START_date} || echo ${LPJG_ini_date})
      lpjg_ics_file=${LPJG_ini}_${LPJG_ini_member}_${ini_start_date}00_lpjg.tgz
      copy_intermediate_storage ${lpjg_ics_dir}/${lpjg_ics_file} ${SCRATCH_TMP_DIR} "TRUE"

      cd ${lpjg_state_dir}
      # untar removing any folder structure (needed when untarring RESTV files)
      # TODO adapt this code for the filenames of restarts generated by other experiments (e.g. RESTV_a1tf_19800101_fc0_1_19800101-19801231.tar.gz)
      mkdir -p ${lpjg_rst_dir}
      tar xzvf ${SCRATCH_TMP_DIR}/${lpjg_ics_file} --transform='s/.*\///' -C ${lpjg_rst_dir}
      rm -rf ${SCRATCH_TMP_DIR}/${lpjg_ics_file}
      cd -

    # special treatment for the lpjg_state directories, maybe user has specified their location in LPJG_STATE_DIR
    elif [[ $LPJG_STATE_DIR != "" ]]; then
      # link to the folder if it already exists in LPJG_STATE_DIR
      if [[ -d ${LPJG_STATE_DIR}/${lpjg_rst_dir} ]] ; then
        ln -sf ${LPJG_STATE_DIR}/${lpjg_rst_dir} ${lpjg_state_dir}
      # untar .tgz file if necessary
      elif [[ -f ${LPJG_STATE_DIR}/${lpjg_rst_dir}.tgz ]] ; then
        # should we untar in the experiment's inidata folder to save space in scratch/projects?
        [[ $LPJG_STATE_DIR_INI == "TRUE" ]] && cd ${lpjg_state_dir} || cd ${LPJG_STATE_DIR}
        # untar removing any folder structure (needed when untarring RESTV files)
        # TODO adapt this code for the filenames of restarts generated by other experiments (e.g. RESTV_a1tf_19800101_fc0_1_19800101-19801231.tar.gz)
        mkdir -p ${lpjg_rst_dir}
        tar xzvf ${LPJG_STATE_DIR}/${lpjg_rst_dir}.tgz --transform='s/.*\///' -C ${lpjg_rst_dir}
        cd -
        [[ $LPJG_STATE_DIR_INI = "TRUE" ]] || ln -sf ${LPJG_STATE_DIR}/${lpjg_rst_dir} ${lpjg_state_dir}
      # if not found, link to the folder (which might be created during the workflow, if not SIM will fail)
      else
        echo "ERROR! cannot find ${lpjg_rst_dir} in ${LPJG_STATE_DIR}"
        [[ "${TEMPLATE_NAME}" != "lsm" ]] && exit 1
        mkdir -p ${LPJG_STATE_DIR}
        ln -sf ${LPJG_STATE_DIR}/${lpjg_rst_dir} ${lpjg_state_dir}
      fi
    fi
  fi
}

#####################################################################################################################
# Globals: TM5_ini, TM5_ini_member, IC_DIR, MEMBER, out_member, TM5_ini_date, ini_start_date, TM5_CONFIG,
# SCRATCH_TMP_DIR
#
# Arguments:
#   None
# Returns:
#   None
# Purpose: IC's for TM5 Component
#
#####################################################################################################################
function tm5_init() {
  if [[ ${TM5_ini} != "" ]]; then
    if [[ ${TM5_ini_member} != '' ]]; then
      calc_member "${TM5_ini_member}" ${MEMBER}
      TM5_ini_member=${out_member}
    fi

    tm5_ics_dir=${IC_DIR}/tm5/${TM5_ini}
    local ini_start_date=$([[ -z "${TM5_ini_date}" ]] && echo ${START_date} || echo ${TM5_ini_date})
    tm5_ics_prefix=${TM5_ini}_${TM5_ini_member}_${ini_start_date}00_
    cd ${tm5_ics_dir}
    # get available tm5 restart files
    tm5_ics_files=$(ls ${tm5_ics_prefix}TM5_restart_${ini_start_date}_0000_glb300x200.nc.gz ${tm5_ics_prefix}save_${ini_start_date}00_glb300x200.hdf.gz 2>/dev/null || true)

    [[ ${tm5_ics_files} = "" ]] && echo "ERROR cannot find TM5 IC files for ${ini_start_date} in ${tm5_ics_dir}" && exit 1

    [[ $TM5_CONFIG =~ "co2" ]] && tmversion="co2" || tmversion="cb05"
    tm5_sub_dir=tm5/restart/${tmversion}-ml${TM5_NLEVS}
    cd ${SCRATCH_TMP_DIR}
    mkdir -p ${tm5_sub_dir}

    for file in ${tm5_ics_files}; do
      copy_intermediate_storage ${tm5_ics_dir}/${file} . "TRUE"
      # Unzip into tm5_sub_dir removing prefix and gz extension from restart file
      gunzip -c ${file} >${tm5_sub_dir}/$(echo "${file%.*}" | sed -e "s/^${tm5_ics_prefix}//")
      rm -f ${file}
    done
  fi
}

######################################################
########################EC-Earth3######################
######################################################

#####################################################################################################################
# Globals: OCE_NUDG, MEMBER
#
# Arguments:
#   None
# Returns:
#   None
# Purpose:  Main function for initialization - EC-Earth3
#
#####################################################################################################################
function ecearth3_init() {

  #
  # IFS
  #

  ifs_setup_members

  #
  # NEMO
  #
  nemo_setup_members

  #
  # OASIS
  #

  #
  # COMMON - Prepare stuff for experiment
  #
  cd ${SCRATCH_TMP_DIR}

  atm_ini $MEMBER

  oce_ini

  [[ "${PISCES_OFF}" == "TRUE" ]] && pisces_offline_forcing

  [[ "${ICE}" == "LIM3" || "${ICE}" == "LIM2" ]] && ice_ini

  [[ "${PISCES}" == "TRUE" ]] &&  pisces_ini

  [[ "$ATM_NUDGING" == "TRUE" ]] && ifs_setup_nudging

  [[ "${OCE_NUDG}" == "TRUE" ]] && nemo_setup_nudging

  [[ "${SURF_RESTO}" == "TRUE" ]] && nemo_surface_restoring

  cd ${INIPATH}

}

######################################################
##########################LSM#########################
######################################################

#####################################################################################################################
# Globals: SCRATCH_TMP_DIR, OSM, MEMBER
#
# Arguments:
#   None
# Returns:
#   None
# Purpose: Main function for initialization - LSM
#
#####################################################################################################################
function lsm_init() {

  cd ${SCRATCH_TMP_DIR}

  if [[ "$OSM" == TRUE ]]; then
    ifs_setup_members
    atm_ini $MEMBER
  fi
}

if [[ "${DEBUG_MODE-}" == "FALSE" ]]; then

  ######################################################
  #
  # MAIN
  #
  ######################################################

  #error handling
  export get_out="false"

  #prepare main inidata folder
  setup_ini_folders

  #init data for the experiment
  ${TEMPLATE_NAME}_init
  cd ${INIPATH}

  # generate the inidata folder - we will make a copy (symbolic links) of the folder
  copy_inidata

  # custom ifs_veg_source
  ifs_veg_source_init

  #if it is a coupled experiment, we setup OASIS coupler
  if [[ "${TEMPLATE_NAME}" == "ecearth3" ]]; then
    oasis_setup_ifs_nemo
  fi

  # IFS-LPJG restarts
  [[ "${TEMPLATE_NAME}" != "lsm" ]] && [[ $LPJG == "TRUE" ]] && oasis_setup_ifs_lpjg
  # special treatment of LPJG ini_state, do it after copying all links
  [[ "${TEMPLATE_NAME}" == "ecearth3" ]] && [[ $LPJG == "TRUE" ]] && lpjg_init
  # if it a lsm run always copy/link LPJG files even if LPJG!=TRUE
  [[ "${TEMPLATE_NAME}" == "lsm" ]] && lpjg_init

  # IFS-TM5 restarts
  if [[ ${TM5} == "TRUE" ]]; then
    oasis_setup_ifs_tm5
    tm5_init
  fi

  #restore path
  cd ${INIPATH}
  if [[ -e inidata/rcf ]]; then
    rm -f rcf
    cp inidata/rcf .
  fi
  #copy ic/restarts to inidata
  [ ! -z "$(ls -A ${SCRATCH_TMP_DIR})" ] && cp -rf --remove-destination ${SCRATCH_TMP_DIR}/* .
  #remove temporary folder used to unpack restarts and ICs
  cd ${ROOTDIR}
  #remove temporary user folder used
  rm -rf ${SCRATCH_TMP_DIR}
  ls -l

  echo "Generating checksum file to check if the inidata is modified during the experiment"

  cd ${ROOTDIR}/${START_date}/${MEMBER}
  inidata_checksum_generate ini

  echo "common.ini Done"

  if [[ "${get_out}" == "true" ]]; then exit 1; fi

fi

###################
# Autosubmit tailer
###################
set -xuve
echo $(date +%s) >> ${job_name_ptrn}_STAT
touch ${job_name_ptrn}_COMPLETED
exit 0

