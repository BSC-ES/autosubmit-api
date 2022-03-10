#!/bin/bash

###############################################################################
#                   EARTHDIAGS t0ni EXPERIMENT
###############################################################################
#
#BSUB -q debug
#BSUB -J t0ni_19931101_fc0_2_EARTHDIAGS
#BSUB -oo /gpfs/scratch/bsc32/bsc32627/t0ni/LOG_t0ni/t0ni_19931101_fc0_2_EARTHDIAGS.cmd.out
#BSUB -eo /gpfs/scratch/bsc32/bsc32627/t0ni/LOG_t0ni/t0ni_19931101_fc0_2_EARTHDIAGS.cmd.err
#BSUB -W 01:00
#BSUB -n 1


#
###############################################################################
###################
# Autosubmit header
###################
set -xuve
job_name_ptrn='/gpfs/scratch/bsc32/bsc32627/t0ni/LOG_t0ni/t0ni_19931101_fc0_2_EARTHDIAGS'
echo $(date +%s) > ${job_name_ptrn}_STAT

###################
# Autosubmit job
###################

module purge
module use /gpfs/projects/bsc32/software/suselinux/11/modules/all
module unuse /apps/modules/modulefiles/applications
module unuse /apps/modules/modulefiles/applications_bis
module unuse /apps/modules/modulefiles/compilers
module unuse /apps/modules/modulefiles/tools
module unuse /apps/modules/modulefiles/libraries
module unuse /apps/modules/modulefiles/environment
module unuse /apps/modules/PRACE
set +x
module load Singularity/3.2.0-GCC-8.3.0
set -xuve

#
# General Paths
#
MODEL=ecearth
VERSION=trunk
PROJDIR=/esarchive/autosubmit/t0ni/proj/auto-ecearth3
#
# Experiment description
#
EXPID=t0ni
MEMBER=fc0
START_date=19931101
VERSION=trunk
NEMGRID=ORCA025L75
IFSGRID=T511L91
CMOR_ACTIVITY_ID=CMIP
CMOR_ADD_STARTDATE=FALSE
CMOR_EXP_CUSTOM=FALSE
MODEL_RES=HR
BSC_OUTCLASS=reduced
TEMPLATE=ecearth3
CURRENT_ARCH=nord3

CONTAINER_VERSION="latest"

. $PROJDIR/plugins/utils.sh
. ${PROJDIR}/platforms/${CURRENT_ARCH}/utils.sh
setup_modules_earthdiags
. ${PROJDIR}/plugins/cmorization.sh
create_sub_experiment_id

if [[ -z $sub_experiment_id ]]; then
  ADD_STARTDATE=FALSE
  APPEND_STARTDATE_YEAR_ONLY=""
else
  ADD_STARTDATE=TRUE
  if [[ ${#sub_experiment_id} -eq 5 ]]; then
    APPEND_STARTDATE_YEAR_ONLY=TRUE
  else
    APPEND_STARTDATE_YEAR_ONLY=FALSE
  fi
fi

set -v
get_grid_dims

CMOR_MODEL_ID=EC-EARTH-AOGCM
if [ ${CMOR_MODEL_ID} = "EC-EARTH-AOGCM" ]; then
  dataset="EC-Earth3"
else
  dataset=$(echo $CMOR_MODEL_ID | sed "s/EC-EARTH/EC-Earth3/")
  # eg: EC-EARTH-HR -> EC-Earth3-HR, EC-EARTH-CC -> EC-Earth3-CC , EC-EARTH-AerChem -> EC-Earth3-AerChem, EC-EARTH-Veg-LR -> EC-EARTH-Veg-LR
fi

nem_grid_wol=$(echo ${NEMGRID} | cut -d 'L' -f 1) # without level (wol)
case $VERSION in
'v2.3.0' | 'ecearth-v2.2')
  NEMOVERSION='Ec2.3_O1L42'
  ;;
v3.* | 'trunk')
  case ${MODEL_RES} in
  "HR") NEMOVERSION=Ec3.2_O25${NEMGRID/ORCA025/} ;;
  "LR") NEMOVERSION=Ec3.2_O1${NEMGRID/ORCA1/} ;;
  esac
  ;;
esac

conf_file=/gpfs/scratch/bsc32/bsc32627/t0ni/diags_${EXPID}_${START_date}_${MEMBER}_2.conf
MEMBER_DIGITS=${MEMBER#fc}

cat >${conf_file} <<EOF1
[DIAGNOSTICS]
# Path to the folder where you want to create the temporary files
SCRATCH_DIR = ${TMPDIR}
SKIP_DIAGS_DONE = False
# Root path for the cmorized data to use
DATA_DIR = /esarchive/
# Path to NEMO's mask and grid files needed for CDFTools
CON_FILES = /esarchive/autosubmit/con_files/
# Diagnostics to run, space separated. You must provide for each one the name and the parameters (comma separated) or
# an alias defined in the ALIAS section (see more below). If you are using the diagnostics just to CMORize, leave it
# empty
DIAGS = BASIC_OCEAN BASIC_SEAICE sivolume,Northern_Hemisphere:Southern_Hemisphere
# Frequency of the data you want to use by default. Some diagnostics do not use this value: i.e. monmean always stores
# its results at monthly frequency (obvious) and has a parameter to specify input's frequency.
FREQUENCY = mon
DATA_CONVENTION = CMIP6
# Path to CDFTOOLS binaries
CDFTOOLS_PATH =
# Common scratch folder for the ocean masks.
# This is useful to avoid replicating them for each run at the fat nodes.
# By default is ‘/scratch/Earth/ocean_masks’
SCRATCH_MASKS =
# If true, copies the mesh files regardless of presence in scratch dir
RESTORE_MESHES = False
# Limits the maximum amount of threads used. Default: 0 (no limitation, one per virtual core available)
MAX_CORES = 1

[CMOR]
SKIP_PREPARE = True
# If true, recreates CMOR files regardless of presence. Default = False
FORCE = FALSE
FORCE_UNTAR = FALSE
# If true, CMORizes ocean files.  Default = True
OCEAN_FILES = FALSE
# If true, CMORizes atmosphere files.  Default = True
ATMOSPHERE_FILES = FALSE
CHUNKS = 2
APPEND_STARTDATE = ${ADD_STARTDATE}
APPEND_STARTDATE_YEAR_ONLY = ${APPEND_STARTDATE_YEAR_ONLY}


# The next bunch of parameters are used to provide metadata for the CMOR files
ACTIVITY = CMIP
ASSOCIATED_EXPERIMENT = 
INITIALIZATION_METHOD = 1
PHYSICS_VERSION = 1
SOURCE = ${MODEL}${VERSION}, ocean: Nemo3.6, ifs36r4, lim3
VERSION = latest

[EXPERIMENT]
# Experiments parameters as defined in CMOR standard
INSTITUTE = EC-Earth-Consortium
MODEL = ${dataset}
NAME = piControl
# Model version: Available versions
MODEL_VERSION =${NEMOVERSION-}
ATMOS_GRID = ${GRID_STARTDATE-}
# Atmospheric output timestep in hours
ATMOS_TIMESTEP = 6
# Ocean output timestep in hours
OCEAN_TIMESTEP = 6

EXPID = t0ni
STARTDATES = ${START_date}
MEMBERS = ${MEMBER_DIGITS}
MEMBER_DIGITS = ${#MEMBER_DIGITS}
# set MEMBER_COUNT_START if CMOR_REALIZATION_INDEX is non-sequential - see #1527
#MEMBER_COUNT_START=-2
CHUNK_SIZE = 1
CHUNKS = 2
CHUNK_LIST = 2

# This ALIAS section is a bit different
# Inside this, you can provide alias for frequent diagnostics calls.
# By default, there are some of the diagnostics available at the previous version.
# You can define an alias for one or more diagnostic calls
#
# if an EARTHDIAGS diagnostic support multiple variables, like interpcdo does, they must be separated by ':', not ',' as the later is reserved to separate the different parameters

[ALIAS]
BASIC_OCEAN = regmean,ocean,tos,Global_Ocean:Atlantic_Ocean:Pacific_Ocean:Indian_Ocean:Antarctic_Ocean:Nino3.4 regmean,ocean,thetao:sos,Global_Ocean:Atlantic_Ocean:Pacific_Ocean:Indian_Ocean:Antarctic_Ocean ohclayer,0,300,Global_Ocean:Atlantic_Ocean:Pacific_Ocean:Indian_Ocean:Antarctic_Ocean ohclayer,0,700,Global_Ocean:Atlantic_Ocean:Pacific_Ocean:Indian_Ocean:Antarctic_Ocean ohclayer,0,2000,Global_Ocean:Atlantic_Ocean:Pacific_Ocean:Indian_Ocean:Antarctic_Ocean ohclayer,0,10000,Global_Ocean:Atlantic_Ocean:Pacific_Ocean:Indian_Ocean:Antarctic_Ocean
BASIC_SEAICE = siasiesiv,Northern_Hemisphere:Southern_Hemisphere
BASIC_PISCES = regmean,ocean,epc100:intpp:intdic:fgco2:fgo2,Global_Ocean:Atlantic_Ocean:Pacific_Ocean:Indian_Ocean:Antarctic_Ocean interpcdo,ocean,no3:o2,r360x180,,,,yearly interpcdo,ocean,intpp:intdic,r360x180
BASIC_ATMOS =

EOF1

set +e

export PROJ_LIB=/opt/conda/share/proj/
export SINGULARITY_BINDPATH=/esarchive:/esarchive
CONTAINER="/esarchive/software/containers/earthdiagnostics/earthdiagnostics-${CONTAINER_VERSION}.sif"
newgrp Earth
singularity exec ${CONTAINER} earthdiags -f ${conf_file} -lc DEBUG
SUCCESS=${?}
rm -r ${TMPDIR}
set -e
if [[ ${SUCCESS} -ne 0 ]]; then
  exit ${SUCCESS}
fi
rm -f ${conf_file}

###################
# Autosubmit tailer
###################
set -xuve
echo $(date +%s) >> ${job_name_ptrn}_STAT
touch ${job_name_ptrn}_COMPLETED
exit 0

