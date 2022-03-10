#!/bin/bash

###############################################################################
#                   SAVEIC t0ni EXPERIMENT
###############################################################################
#
#SBATCH --qos=bsc_es
#SBATCH -A bsc32
#
#
#SBATCH --cpus-per-task=48
#0
#SBATCH -n 1
#SBATCH -t 02:00:00
#SBATCH -J t0ni_19931101_fc0_1_SAVEIC
#SBATCH --output=/gpfs/scratch/bsc32/bsc32627/t0ni/LOG_t0ni/t0ni_19931101_fc0_1_SAVEIC.cmd.out
#SBATCH --error=/gpfs/scratch/bsc32/bsc32627/t0ni/LOG_t0ni/t0ni_19931101_fc0_1_SAVEIC.cmd.err
#SBATCH --exclusive
#
###############################################################################
###################
# Autosubmit header
###################
set -xuve
job_name_ptrn='/gpfs/scratch/bsc32/bsc32627/t0ni/LOG_t0ni/t0ni_19931101_fc0_1_SAVEIC'
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
CURRENT_ARCH=marenostrum4
HPCPROJ=bsc32
HPCUSER=bsc32627
EXPID=t0ni
JOBNAME=t0ni_19931101_fc0_1_SAVEIC
ROOTDIR=/gpfs/scratch/bsc32/bsc32627/t0ni
LOGDIR=$ROOTDIR/LOG_$EXPID
PROJDEST=auto-ecearth3
PROJDIR=$ROOTDIR/$PROJDEST
CURRENT_ARCH=marenostrum4
SCRATCH_DIR=/gpfs/scratch
NUMTHREADS=48

#
# General Paths and Conf.
#
MODEL=ecearth
VERSION=trunk
CHUNK=1
# set the mask for padding the chunk number to three digits
chunk_zero_padded=$(printf "%03d\n" ${CHUNK})
Chunk_start_date=19931101
Chunk_end_date=19931130
START_date=19931101
START_date_1=19931031
MEMBER=fc0

# always use intermediate storage so we save to IC repos when SAVE_IC_REPOS=TRUE
# in any case, .tar files are kept in runtime/save_ic/ic, CLEAN will move it to intermediate_storage
USE_INTERMEDIATE_STORAGE=TRUE
IS_TRANSFER=FALSE

export HPCPROJ

. ${PROJDIR}/platforms/${HPCARCH}/configure.sh
load_platform_environment

MODEL_DIR=$MODELS_DIR/$MODEL/$VERSION
BSC_OUTCLASS=reduced
CMIP6_OUTCLASS=
if [[ -n "${BSC_OUTCLASS-}" ]]; then
  outclass=/auto-ecearth3/outclass/${BSC_OUTCLASS-}
elif [[ -n "${CMIP6_OUTCLASS-}" ]]; then
  outclass=ctrl/output-control-files/cmip6/${CMIP6_OUTCLASS}
elif [[ -z "${BSC_OUTCLASS-}" ]] && [[ -z "${CMIP6_OUTCLASS-}" ]]; then
  outclass=ctrl
fi

RUN_dir=$ROOTDIR/$START_date/$MEMBER
SETUP_dir=$PROJDIR/setup/outclass/${outclass}
INIPATH=$RUN_dir/inidata

PATHOUT_IC=${RUN_dir}/runtime/save_ic/ic

TMP_DIR=${RUN_dir}/runtime/save_ic/tmp
mkdir -p $TMP_DIR
cd $TMP_DIR

#
# Model Paths and Conf.
#
ini_data_dir=$MODEL_DIR/inidata

#
# get model config from AS variables
#
#ifs
TEMPLATE_NAME=ecearth3
ifs=""
if [[ "$TEMPLATE_NAME" == ecearth3* ]] || [[ "$TEMPLATE_NAME" == ifs* ]]; then
  ifs="ifs"
fi
[[ "$TEMPLATE_NAME" == ifs3* ]] && amip="amip" || amip=""
[ "FALSE" = TRUE ] && atmnudg="atmnudg" || atmnudg=""
[ "FALSE" = TRUE ] && sppt="sppt" || sppt=""

#nemo
nemo=""
pisces=""
lim3=""
rnfmapper=""
xios=""
if [[ "$TEMPLATE_NAME" == ecearth3* ]] || [[ "$TEMPLATE_NAME" == nemo3* ]]; then
  [[ "a2s5" == *[!\ ]* ]] && start_from_restart=":start_from_restart" || start_from_restart=""
  [ "%OCE_NUDG" = TRUE ] && ocenudg=":ocenudg" || ocenudg=""
  [ "FALSE" = TRUE ] && surfresto=":surfresto" || surfresto=""
  [ "TRUE" = TRUE ] && elpin=":elpin" || elpin=""
  nemo="nemo"${start_from_restart}${ocenudg}${surfresto}${elpin}
  [ "FALSE" = TRUE ] && pisces="pisces" || pisces=""
  lim3="lim3"
  xios="xios:detached"
  rnfmapper="rnfmapper"
fi

#others
[[ "FALSE" == TRUE ]] && lpjg=lpjg:fdbck || lpjg=""
[[ "FALSE" == TRUE ]] && tm5=tm5:chem,o3fb,ch4fb,aerfb || tm5=""
[ "ifs" == "" ] && ifs_veg_source="era20c" || ifs_veg_source="ifs"
if [[ "end_leg" == FALSE ]] || [[ "end_leg" == "" ]]; then save_ic=""; else save_ic="save_ic:end_leg"; fi

config="${ifs} ${amip} ${atmnudg} ${sppt} ${nemo} ${pisces} ${lim3} ${rnfmapper} ${xios} oasis ${lpjg} ${tm5} ${save_ic}"

#
# Dealing with initial condtions (plugin)
#
#. $PROJDIR/plugins/initialization.sh

#
# IFS
#
ifs_lastout=false
ifs_grid=T511L91
ifs_grid_wol=$(echo ${ifs_grid} | cut -d 'L' -f 1) # without level (wol)
ATM_ini=t0ni
ATM_ini_member=fc0

#
# NEMO
#
nem_grid=ORCA025L75
nem_grid_wol=$(echo ${nem_grid} | cut -d 'L' -f 1) # without level (wol)
OCEAN_ini=t0ni
OCEAN_ini_member=fc0

#
# ICE
#
ICE_ini=t0ni
ICE_ini_member=fc0

#
# PISCES
#
PISCES=FALSE
PISCES_ini=t0ni
PISCES_ini_member=fc0
PISCES_OFF=FALSE
PISCES_OFF_DYN=

#
# LPJG
#
LPJG_ini=t0ni
LPJG_ini_member=fc0

#
# TM5
#
TM5_ini=t0ni
TM5_ini_member=fc0
TM5_NLEVS=34

#
# COMMON
#

#
# Prepare stuff for experiment
#

function count_files() {
  local ifiles=$1
  local nifiles=$(ls $ifiles 2>/dev/null) || nifiles=""
  nifiles=($nifiles)
  nifiles=${#nifiles[@]}
  echo $nifiles
}

# Function to create IC files for IFS from special output based on a script from K. Wyser
# copied from EC-Earth libsave_ic.sh with some simplifications
function save_ic_ifs_out2init_as() {
  icdate=${save_ic_date1[$1]}
  #srcdir=$2
  filter_output=true
  grib_filter=${GRIB_BIN_PATH}${GRIB_BIN_PATH:+/}grib_filter

  # temporary directory
  tmpdir=tmp_save_ic
  [ -d $tmpdir ] && rm -rf ${tmpdir}
  mkdir -p $tmpdir

  # first IFS timestep of a month is saved in last output file
  if [[ "$(date -d "${icdate}" +%d)" == "01" ]]; then
    yyyymm=$(date -d "${icdate} - 6 hours" +%Y%m)
  else
    yyyymm=$(date -d "${icdate}" +%Y%m)
  fi

  # find the ICMSH/GG files containing the last timestep, which are in $srcdir/output/ifs/???
  #local ifile_sh=`find $srcdir -name ICMSH${exp_name}+$yyyymm -print -quit`
  #local ifile_gg=`find $srcdir -name ICMGG${exp_name}+$yyyymm -print -quit`
  pwd
  ls
  #ifile_sh=ICMSH${exp_name}+$yyyymm
  #ifile_gg=ICMGG${exp_name}+$yyyymm
  ifile_sh=ICMSH${exp_name}+$yyyymm-out+init
  ifile_gg=ICMGG${exp_name}+$yyyymm-out+init
  if [[ ! -f "$ifile_sh" ]]; then
    info "cannot find ICMSH file $ifile_sh to create initial conditions at $icdate!"
    return 0
  fi
  if [[ ! -f "$ifile_gg" ]]; then
    info "cannot find ICMGG file $ifile_gg to create initial conditions at $icdate!"
    return 0
  fi

  if $filter_output; then
    # define grib filters to separate data for IC from normal output
    # filter_time_init is to define which timestep contains the ICs, currently only one per month is supported
    filter_time_init="dataDate == ${icdate} && dataTime == 0"

    # SH file
    ofile_sh_init=${tmpdir}/sh_init.grb
    filter_sh=${tmpdir}/filter_sh
    write_sh_init="if ( $filter_time_init ) { write \"${ofile_sh_init}\"; }"
    cat >$filter_sh <<EOT
if ( typeOfLevel is "hybrid" ) { ${write_sh_init}; }
EOT

    #GG file
    ofile_gg_init=${tmpdir}/gg_init.grb
    filter_gg=${tmpdir}/filter_gg
    write_gg_init="if ( $filter_time_init ) { write \"${ofile_gg_init}\"; }"
    cat >$filter_gg <<EOT
if ( levelType is "ml" ) { ${write_gg_init}; }
else {
  if ( ! ( levelType is "pl" ) ) { ${write_gg_init}; }
}
EOT

    #run grib_filter on SH and GG files
    $grib_filter $filter_sh $ifile_sh
    $grib_filter $filter_gg $ifile_gg
    if [[ ! -f "$ofile_sh_init" ]]; then
      info "ICMSH file $ifile_sh does not contain data to create initial conditions at $icdate"
      return 0
    fi
    if [[ ! -f "$ofile_gg_init" ]]; then
      info "ICMGG file $ifile_gg does not contain data to create initial conditions at $icdate"
      return 0
    fi

    #rename files
    ifile_sh=${ofile_sh_init}
    ifile_gg=${ofile_gg_init}
  fi # $filter_output

  if [[ ! -f "$ifile_sh" ]]; then
    info "cannot find ICMSH file $ifile_sh to create initial conditions at $icdate!"
    return 0
  fi
  if [[ ! -f "$ifile_gg" ]]; then
    info "cannot find ICMGG file $ifile_gg to create initial conditions at $icdate!"
    return 0
  fi

  #tgtdir=save_ic/$icdate
  tgtdir=.
  ofile_sh=${tgtdir}/ICMSH${exp_name}INIT
  ofile_gg_init=${tgtdir}/ICMGG${exp_name}INIT
  ofile_gg_iniua=${tgtdir}/ICMGG${exp_name}INIUA

  # make sure the output folder is created and delete any existing files
  #[ -d $tgtdir ] && rm -rf ${tgtdir}/* || mkdir -p $tgtdir
  mkdir -p $tgtdir
  rm -f $ofile_sh $ofile_gg_init $ofile_gg_iniua

  cat >${tmpdir}/gf1 <<EOT
if ( typeOfLevel is "hybrid" ) { write "${tmpdir}/shinit.[shortName].[level]"; }
EOT
  $grib_filter ${tmpdir}/gf1 $ifile_sh

  cp -f ${tmpdir}/shinit.lnsp.1 $ofile_sh
  for lev in {1..91}; do
    for var in vo d t; do
      cat ${tmpdir}/shinit.$var.$lev >>$ofile_sh
    done
  done
  cat ${tmpdir}/shinit.z.1 >>$ofile_sh

  cat >${tmpdir}/gf2 <<EOT
write "${tmpdir}/gginit.[shortName]";
EOT
  $grib_filter ${tmpdir}/gf2 $ifile_gg

  for var in stl1 stl2 stl3 stl4 swvl1 swvl2 swvl3 swvl4 sd src skt ci tsn asn \
    rsn sst istl1 istl2 istl3 istl4 chnk lsm sr al aluvp alnip aluvd alnid \
    lai_lv lai_hv sdfor slt sdor isor anor slor lsrh cvh cvl tvh tvl; do
    cat ${tmpdir}/gginit.$var >>$ofile_gg_init
  done

  cat >${tmpdir}/gf3 <<EOT
write "${tmpdir}/gginiua.[shortName].[level]";
EOT
  $grib_filter ${tmpdir}/gf3 $ifile_gg

  #   ${tmpdir}/gginiua.o3 \ check this!
  for lev in {1..91}; do
    for var in q; do
      cat ${tmpdir}/gginiua.$var.$lev >>$ofile_gg_iniua
    done
  done

  for lev in {1..91}; do
    for var in crwc cswc clwc ciwc cc; do
      cat ${tmpdir}/gginiua.$var.$lev >>$ofile_gg_iniua
    done
  done

  # delete tmp folder
  #rm -rf $tmpdir

  echo "save_ic_ifs_out2init ended successfully, results are in $tgtdir"
}

# most of this code copied from runtime script, preserving indentation for easy comparison

# define variables used in the runscript
source $ROOTDIR/librunscript.sh
exp_name=t0ni
nem_time_step_sec=2700 # default, set below to real value if has_config nemo
run_dir=$RUN_dir/runtime
leg_number=${CHUNK}

# Time step settings
if has_config nemo; then
  case "${nem_grid}" in
  ORCA1L*)
    nem_time_step_sec=2700
    lim_time_step_sec=2700
    ;;
  ORCA025L*)
    nem_time_step_sec=900
    lim_time_step_sec=900
    ;;
  *)
    error "Can't set time steps for unknown horizontal grid: ${nem_grid}"
    ;;
  esac
fi

# -----------------------------------------------------------------------------
# *** Extra initial conditions saved during the run
# -----------------------------------------------------------------------------
save_ic_lpjg_days=""
if has_config save_ic; then
  source $ROOTDIR/libsave_ic.sh
  declare -a save_ic_date save_ic_date1 save_ic_sec save_ic_day save_ic_ppt_file save_ic_nemo_ts
  #else
  #     echo "doing nothing"
  #fi

  run_start_date="19931101"
  run_end_date="19931101 + 1 month"
  leg_start_date="19931101"
  leg_end_date="19931130 + 1 day"

  # Regularise the format of the start and end date of the simulation
  run_start_date=$(date -uR -d "${run_start_date}")
  run_end_date=$(date -uR -d "${run_end_date}")
  leg_start_date=$(date -uR -d "${leg_start_date}")
  leg_end_date=$(date -uR -d "${leg_end_date}")

  # Some time variables needed later
  leg_length_sec=$(($(date -d "${leg_end_date}" +%s) - $(date -d "${leg_start_date}" +%s)))
  leg_start_sec=$(($(date -d "${leg_start_date}" +%s) - $(date -d "${run_start_date}" +%s)))
  leg_end_sec=$(($(date -d "${leg_end_date}" +%s) - $(date -d "${run_start_date}" +%s)))
  leg_start_date_yyyymmdd=$(date -u -d "${leg_start_date}" +%Y%m%d)
  leg_start_date_yyyy=$(date -u -d "${leg_start_date}" +%Y)
  leg_end_date_yyyy=$(date -u -d "${leg_end_date}" +%Y)
  leg_end_date_yyyymmdd=$(date -u -d "${leg_end_date}" +%Y%m%d)

  # Initial conditions saved during the run
  do_save_ic=false
  save_ic_custom=false
  has_config save_ic && save_ic_get_config
  # if you do not use an option with save_ic, you must define 'do_save_ic' and
  # 'save_ic_date_offset' here or in ../libsave_ic.sh/save_ic_get_config()
  # with AS runtime, no need to edit the script, set SAVE_IC_OFFSET (and optionally SAVE_IC_COND)
  if $save_ic_custom; then
    [[ "true" == "" ]] && save_ic_cond=true || save_ic_cond='true'
    if eval $save_ic_cond; then do_save_ic=true; else do_save_ic=false; fi
    save_ic_date_offset=()
  fi
  ${do_save_ic} && save_ic_define_vars

  #do_save_ic=end_leg ; [ -z "${do_save_ic}" ] && do_save_ic=false
  SAVE_IC_REPOS=FALSE
  [ -z "${SAVE_IC_REPOS}" ] && SAVE_IC_REPOS=FALSE

  if ${do_save_ic}; then
    # process initial conditions
    for ((i = 0; i < ${#save_ic_date[@]}; i++)); do
      echo =====================================
      outdir=${run_dir}/save_ic/${save_ic_date1[$i]}

      # continue if ICs have already been processed by previous job, and outdir is empty
      # outdir is removed at the end of the loop, so it can only not be empty if SIM was re-run in the meantime
      tarfile="IC_${EXPID}_${START_date}_${MEMBER}_${chunk_zero_padded}_${i}_${Chunk_start_date}-${Chunk_end_date}.tar"
      if [ -f ${PATHOUT_IC}/${tarfile} ] && [ ! -d ${outdir} ]; then
        echo "skipping save_ic for date "${save_ic_date1[$i]}" since it has apparently been done in a previous job"
        continue
      fi

      # make sure we have some output - this might not be a problem if running the lsm template (with only LPJG ICs)
      if [ ! -d $outdir ] ; then
        echo "SAVEIC problem - there are no ICs for date ${save_ic_date1[$i]}"
        [[ "$TEMPLATE_NAME" != "lsm" ]] && exit 1 || mkdir -p ${outdir}
      fi

      ifs_timestamp=${save_ic_date1[$i]}00
      nemo_timestamp=$(date -u -d "${save_ic_date[$i]} -1 day" +%Y%m%d)
      cd ${outdir}
      mkdir -p delete

      echo files for ${save_ic_date1[$i]} are in ${outdir}
      ls $outdir

      echo =====================================

      # IFS files
      if has_config ifs; then
        [ ! -d ifs ] && echo "SAVEIC problem - there are no ICs for IFS for date ${save_ic_date1[$i]}" && exit 1
        cd ifs
        ifiles="ICMGG${exp_name}INIT ICMGG${exp_name}INIUA ICMSH${exp_name}INIT"
        odir=${outdir}/ic/atmos/${ifs_grid}/${ATM_ini}
        ofile=${ATM_ini}_${ATM_ini_member}_${ifs_timestamp}.tar.gz
        # tar and move to temporary ic repository
        # TODO should we remove the full output file (e.g. ICMGGa0fh+195001)
        nifiles=$(count_files "$ifiles")
        # if nothing is found, try and rebuild the ICs with what is left from a previous run
        if [[ $nifiles -ne 3 ]] && ( ! ([[ -f ${odir}/${ofile} ]] && [[ -f ${outdir}/ifs_ok ]])); then
          if [[ $(count_files "ICMGG${exp_name}+??????-out+init ICMSH${exp_name}+??????-out+init") -ge 2 ]]; then
            save_ic_ifs_out2init_as $i
            nifiles=$(count_files "$ifiles")
          fi
        fi

        if [[ $nifiles -eq 3 ]]; then
          echo "IFS ifiles $ifiles found!"
          rm -rf $odir ${outdir}/ifs_ok ${outdir}/tmp_save_ic
          mkdir -p $odir
          tar -czvf ${odir}/${ofile} $ifiles
          touch ${outdir}/ifs_ok
          #echo copied `basename $ofile` to $odir
          mv ${ifiles} ICMGG${exp_name}+??????* ICMSH${exp_name}+??????* ../delete
        elif [[ -f ${odir}/${ofile} ]] && [[ -f ${outdir}/ifs_ok ]]; then
          echo "IFS ofile ${odir}/${ofile} found!"
        else
          echo "SAVEIC problem - IFS ifiles $ifiles not found!"
          exit 1
        fi
        cd ..
      fi

      echo =====================================

      # NEMO files
      if has_config nemo; then
        if [[ ${save_ic_nemo_ts[$i]} -ne -1 ]]; then
          [ ! -d nemo ] && echo "SAVEIC problem - there are no ICs for NEMO for date ${save_ic_date1[$i]}" && exit 1
          cd nemo
          ns=$(printf %08d $((save_ic_nemo_ts[$i])))
          #ftype_=( oce ice )
          #filebase_=( ${exp_name}_${ns}_restart_oce ${exp_name}_${ns}_restart_ice )
          #ofile_=( ${OCEAN_ini}_${OCEAN_ini_member}_${nemo_timestamp}_restart.nc.gz ${ICE_ini}_${ICE_ini_member}_${nemo_timestamp}_restart_ice.nc.gz )
          #odir_=( ${outdir}/ic/ocean/${nem_grid}/${OCEAN_ini} ${outdir}/ic/ice/${nem_grid_wol}_${ICE}/${ICE_ini})
          ftype_=(oce)
          filebase_=(${exp_name}_${ns}_restart_oce)
          ofile_=(${OCEAN_ini}_${OCEAN_ini_member}_${nemo_timestamp}_restart.nc.gz)
          odir_=(${outdir}/ic/ocean/${nem_grid}/${OCEAN_ini})
          if has_config lim3; then
            ftype_+=(ice)
            filebase_+=(${exp_name}_${ns}_restart_ice)
            ofile_+=(${ICE_ini}_${ICE_ini_member}_${nemo_timestamp}_restart_ice.nc.gz)
            odir_+=(${outdir}/ic/ice/${nem_grid_wol}_LIM3/${ICE_ini})
          fi
          if has_config pisces; then
            ftype_+=(trc)
            filebase_+=(${exp_name}_${ns}_restart_trc)
            ofile_+=(${PISCES_ini}_${PISCES_ini_member}_${nemo_timestamp}_restart_trc.nc.gz)
            odir_+=(${outdir}/ic/oceantrc/${nem_grid}/${PISCES_ini})
          fi
          echo filebase_oce: ${filebase_[0]} filebase_ice: ${filebase_[1]}
          for ((j = 0; j < ${#filebase_[@]}; j++)); do
            #ndomain=$3
            filebase=${filebase_[j]}
            ofile=${ofile_[j]}
            odir=${odir_[j]}

            ifiles=(${filebase}_*)
            ndomain=${#ifiles[@]}
            if [ $ndomain -gt 1 ]; then
              rm -f ${outdir}/nemo/${filebase}_ok
              # rebuild restarts
              echo found $ndomain files matching pattern $filebase
              rm -f ${filebase}.nc ${filebase}.nc.gz ${outdir}/nemo/${filebase}_ok
              # TODO rebuild_nemo in scratch dir
              rebuild_nemo -t${NUMTHREADS:-1} $filebase $ndomain
              rm -f nam_rebuild
              gzip ${filebase}.nc
              # move rebuilds to temporary ic repository
              rm -rf $odir
              mkdir -p $odir
              mv ${filebase}.nc.gz ${odir}/${ofile}
              touch ${outdir}/nemo/${filebase}_ok
              #echo copied $ifile to ${odir}/${ofile}
              mv ${filebase}*.nc ../delete
            elif [[ -f ${outdir}/nemo/${filebase}_ok ]] && [[ -f ${odir}/${ofile} ]]; then
              echo ofile ${odir}/${ofile} found!
            else
              echo "SAVEIC problem - did not find NEMO restart files matching pattern $filebase"
              echo "you can put the rebuilt restarts in $odir or the raw restarts in ${outdir}/nemo and re-run SAVEIC"
              exit 1
            fi
          done
          cd ..
        fi
      fi

      echo =====================================

      # oasis files - don't crash if not found since they are not produced in the middle of a CHUNK
      if has_config oasis && [ -d oasis ]; then
        cd oasis
        #ifiles=`ls $oas_rst_files 2>/dev/null || true`
        oas_rst_dir=${outdir}/oasis

        # Restart files for the coupling fields (note 8 character limit in OASIS)
        #   rstas.nc : atmosphere single-category fields
        #   rstam.nc : atmosphere multi-category fields
        #   rstos.nc : ocean single-category fields
        #   rstom.nc : ocean multi-category fields
        oas_rst_ifs_nemo="rstas.nc rstos.nc"

        if has_config ifs nemo; then
          ifiles=$(ls ${oas_rst_ifs_nemo} 2>/dev/null || true)
          odir=${outdir}/ic/coupler/${ifs_grid_wol}-${nem_grid_wol}/${ATM_ini}
          # gzip and move to temporary ic repository
          if [[ $ifiles != "" ]]; then
            echo oasis ifs nemo restart files $ifiles found!
            rm -f ${outdir}/oasis_ok
            rm -rf $odir
            mkdir -p $odir
            for ifile in $(ls $ifiles 2>/dev/null); do
              ofile=${ATM_ini}_${ATM_ini_member}_${ifs_timestamp}_$(basename ${ifile}).gz
              gzip -c $ifile >${odir}/${ofile}
              #echo moved $ifile to ${odir}/${ofile}
              mv ${ifile} ../delete
            done
            touch ${outdir}/oasis_ok
          elif [[ -f ${outdir}/oasis_ok ]]; then
            echo "oasis files already present"
          else
            echo "SAVEIC problem - no oasis ifs nemo restart files found in ${oas_rst_dir} !"
          fi
        fi

        oas_rst_ifs_lpjg="vegin.nc lpjgv.nc"

        if has_config ifs lpjg; then
          ifiles=$(ls ${oas_rst_ifs_lpjg} 2>/dev/null || true)
          odir=${outdir}/ic/coupler/${ifs_grid_wol}/${ATM_ini}
          # gzip and move to temporary ic repository
          if [[ $ifiles != "" ]]; then
            echo oasis restart files $ifiles found!
            rm -f ${outdir}/oasis_ok
            rm -rf $odir
            mkdir -p $odir
            for ifile in $(ls $ifiles 2>/dev/null); do
              ofile=${ATM_ini}_${ATM_ini_member}_${ifs_timestamp}_$(basename ${ifile}).gz
              gzip -c $ifile >${odir}/${ofile}
              #echo moved $ifile to ${odir}/${ofile}
              mv ${ifile} ../delete
            done
            touch ${outdir}/oasis_ok
          else
            echo "SAVEIC problem - no oasis ifs lpjg restart files found in ${oas_rst_dir} !"
          fi
        fi

        if has_config ifs tm5; then
          # get all files in oasis dir except the ones for IFS+NEMO and IFS+LPJG
          ifiles=$(ls 2>/dev/null | grep -v -e ${oas_rst_ifs_nemo// / -e } -e ${oas_rst_ifs_lpjg// / -e })
          odir=${outdir}/ic/coupler/${ifs_grid_wol}-TM5-${TM5_NLEVS}-levels/${ATM_ini}
          # gzip and move to temporary ic repository
          if [[ $ifiles != "" ]]; then
            echo "oasis ifs tm5 restart files $ifiles found!"
            rm -f ${outdir}/oasis_ok
            rm -rf $odir
            mkdir -p $odir
            for ifile in $(ls $ifiles 2>/dev/null); do
              ofile=${ATM_ini}_${ATM_ini_member}_${ifs_timestamp}_$(basename ${ifile}).gz
              gzip -c $ifile >${odir}/${ofile}
              #echo moved $ifile to ${odir}/${ofile}
              mv ${ifile} ../delete
            done
            touch ${outdir}/oasis_ok
          else
            echo "SAVEIC problem - no oasis ifs tm5 restart files found in ${oas_rst_dir} !"
          fi
        fi

        cd ..
      fi

      echo =====================================

      # LPJG
      if has_config lpjg; then
        # end-of-leg restarts are in restart/lpjg/???, intermediate restarts are in save_ic/ folder
        if [[ $leg_end_date_yyyymmdd == ${save_ic_date1[$i]} ]]; then
          full_lpjg_restart=false
          rstdir=${run_dir}/restart/lpjg/$( printf "%03d\n" ${CHUNK} )
        else
          full_lpjg_restart=true
          rstdir=${outdir}/lpjg
        fi
        ofile=${LPJG_ini}_${LPJG_ini_member}_${ifs_timestamp}_lpjg.tgz
        odir=${outdir}/ic/lpjg/${ifs_grid_wol}/${LPJG_ini}
        if [[ -f ${outdir}/lpjg_ok && -f ${odir}/${ofile} ]] ; then
          echo "lpjg files already present"
        elif [[ -d $rstdir ]] ; then
          rm -f ${outdir}/lpjg_ok
          mkdir -p $odir
          cd $rstdir
          #tar -czvf ${odir}/${ofile} *
          # use pigz (parallel gzip) instead of gzip since these files are quite big
          tar -cvf - * | pigz -p ${NUMTHREADS} > ${odir}/${ofile}
          cd -
          ${full_lpjg_restart} && rm -rf ${rstdir}
          touch ${outdir}/lpjg_ok
        else
          echo "SAVEIC problem - no lpjg restart files found in ${rstdir}"
          exit 1
        fi
      fi #LPJG

      echo =====================================

      # TM5 - only get ICs if this is the last timestep of the leg
      if has_config tm5 && [[ $leg_end_date_yyyymmdd == ${save_ic_date1[$i]} ]]; then
        [ ! -d tm5 ] && echo "SAVEIC problem - there are no ICs for TM5 for date ${save_ic_date1[$i]}" && exit 1
        cd tm5
        ifiles=$(ls TM5_restart_${leg_end_date_yyyymmdd}_0000_glb300x200.nc save_${leg_end_date_yyyymmdd}00_glb300x200.hdf 2>/dev/null || true)
        odir=${outdir}/ic/tm5/${TM5_ini}
        # gzip and move to temporary ic repository
        if [[ $ifiles != "" ]]; then
          echo tm5 restart files $ifiles found!
          rm -f ${outdir}/tm5_ok
          rm -rf $odir
          mkdir -p $odir
          for ifile in $(ls $ifiles 2>/dev/null); do
            ofile=${TM5_ini}_${TM5_ini_member}_${ifs_timestamp}_$(basename ${ifile}).gz
            gzip -c $ifile >${odir}/${ofile}
            #echo moved $ifile to ${odir}/${ofile}
            mv ${ifile} ../delete
          done
          touch ${outdir}/tm5_ok
        elif [[ -f ${outdir}/tm5_ok ]]; then
          echo "tm5 files already present"
        else
          echo "SAVEIC problem - no tm5 restart files found"
          exit 1
        fi
        cd -
      fi #TM5

      echo =====================================

      # exit if no output is found
      if [ ! -d ${outdir}/ic ]; then
        echo "SAVEIC problem! no files in ${outdir}/ic"
        exit 1
      fi

      #Apply proper permissions
      chmod 775 $(find ${outdir}/ic/ -type d)
      chmod 654 $(find ${outdir}/ic/ -type f)

      # optionally copy files to IC repository
      if [[ $SAVE_IC_REPOS == "TRUE" ]]; then
        # TODO test this on CCA
        if [[ "${HPCARCH}" = "ecmwf-xc40" ]]; then
          echo "SAVE_IC_REPOS = TRUE not supported for platform ${HPCARCH}"
          exit 1
        fi
        # copy files to IC_DIR
        pathout_ic=${IC_DIR}
        # move each file to IC repository in the proper directory
        for ifile in $( (cd ${outdir}/ic && find * -type f)); do
          fdir=$(dirname ${ifile})
          # Create the folder && apply permissions in case we are overwritting files in the target file
          # todo a platform-dependent function/option for this
          target_group=bsc32
          sg ${target_group} "mkdir -p -m775 ${pathout_ic}/${fdir}"
          cp -f ${outdir}/ic/${ifile} ${pathout_ic}/${fdir}
          chmod 744 ${pathout_ic}/${ifile}
          echo moved ${ifile} to ${pathout_ic}/${fdir}
        done
      fi

      # create a tarfile which can be untarred later in the IC repository
      pushd .
      cd ${outdir}/ic
      tar -cvf ../${tarfile} *
      chmod 774 ../${tarfile}
      cd ..

      # move to temp folder, clean/transfer will transfer to /esarchive
      mkdir -p ${PATHOUT_IC}
      mv -f ${tarfile} ${PATHOUT_IC}
      echo moved ${tarfile} to ${PATHOUT_IC}

      popd

      # cleanup, this assumes that files have been copied correctly
      rm -rf ${outdir}

    done #for

  else
    echo "doing nothing"
  fi

else
  echo "doing nothing"
fi

###################
# Autosubmit tailer
###################
set -xuve
echo $(date +%s) >> ${job_name_ptrn}_STAT
touch ${job_name_ptrn}_COMPLETED
exit 0

