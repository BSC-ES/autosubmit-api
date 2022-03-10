#!/bin/bash

###############################################################################
#                   CMORATM t0ni EXPERIMENT
###############################################################################
#
#SBATCH --qos=bsc_es
#SBATCH -A bsc32
#
#
#SBATCH --cpus-per-task=1
#0
#SBATCH -n 1
#SBATCH -t 3:00:00
#SBATCH -J t0ni_19931101_fc0_1_CMORATM
#SBATCH --output=/gpfs/scratch/bsc32/bsc32627/t0ni/LOG_t0ni/t0ni_19931101_fc0_1_CMORATM.cmd.out
#SBATCH --error=/gpfs/scratch/bsc32/bsc32627/t0ni/LOG_t0ni/t0ni_19931101_fc0_1_CMORATM.cmd.err
#SBATCH --exclusive
#
###############################################################################
###################
# Autosubmit header
###################
set -xuve
job_name_ptrn='/gpfs/scratch/bsc32/bsc32627/t0ni/LOG_t0ni/t0ni_19931101_fc0_1_CMORATM'
echo $(date +%s) > ${job_name_ptrn}_STAT

###################
# Autosubmit job
###################

set -xuve
#
# Architecture
#

CURRENT_ARCH=marenostrum4
EXPID=t0ni
ROOTDIR=/gpfs/scratch/bsc32/bsc32627/t0ni
PROJDEST=auto-ecearth3
PROJDIR=$ROOTDIR/$PROJDEST
BSC_OUTCLASS=reduced
CMIP6_OUTCLASS=
CMOR_REALIZATION_INDEX=""
[[ "FALSE" == TRUE ]] && LPJG=TRUE || LPJG=FALSE

export HPCPROJ

#
# General Paths and Conf.
#
MODEL=ecearth
MODEL_RES=HR
VERSION=trunk
#MODEL_DIR=${MODELS_DIR}/$MODEL/$VERSION
START_date=19931101
MEMBER=fc0
SCRATCH_DIR=/gpfs/scratch
CMOR_ACTIVITY_ID=CMIP
CMOR_EXP=piControl
CMOR_MODEL_ID=EC-EARTH-AOGCM
TEMPLATE_NAME=ecearth3
TASKTYPE=CMORATM
#
# Chunk Management
#
CHUNK=1
Chunk_start_date=19931101
Chunk_end_date=19931130
Chunk_last=FALSE
# In months
CHUNKSIZE=1

RUN_dir=${ROOTDIR}/${START_date}/${MEMBER}/runtime
output_dir_atm=${RUN_dir}/output/ifs/$(printf "%03d\n" ${CHUNK})
output_dir_oce=${RUN_dir}/output/nemo/$(printf "%03d\n" ${CHUNK})
output_dir_lpjg=${RUN_dir}/output/lpjg/$(printf "%03d\n" ${CHUNK})
output_dir_tm5=${RUN_dir}/output/tm5/$(printf "%03d\n" ${CHUNK})

#
# Cmorization
#
NFRP=6
NEMO_resolution=ORCA025L75
IFS_resolution=T511L91
PROJ_TYPE=STANDARD
CMOR_ADD_STARTDATE=FALSE
PRODUCTION_EXP=FALSE
CMORIZATION=TRUE
CMOR_EXP_CUSTOM=FALSE

#####################################################################################################################
# Globals: PROJDIR, CURRENT_ARCH, CMIP6_OUTCLASS, BSC_OUTCLASS, MODEL_RES, NEMO_resolution, IFS_resolution, MEMBER,
#         Chunk_start_date, CMOR_EXP_CUSTOM, PATH_FLAGS, CMOR_ACTIVITY_ID, CMOR_MODEL_ID
# Arguments:
#
# Returns:
#   None
# Purpose: Prepare que environment for running the cmorization process, this method is common to all type of models.
#          it creates the neccesary folders and defines the list of vars to be used depending of the defined OUTCLASS
#          type
#
#####################################################################################################################
function setenvcmor() {

  set +ue
  . ${PROJDIR}/platforms/${CURRENT_ARCH}/configure.sh
  load_modules_ece2cmor
  export PYTHONPATH=${PROJDIR}/ece2cmor/:$PYTHONPATH
  export PYTHONPATH=${PROJDIR}/ece2cmor/ece2cmor3/scripts:$PYTHONPATH
  define_paths_ece2cmor
  . ${PROJDIR}/plugins/cmorization.sh

  # set varlist
  if [[ -z ${CMIP6_OUTCLASS-} && -z ${BSC_OUTCLASS-} ]]; then
    echo "Classic outclass can't be CMORIZED"
    exit 1
  fi

  if [[ -n "${CMIP6_OUTCLASS}" ]] && [[ -n "${BSC_OUTCLASS}" ]]; then
    echo "only one OUTCLASS should be set"
    exit 1
  fi

  if [[ -n "${BSC_OUTCLASS-}" ]] && [[ -z "${CMIP6_OUTCLASS-}" ]]; then
    REPLACEMENT_TABLES=$(find ${PROJDIR}/outclass/${BSC_OUTCLASS} -name "CMIP6*.json" -type f)
    if [[ -z ${REPLACEMENT_TABLES} ]]; then
      echo "No CMIP6 tables have been replaced."
    else
      cp ${PROJDIR}/outclass/${BSC_OUTCLASS}/CMIP6*json ${PROJDIR}/ece2cmor/ece2cmor3/resources/tables/.
    fi
    EXCEL_FILE=$(echo ${PROJDIR}/outclass/${BSC_OUTCLASS}/*varlist*.json)
  fi

  if [[ -n "${CMIP6_OUTCLASS}" ]] && [[ -z "${BSC_OUTCLASS}" ]]; then
    if [[ ${CMIP6_OUTCLASS} == "OMIP/cmip6-experiment-OMIP-omip1" ]] && [[ ${CMOR_MODEL_ID} == "EC-EARTH-AOGCM" ]]; then
      EXCEL_FILE=$(echo ${ROOTDIR}/ctrl/output-control-files/cmip6/${CMIP6_OUTCLASS}/cmip6-data-request-varlist-OMIP-omip1-EC-EARTH-CC.json)
    elif [[ ${CMIP6_OUTCLASS} == "ScenarioMIP/EC-EARTH-CC/cmip6-experiment-ScenarioMIP-ssp245" ]] && [[ ${CMOR_MODEL_ID} == "EC-EARTH-AOGCM" ]]; then
      EXCEL_FILE=$(echo ${ROOTDIR}/ctrl/output-control-files/cmip6/${CMIP6_OUTCLASS}/cmip6-data-request-varlist-ScenarioMIP-ssp245-EC-EARTH-CC.json)
    else
      EXCEL_FILE=$(echo ${ROOTDIR}/ctrl/output-control-files/cmip6/${CMIP6_OUTCLASS}/*-varlist-*-*-*${CMOR_MODEL_ID}.json)
    fi
  fi
  ##

  if [[ ${MODEL_RES} == "LR" ]]; then
    MODEL_NAME="EC-Earth3"
  elif [[ ${MODEL_RES} == "HR" ]]; then
    MODEL_NAME="EC-Earth3-HR"
  elif [[ ${MODEL_RES} == "VHR" ]]; then
    MODEL_NAME="EC-Earth3-VHR"
  else
    echo "Wrong MODEL_RES" $MODEL_RES "is not in LR or HR or VHR"
    exit
  fi

  grid=$(echo $NEMO_resolution | cut -f1 -d "L")$(echo $IFS_resolution | cut -f1 -d "L")
  member_index=$(echo $((10#$(echo ${MEMBER} | cut -c3-) + 1)))
  cmor_realization_indexing

  startyear=$(echo $Chunk_start_date | cut -c1-4)
  startmonth=$(echo $Chunk_start_date | cut -c5-6)
  [[ ! -f $ROOTDIR/LOG_$EXPID/${EXPID}_CMOR_DATASETVERSION ]] && echo v$(date +%Y%m%d) >$ROOTDIR/LOG_${EXPID}/${EXPID}_CMOR_DATASETVERSION
  export cmordatasetversion=$(cat $ROOTDIR/LOG_${EXPID}/${EXPID}_CMOR_DATASETVERSION)
  mkdir -p ${RUN_dir}/cmor_outputs
  if [[ ${CMOR_EXP_CUSTOM} == "TRUE" ]]; then
    if [[ -z $( grep $CMOR_EXP ${PROJDIR}/ece2cmor/ece2cmor3/resources/tables/CMIP6_CV.json ) ]] || [[ -z $( grep $START_date ${PROJDIR}/ece2cmor/ece2cmor3/resources/tables/CMIP6_CV.json ) ]] ; then
      python ${PROJDIR}/plugins/cmor_pythonsetup.py --projdir $PROJDIR --template_name $TEMPLATE_NAME --expid $EXPID --cmor_exp $CMOR_EXP --cmor_add_startdate $CMOR_ADD_STARTDATE --startdate $START_date
    fi
  fi

  #TODO override defaults this should come from proj.conf
  #activity_id=CMIP
  activity_id=$CMOR_ACTIVITY_ID
  model_id=$CMOR_MODEL_ID

  mkdir -p ${RUN_dir}/cmor_outputs
  # path for cmor jobs flags/signaling
  export PATH_FLAGS=${RUN_dir}/flags
  if [[ ! -d ${PATH_FLAGS} ]]; then
    mkdir -p ${PATH_FLAGS}
  fi

  set -ue

}

#####################################################################################################################
# Globals: CMOR_ACTIVITY_ID, RUN_dir, CMOR_EXP, MEMBER, CMOR_EXP_CUSTOM, BSC_OUTCLASS, CMOR_ADD_STARTDATE, START_date
# Arguments:
#   None
# Returns:
#   None
# Purpose: based on the metadadata ( that depends of the type of cmorization to be run ) the cmor templates are generated
#
#####################################################################################################################
function cmor_gen_templates() {
  . ${PROJDIR}/plugins/cmorization.sh
  create_sub_experiment_id
  # cd into the metadata dir to avoid clashes with other cmor jobs
  metadata_dir=${RUN_dir}/../tmp/cmor/metadata-${CMOR_ACTIVITY_ID}-${component}-${MEMBER}-${startyear}${startmonth}
  mkdir -p ${metadata_dir}
  cd ${metadata_dir}
  ${PROJDIR}/ece2cmor/ece2cmor3/scripts/modify-metadata-template.sh ${activity_id} ${CMOR_EXP} ${model_id} ${PROJDIR}/ece2cmor/ece2cmor3/resources/metadata-templates/cmip6-CMIP-piControl-metadata-template.json
  metadata_template_oce="${metadata_dir}/metadata*-${activity_id}-${CMOR_EXP}-${model_id}-nemo-template.json"
  metadata_template_atm="${metadata_dir}/metadata*-${activity_id}-${CMOR_EXP}-${model_id}-ifs-template.json"
  metadata_template_lpjg="${metadata_dir}/metadata*-${activity_id}-${CMOR_EXP}-${model_id}-lpjg-template.json"
  metadata_template_tm5="${metadata_dir}/metadata*-${activity_id}-${CMOR_EXP}-${model_id}-tm5-template.json"

  for f in ${metadata_dir}/*${CMOR_EXP}*-*-template.json; do
    sed -i 's/"realization_index":            "1",/"realization_index":            "'${realization_index}'",/g' $f
    sed -i '10 a\    "outpath":                      "'${RUN_dir}'/cmor_outputs/cmor_'${component}'_'${CHUNK}'",' $f
    sed -i '11 a\    "output_path_template":                      "<activity_id><institution_id><source_id><experiment_id><variant_label><table><variable_id><grid_label><'$cmordatasetversion'>",' $f
    sed -i '15 a\    "variant_info":                 "forcing: Nat.Ant. Member generated from autosubmit member '${MEMBER}'",' $f
    if [[ -n $sub_experiment_id ]]; then
      sed -i 's/"sub_experiment_id":            "none",/"sub_experiment_id":            "'${sub_experiment_id}'",/g' $f
    fi
  done
}

#####################################################################################################################
# Globals: TASKTYPE, MEMBER, CHUNK, EXPID, EXCEL_FILE, RUN_dir, PROJDIR, PATH_FLAGS,
# Arguments:
#
# Returns:
#   None
# Purpose: Main cmorization function, common to most models
#
#####################################################################################################################
function cmor() {
  component=$(echo ${TASKTYPE#CMOR} | tr '[:upper:]' '[:lower:]')
  skip_alevel_vars=""
  if [[ ${component} == "oce" ]]; then
    cmor_model="nemo"
  elif [[ ${component} == "atm" ]]; then
    cmor_model="ifs"
    if [[ "$CMIP6_OUTCLASS" != *"pextra"* ]]; then
      skip_alevel_vars="--skip_alevel_vars"
    fi
  else
    cmor_model=${component}
  fi
  output_dir=output_dir_${component}
  metadata_template=metadata_template_${component}

  cmor_gen_templates
  cd ${metadata_dir}
  find . -type f \! -name "*${cmor_model}*" -delete

  tmpdir=${RUN_dir}/../tmp/cmor/tmp-${component}-${MEMBER}-${startyear}${startmonth}
  rm -rf $tmpdir
  mkdir -p $tmpdir
  rm -rf ${RUN_dir}/cmor_outputs/cmor_${component}_${CHUNK}
  mkdir -p ${RUN_dir}/cmor_outputs/cmor_${component}_${CHUNK}

  cd ${PROJDIR}/ece2cmor/ece2cmor3
  ./ece2cmor.py --${cmor_model} --exp ${EXPID} --meta ${!metadata_template} --tmpdir ${tmpdir} --varlist ${EXCEL_FILE} ${!output_dir} $skip_alevel_vars
  rm -rf ${tmpdir}
  #fx management
  if [[ $(printf "%03d\n" ${CHUNK}) == '001' ]]; then
  #if 1st chunk and lsm, add fx areacella from the templates directory
    if [[ $component == "lpjg" ]] && [[ -n $IFS_resolution ]] ; then
      if [ ${CMOR_MODEL_ID} = "EC-EARTH-AOGCM" ]; then
        dataset="EC-Earth3"
      else
        dataset=$(echo $CMOR_MODEL_ID | sed "s/EC-EARTH/EC-Earth3/")
        # eg: EC-EARTH-HR -> EC-Earth3-HR, EC-EARTH-CC -> EC-Earth3-CC , EC-EARTH-AerChem -> EC-Earth3-AerChem, EC-EARTH-Veg-LR -> EC-EARTH-Veg-LR
      fi
      CMORFILENAME=areacella_fx_${dataset}_${CMOR_EXP}_r${member_index}i1p1f1_gr.nc
      cmordatasetversion=$(cat $ROOTDIR/LOG_${EXPID}/${EXPID}_CMOR_DATASETVERSION) 
      CMOR_FX_DIR=${RUN_dir}/cmor_outputs/cmor_${component}_${CHUNK}/${CMOR_ACTIVITY_ID}/EC-Earth-Consortium/${dataset}/${CMOR_EXP}/r${member_index}i1p1f1/fx/areacella/gr/$cmordatasetversion
      mkdir -p $CMOR_FX_DIR
      [[ ! -f ${CMOR_FX_DIR}/$CMORFILENAME ]] && cp ${PROJDIR}/fx_files/${IFS_resolution}/areacella_fx_EC-Earth3-CC_piControl_r0i0p0f0_gr.nc ${CMOR_FX_DIR}/$CMORFILENAME
    fi
  else
  #if not first chunk, remove the files (because already generated at chunk 1
    find ${RUN_dir}/cmor_outputs/cmor_${component}_${CHUNK} -type d -name "*fx" -exec rm -rf {} +
  fi
  for f in $( find ${RUN_dir}/cmor_outputs/cmor_${component}_${CHUNK} -type f -name "*Eyr*nc"); do
    if [[ ! -z $(ncdump -h $f | grep "frequency = \"yrPt" ) ]]; then
      year=$(basename $f | cut -f7 -d"_" | cut -c1-4)
      cdo settaxis,${year}-12-31,23:00 $f ${f}2
      cdo setreftime,1850-01-01,00:00 ${f}2 $f
      rm ${f}2 
    fi
  done
  # set the cmor process to complete
  touch ${PATH_FLAGS}/cmor_${component}_${CHUNK}
}

#
#####################################################################################################################
# Globals: RUN_dir, CHUNK, cmor_dir, component
# Arguments:
#   None
# Returns:
#   None
# Purpose: Function to clean the cmorisation output by looking for .copy files and files with corrupted names.
#            When running cmorisation twice in the same CHUNK,  some files might end up duplicated or with a bad name.
#            This funciton cleans the cmor_${CHUNK} before it's transferred.
#
#####################################################################################################################
function clean_cmor() {
  cmor_dir=${RUN_dir}/cmor_outputs/cmor_${component}_${CHUNK}
  cd $cmor_dir
  if [[ ${component} == "lpjg" ]]; then
    for f in $(find $cmor_dir -type f -name "*nc"); do
      [[ ! -z $(ncdump -h $f | grep "time:units = \"days since 1850-01-01\" ;") ]] && ncatted -O -a units,time,m,c,"days since 1850-01-01 00:00:00" $f
    done
  fi
  find . -name "*.copy*" -type f -delete
}

#
#####################################################################################################################
# Globals: RUN_dir, CHUNK, Chunk_start_date, Chunk_end_date, cmor_dir, component
# Arguments:
#   None
# Returns:
#   None
# Purpose: Function to check number of timesteps of 6hourly files. This is a quick check previous to NCTIME which is run after transfer to esarchive
#
#####################################################################################################################
function check_cmor_timestep() {
  cmor_dir=${RUN_dir}/cmor_outputs/cmor_${component}_${CHUNK}
  cd $cmor_dir
  #Check one directory of each frequency
  for freq in 6hr day mon; do
    dir_to_check=""
    for dir_to_check in $(find $cmor_dir -mindepth 9 -type d | grep -E "$freq" | head -1); do
      if [[ ! -z $dir_to_check ]]; then
        if [[ ! -z $(echo $dir_to_check | grep 6hr) ]]; then
          expected_timesteps=$((($(date -u -d $Chunk_end_date +%s) - $(date -u -d $Chunk_start_date +%s)) / 21600 + 4))
        elif [[ ! -z $(echo $dir_to_check | grep day) ]]; then
          expected_timesteps=$((($(date -u -d $Chunk_end_date +%s) - $(date -u -d $Chunk_start_date +%s)) / 86400 + 1))
        else
          expected_timesteps=$(($CHUNKSIZE))
        fi
        cd $dir_to_check
        number_of_timesteps=$(
          for f in *; do
            cdo -s ntime $f
          done | awk '{sum += $1} END {print sum}'
        )
        if [[ $number_of_timesteps != $expected_timesteps ]]; then
          echo "Found $number_of_timesteps timesteps in $dir_to_check, when we were expecting $expected_timesteps. Something might have gone wrong with CMORization. Check the outputs."
          exit 1
        fi
        echo $freq $dir_to_check $expected_timesteps $number_of_timesteps
      fi
    done
  done
}
#####################################################################################################################
# Globals: MEMBER, CHUNK, PROJDIR, MODEL_RES, USER_JASMIN,
# Arguments:
#   None
# Returns:
#   None
# Purpose: transfer jasmin log files to dedicated server
#
#####################################################################################################################
function transfer_cmor_jasmin() {
  member_index=$(echo $((10#$(echo ${MEMBER} | cut -c3-) + 1)))
  DATE=${DATE:-$(date -u +%Y%m%d_%H%M%S)}
  SRCDIR=${PROJDIR}/ece2cmor/ece2cmor3/cmor_${CHUNK}_${MEMBER}
  SERVER=jasmin-xfer2.ceda.ac.uk
  TGTDIR=/group_workspaces/jasmin2/primavera2/upload/EC-Earth-Consortium/EC-Earth-3-${MODEL_RES}/incoming/v$DATE
  cd $SRCDIR
  rsync -rvz --omit-dir-times --rsh="ssh -c arcfour" $SRCDIR/ ${USER_JASMIN}@${SERVER}:${TGTDIR}
}
######################################################
#
# MAIN
#
######################################################

if [[ ${CMORIZATION} == '' ]] || [[ ${CMORIZATION} == 'TRUE' ]]; then
  # prepare environment
  setenvcmor
  # execute cmorization for the related component
  cmor
  # clean garbage
  clean_cmor
  #check number of timesteps of cmor 6hourly output
  check_cmor_timestep
else
  echo "CMORIZATION is disabled but the job ${TASKTYPE} is still in the job list of the experiment, please remove it if you are not using it"
fi

###################
# Autosubmit tailer
###################
set -xuve
echo $(date +%s) >> ${job_name_ptrn}_STAT
touch ${job_name_ptrn}_COMPLETED
exit 0

