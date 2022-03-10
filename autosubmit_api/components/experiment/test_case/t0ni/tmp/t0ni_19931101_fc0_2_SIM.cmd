#!/bin/bash

###############################################################################
#                   SIM t0ni EXPERIMENT
###############################################################################
#
#SBATCH --qos=bsc_es
#SBATCH -A bsc32
#
#
#
#SBATCH --cpus-per-task=1
#SBATCH -n 2400
#SBATCH -t 2:00:00
#SBATCH -J t0ni_19931101_fc0_2_SIM
#SBATCH --output=/gpfs/scratch/bsc32/bsc32627/t0ni/LOG_t0ni/t0ni_19931101_fc0_2_SIM.cmd.out
#SBATCH --error=/gpfs/scratch/bsc32/bsc32627/t0ni/LOG_t0ni/t0ni_19931101_fc0_2_SIM.cmd.err

#
###############################################################################
###################
# Autosubmit header
###################
set -xuve
job_name_ptrn='/gpfs/scratch/bsc32/bsc32627/t0ni/LOG_t0ni/t0ni_19931101_fc0_2_SIM'
echo $(date +%s) > ${job_name_ptrn}_STAT

###################
# Autosubmit job
###################

#!/usr/bin/env bash

set -xuve

cd /gpfs/scratch/bsc32/bsc32627/t0ni

# librunscript defines some helper functions
source ./librunscript.sh

# =============================================================================
# *** BEGIN User configuration
# =============================================================================

# -----------------------------------------------------------------------------
# *** General configuration
# -----------------------------------------------------------------------------
# Component configuration (for syntax of the $config variable, see librunscript.sh)
#
# Currently maintained:
#     config="ifs amip oasis"                            # "GCM forced-SST" : IFS + AMIP
#     config="ifs amip oasis lpjg:fdbck"                 # "Veg"            : forced-GCM + LPJ-Guess
#     config="ifs amip oasis tm5:chem,o3fb,ch4fb,aerfb"  # "AerChem"        : forced-GCM + TM5
#
#     config="ifs nemo lim3 rnfmapper xios:detached oasis"                                 # "GCM"     : IFS+NEMO
#     config="ifs nemo lim3 rnfmapper xios:detached oasis lpjg:fdbck"                      # "Veg"     : GCM+LPJ-Guess
#     config="ifs nemo lim3 rnfmapper xios:detached oasis pisces lpjg:fdbck tm5:co2,co2fb" # "C-cycle" : GCM+LPJG+TM5
#     config="ifs nemo lim3 rnfmapper xios:detached oasis tm5:chem,o3fb,ch4fb,aerfb"       # "AerChem" : GCM+TM5
#
#     config="ifs nemo pisces lim3 rnfmapper xios:detached oasis"     # "GCM"     : IFS+NEMO+PISCES
#

#config="ifs nemo lim3 rnfmapper xios:detached oasis lpjg:fdbck tm5:co2"

# get config from autosubmit variables

#ifs
ifs="ifs"
TEMPLATE_NAME=ecearth3
[[ "$TEMPLATE_NAME" = ifs3* ]] && amip="amip" || amip=""
[ "FALSE" = TRUE ] && atmnudg="atmnudg" || atmnudg=""
[ "FALSE" = TRUE ] && sppt="sppt" || sppt=""

#nemo
nemo=""; pisces=""; lim3=""; rnfmapper=""; xios=""
[[ "$TEMPLATE_NAME" = nemo3* ]] && error "ece-esm.sh runscript does not support nemo only!"
if [[ "$TEMPLATE_NAME" = ecearth3* ]];
then
  [[ "a2s5" = *[!\ ]* ]] && start_nemo_from_restart=":start_from_restart" || start_nemo_from_restart=""
  [[ "" = *[!\ ]* ]] && start_pisces_from_restart=":start_from_restart" || start_pisces_from_restart=""
  [ "FALSE" = TRUE ] && ocenudg=":ocenudg" || ocenudg=""
  [ "FALSE" = TRUE ] && surfresto=":surfresto" || surfresto=""
  [ "TRUE" = TRUE ] && elpin=":elpin" || elpin=""
  nemo="nemo"${start_nemo_from_restart}${ocenudg}${surfresto}${elpin}
  [ "FALSE" = TRUE ] && pisces="pisces"${start_pisces_from_restart} || pisces=""
  lim3="lim3"; xios="xios:detached"; rnfmapper="rnfmapper"
fi

#others
CMIP5_RCP=0
[[ "FALSE" = TRUE ]] && lpjg=lpjg:fdbck || lpjg=""
[[ "FALSE" = TRUE ]] && tm5=tm5:chem,o3fb,ch4fb,aerfb || tm5=""
[ "TRUE" = TRUE ] && elpin=":elpin" || elpin=""
[ "ifs" == "" ]  && ifs_veg_source="era20c" || ifs_veg_source="ifs"
if [[ "end_leg" = FALSE ]] || [[ "end_leg" = "" ]] ; then save_ic="" ; else save_ic="save_ic:end_leg" ; fi

config="${ifs} ${amip} ${atmnudg} ${sppt} ${nemo} ${pisces} ${lim3} ${rnfmapper} ${xios} oasis ${lpjg} ${tm5} ${save_ic}"

# minimum sanity
has_config amip nemo && error "Cannot have both nemo and amip in config!!"
! has_config ifs && error "The ESM script requires ifs in config"

# Experiment name (exactly 4 letters!)
export exp_name=t0ni

# Simulation start and end date. Use any (reasonable) syntax you want.
run_start_date="19931101"
# define run_start_date_as with proper format e.g. 19900101
export run_start_date_as=$(date -u -d "${run_start_date}" +%Y%m%d)
run_end_date="19931201 + 1 month"

# Simulation member. Use any (reasonable) syntax you want.
export member="fc0"

# Set $force_run_from_scratch to 'true' if you want to force this run to start
# from scratch, possibly ignoring any restart files present in the run
# directory. Leave set to 'false' otherwise.
# NOTE: If set to 'true' the run directory $run_dir is cleaned!
CHUNK=2
force_run_from_scratch=TRUE
force_run_from_scratch=${force_run_from_scratch:-false}
force_run_from_scratch=$(echo ${force_run_from_scratch} | tr '[:upper:]' '[:lower:]')
# we only apply this for the first chunk
if ${force_run_from_scratch} && [[ "${CHUNK}" != "1" ]] ; then
  force_run_from_scratch=false
fi

# Resolution (TM5 resolution is set at compilation)
ifs_grid=T511L91
nem_grid=ORCA025L75

# Restart frequency. Use any (reasonable) number and time unit you want.
# For runs without restart, leave this variable empty
rst_freq="1 month"

# Number of restart legs to be run in one go
run_num_legs=1

# Coupling frequencies
has_config ifs tm5  && cpl_freq_atm_ctm_hrs=6
has_config ifs lpjg && cpl_freq_atm_lpjg_hrs=24

# Don't change the coupling frequency because UPDCLIE (where SST and SIC
# are updated) is called every 24 hours (hardcoded in ifs-36r4/src/ifs/utility/updtim.F90)
has_config amip && cpl_freq_amip_sec=86400

# Directories
start_dir=${PWD}
ctrl_file_dir=${start_dir}/ctrl
output_control_files_dir=${start_dir}//auto-ecearth3/outclass/reduced

# Architecture
build_arch=ecconf
use_machinefile=TRUE

# This file is used to store information about restarts
ece_info_file="ece.info"

# -----------------------------------------------------------------------------
# *** Read platform dependent configuration
# -----------------------------------------------------------------------------
source ./ecconf.cfg

configure

# -----------------------------------------------------------------------------
# *** Time step settings
# -----------------------------------------------------------------------------
if has_config ifs
then
    case "${ifs_grid}" in

        T159L*) ifs_time_step_sec=3600 ;;
        T255L*) ifs_time_step_sec=2700 ;;
        T511L*) ifs_time_step_sec=900  ;;

        *)  error "Can't set time steps for unknown horizontal grid: ${ifs_grid}"
            ;;
    esac
fi

if has_config nemo
then
    case "${nem_grid}" in

        ORCA1L*)   nem_time_step_sec=2700; lim_time_step_sec=2700 ;;
        ORCA025L*) nem_time_step_sec=900 ; lim_time_step_sec=900  ;;

        *)  error "Can't set time steps for unknown horizontal grid: ${nem_grid}"
            ;;
    esac
fi

if has_config ifs nemo
then
    case "${ifs_grid}--${nem_grid}" in

        T159L*--ORCA1L*)
            ifs_time_step_sec=3600; nem_time_step_sec=2700; lim_time_step_sec=2700; cpl_freq_atm_oce_sec=10800
            ;;
        T255L*--ORCA1L*)
            ifs_time_step_sec=2700; nem_time_step_sec=2700; lim_time_step_sec=2700; cpl_freq_atm_oce_sec=2700
            ;;
        T511L*--ORCA025L*)
            ifs_time_step_sec=900 ; nem_time_step_sec=900 ; lim_time_step_sec=900 ; cpl_freq_atm_oce_sec=2700
            ;;

        *)  error "Can't set time steps for unknown combination of horizontal grids: ${ifs_grid}-${nem_grid}"
            ;;
    esac
fi

# -----------------------------------------------------------------------------
# *** IFS configuration
# -----------------------------------------------------------------------------

ifs_version=36r4

ifs_di_freq=$(( 24 * 3600 / ifs_time_step_sec ))
ifs_ddh_freq=$(( 120 * 3600 / ifs_time_step_sec ))

export ifs_res_hor=$(echo ${ifs_grid} | sed 's:T\([0-9]\+\)L\([0-9]\+\):\1:')
ifs_res_ver=$(echo ${ifs_grid} | sed 's:T\([0-9]\+\)L\([0-9]\+\):\2:')

export ifs_numproc=912

ifs_exe_file=${ecearth_src_dir}/ifs-${ifs_version}/bin/ifsmaster-${build_arch}

ifs_lastout=false

ifs_cmip5=TRUE
ifs_cmip5_rcp=0
export ifs_cmip_fixyear=0
[ -z "${ifs_cmip_fixyear}" ] && ifs_cmip_fixyear=0
export ifs_cmip_fixyear_ch4=0
[ -z "${ifs_cmip_fixyear_ch4}" ] && ifs_cmip_fixyear_ch4=0

# Repeat trap from ifs/suecrad.F90 for early catch
if ! has_config tm5:ch4fb && (( $ifs_cmip_fixyear != $ifs_cmip_fixyear_ch4 ))
then
    error 'CH4 in IFS is not provided by TM5, NCMIPFIXYR_CH4 should be set equal to NCMIPFIXYR'
fi

ifs_cmip6=TRUE
ifs_mac2sp=TRUE
ifs_cmip6piaer=TRUE
ifs_cmip6_scenario=historical

# enable optional COVID-19 scenarios, requires ifs_cmip6_scenario=SSP2-4.5
ifs_covid19=FALSE
# choose one scenario : Base TwoYearBlip ModerateGreen StrongGreen FossilFuel
ifs_covid19scen=Base
# basic sanity checks when covid19 is activated (SSP scenario and no support for LPJ-GUESS, PISCES nor TM5)
if [ ${ifs_covid19} == TRUE ] ; then
    [ ${ifs_cmip6_scenario} != SSP2-4.5 ] && info "with ifs_covid19=TRUE IFS uses ifs_cmip6_scenario=SSP2-4.5 not ${ifs_cmip6_scenario}"
    has_config any lpjg pisces tm5 && error "ifs_covid19=TRUE is not supported with LPJ-GUESS, PISCES nor TM5"
fi

lcmip6_strataer_simp=FALSE
lcmip6_strataer_full=TRUE
lcmip6_strataer_bckgd=FALSE

export ifs_A4xCO2=FALSE
export ifs_1PCTCO2=FALSE
export bgc_1PCTCO2=FALSE

# Time-varying orbital forcing (Qiong Zhang, SU-2013-09)
# https://dev.ec-earth.org/projects/ecearth3/wiki/Orbital_forcing_in_EC-Earth_3
#
#   ifs_orb_switch=false, no orbital calculations applied
#   ifs_orb_switch=true, use orbital calculations according to ifs_orb_mode
#   ifs_orb_mode="fixed_year", or "variable_year", or "fixed_parameters"
#     fixed_year: calculate the orbital parameters at ifs_orb_iyear, e.g.,1850
#     variable_year: calculate orbital parameters annually start from ifs_orb_iyear
#     fixed_parameters: prescribe orbital parameters for given year
case "${ifs_grid}" in
    T159*) ifs_orb_switch=true ;;
    *)     ifs_orb_switch=false ;;
esac
ifs_orb_mode="variable_year"
ifs_orb_iyear=$(date -u -d "${run_start_date}" +%Y)

# Relaxation of soil moisture (Wilhelm May, LU; October 2017)
#  
# LRXSM: Parameter indicating the levels to be nudged 
#
#   LRXSM =  0: no nudging 
#   LRXSM = 12: 4xdaily data and 3 levels (excluding level 1)      
#   LRXSM = 13: 4xdaily data and 4 levels
#
# LRXSMTx: time scale of the relaxation for level X (in hours)
#  
#   LRXSMTx =   0: actual values relpaced by external ones 
#   LRXSMTx =  24: 1 day
#   LRXSMTx = 120: 5 days
#
# LRXSMS: indicates when the relaxation is done 
#
#   LRXSMS = 0: before the time step
#   LRXSMS = 1:  after the time step
#
has_config soilnudg && ifs_lrxsm=13 || ifs_lrxsm=0
ifs_lrxsmt1=96
ifs_lrxsmt2=72
ifs_lrxsmt3=48
ifs_lrxsmt4=24
ifs_lrxsms=1

# IFS tuning parameters
variant=
has_config tm5:chem && variant=-AerChem
ifs_tuning_parameter_file=${ctrl_file_dir}/ifs-tuning-parameters-${ifs_grid}${variant}.sh
if [ -f ${ifs_tuning_parameter_file} ]
then
    source ${ifs_tuning_parameter_file}
else
    error "Sorry, ${ifs_tuning_parameter_file} not found, exiting."
fi


# Select source of vegetation data:
#  ifs       climatology from IFS
#  era20c    vegetation from an off-line LPJ-Guess run forced with ERA20C
#            (currently available only for T255 and T159)
#  cmip6     vegetation from an EC-Earth3-Veg (interactive LPJ-Guess) run 
#            (currently available only for T255)
#  custom_exp vegetation from any EC-Earth3-Veg run exp
#            (must contain same variables as era20c & cmip6 and located in icmcl_exp folder)
#  none      don't create an ICMCL file with vegetation data (this is set
#            automatically if LPJG is used with feedback)
#
# set above in AS runtime

has_config lpjg:fdbck && ifs_veg_source="none"

case ${ifs_veg_source} in
"ifs" )
    # Use Lambert-Beer to compute effective vegetation cover
    n_compute_eff_veg_fraction=2
    ;;
"era20c" )
    # LPJG vegetation is provided as effective cover
    # Don't use Lambert-Beer
    n_compute_eff_veg_fraction=0

    case "${ifs_grid}" in
        T159L*) veg_version=v29 ;;
        T255L*) veg_version=v16 ;;
        *)  error "Vegetation from off-line LPJ-Guess not available for ${ifs_grid}" ;;
    esac    
    ;;
"cmip6" )
    # LPJG vegetation is provided as effective cover
    # Don't use Lambert-Beer
    n_compute_eff_veg_fraction=0

    case "${ifs_grid}" in
        T255L*) veg_version=v32 ;;
        *)  error "Vegetation from CMIP6 EC-Earth3-Veg not available for ${ifs_grid}" ;;
    esac    
    ;;
"custom_"* )
    # LPJG vegetation is provided as effective cover
    # Don't use Lambert-Beer
    n_compute_eff_veg_fraction=0

    veg_version=${ifs_veg_source:7}
    if [ ! -d ${ini_data_dir}/ifs/${ifs_grid}/icmcl_${veg_version} ]
    then
        error "requested IFS_VEG_SOURCE = ${ifs_veg_source} but not found in ${ini_data_dir}/ifs/${ifs_grid}/icmcl_${veg_version}"
    fi
    ;;
"none" )
    # LPJG with feedback
    n_compute_eff_veg_fraction=0
    ! has_config lpjg:fdbck && error "IFS requires an offline source of vegetation"
    ;;
* )
    error "Vegetation from ${ifs_veg_source} not implemented"
    ;;
esac

# use DMI land ice physics and varying snow albedo
case "${ifs_grid}" in
    T159*) ifs_landice=true ;;
    *)     ifs_landice=false ;;
esac

# -----------------------------------------------------------------------------
# *** NEMO/LIM configuration
# -----------------------------------------------------------------------------

# This is only needed if the experiment is started from an existing set of NEMO
# restart files
nem_restart_file_path=${ini_data_dir}

nem_restart_offset=0

nem_res_hor=$(echo ${nem_grid} | sed 's:ORCA\([0-9]\+\)L[0-9]\+:\1:')

nem_config=${nem_grid}
has_config lim3           && nem_config=${nem_config}_LIM3

if has_config pisces tm5:co2
then
    nem_config=${nem_config}_CarbonCycle
elif has_config pisces
then
    nem_config=${nem_config}_PISCES
fi

# TODO - nemo standalone configs are not accounted for in this script, but this would set the required nem_config
! has_config ifs && nem_config=${nem_config}_standalone

nem_exe_file=${ecearth_src_dir}/nemo-3.6/CONFIG/${nem_config}/BLD/bin/nemo.exe

nem_numproc=1392

# Thermal conductivity of snow, see comment in ctrl/namelist.lim3.ref.sh
case "${ifs_grid}" in
    T159L* ) nem_rn_cdsn=0.25 ;;
    * )      nem_rn_cdsn=0.27 ;;
esac

# -----------------------------------------------------------------------------
# *** Runoff mapper configuration
# -----------------------------------------------------------------------------

rnf_exe_file=${ecearth_src_dir}/runoff-mapper/bin/runoff-mapper.exe
rnf_numproc=1

# -----------------------------------------------------------------------------
# *** LPJ-GUESS configuration
# -----------------------------------------------------------------------------

lpjg_time_step_sec=86400
lpjg_numproc=

has_config lpjg       && lpjg_on=1
has_config lpjg:fdbck && lpjg_fdbck=1
has_config tm5:co2    && lpjg_fdbck_tm5=1 || lpjg_fdbck_tm5=0

lpjg_fixNdepafter=-1
lpjg_fixLUafter=-1
[ -z "${lpjg_fixNdepafter}" ] && lpjg_fixNdepafter=-1
[ -z "${lpjg_fixLUafter}" ] && lpjg_fixLUafter=-1
export lpjg_fixNdepafter lpjg_fixLUafter

info '!!!! CMIP FIX YEAR SETTINGS:'
info "ifs_cmip_fixyear:  $ifs_cmip_fixyear"
info "lpjg_fixNDepAfter: $lpjg_fixNdepafter"
info "lpjg_fixLUAfter:   $lpjg_fixLUafter"
info '!!!!'  

lpjg_res=T${ifs_res_hor}
lpjg_exe_file=${ecearth_src_dir}/lpjg/build/guess_${lpjg_res}

# -----------------------------------------------------------------------------
# *** AMIP-reader configuration
# -----------------------------------------------------------------------------

amip_exe_file=${ecearth_src_dir}/amip-forcing/bin/amip-forcing.exe
amip_numproc=1

# -----------------------------------------------------------------------------
# *** TM5 configuration
# -----------------------------------------------------------------------------

if $(has_config tm5)
then
    # With TM5, NPRTRV is set to 1 in the namelist. To avoid some out-of-bound
    # arrays in IFS, we must limit the number of cores for IFS
    if (( ifs_numproc > (ifs_res_hor+1) ))
    then
        error "too much cores requested for IFS, max is $((ifs_res_hor+1))"
    fi

    # TM5 settings
    has_config tm5:co2 && tmversion="co2" || tmversion="cb05"
    has_config tm5:co2 && export tm5_co2=1 || export tm5_co2=0
    export tm5_exch_nlevs=34
    tm5_time_step_sec=3600
    export tm5_numproc_x=1
    export tm5_numproc_y=45
    tm5_numproc=$(( tm5_numproc_x * tm5_numproc_y ))
    export tm5_emiss_fixyear=0

    # limited number of levels for feedback (aerosols, currently set to lmax_conv in TM5)
    case ${tm5_exch_nlevs} in
        34) export tm5_exch_nlevs_cutoff=23 ;;
        10) export tm5_exch_nlevs_cutoff=10 ;;
         4) export tm5_exch_nlevs_cutoff=4  ;;
         *) error "not supported number of levels for TM5"
    esac

    # executable
    tm5_exe_file=${ecearth_src_dir}/tm5mp/build-${tmversion}-ml${tm5_exch_nlevs}/appl-tm5-${tmversion}.x

    # path to initial conditions, modify as needed
    tm5_restart_file_path=${ini_data_dir}/tm5/restart/${tmversion}-ml${tm5_exch_nlevs}

    # fields sent back to IFS
    has_config tm5:o3fb   && tm5_to_ifs=O3 || tm5_to_ifs=
    has_config tm5:ch4fb  && tm5_to_ifs=${tm5_to_ifs},CH4
    has_config tm5:aerfb && tm5_to_ifs=${tm5_to_ifs},"\
N2,SU2,BC2,OC2,N3,SU3,BC3,OC3,SS3,DU3,\
N4,SU4,BC4,OC4,SS4,DU4,N5,BC5,OC5,N6,DU6,N7,DU7,\
NO3,MSA,\
AOD_01,AOD_02,AOD_03,AOD_04,AOD_05,AOD_06,AOD_07,AOD_08,AOD_09,AOD_10,AOD_11,AOD_12,AOD_13,AOD_14,\
SSA_01,SSA_02,SSA_03,SSA_04,SSA_05,SSA_06,SSA_07,SSA_08,SSA_09,SSA_10,SSA_11,SSA_12,SSA_13,SSA_14,\
ASF_01,ASF_02,ASF_03,ASF_04,ASF_05,ASF_06,ASF_07,ASF_08,ASF_09,ASF_10,ASF_11,ASF_12,ASF_13,ASF_14"
    has_config tm5:co2fb && tm5_to_ifs=${tm5_to_ifs},CO2

    export tm5_to_ifs=$(echo ${tm5_to_ifs} | sed "s/^,//")

    # coupled to LPJ-Guess and/or PISCES?
    has_config tm5:co2 lpjg   && export cpl_tm_guess=T  || export cpl_tm_guess=F
    has_config tm5:co2 pisces && export cpl_tm_pisces=T || export cpl_tm_pisces=F
fi

# -----------------------------------------------------------------------------
# *** OASIS configuration
# -----------------------------------------------------------------------------

# Restart files for the coupling fields (note 8 character limit in OASIS)
#   rstas.nc : atmosphere single-category fields
#   rstam.nc : atmosphere multi-category fields
#   rstos.nc : ocean single-category fields
#   rstom.nc : ocean multi-category fields
oas_rst_ifs_nemo="rstas.nc rstos.nc"

oas_rst_ifs_lpjg="vegin.nc lpjgv.nc"

# Met fields from IFS to TM (always required)
oas_rst_ifs_tm5="r_hum.nc r_g2d.nc r_udr.nc r_div.nc r_vor.nc \
                 r_ddr.nc r_tmp.nc r_dmf.nc r_s2d.nc r_umf.nc"

has_config tm5:chem && \
    oas_rst_ifs_tm5=${oas_rst_ifs_tm5}' r_cc_.nc r_clw.nc r_cco.nc r_ciw.nc r_ccu.nc'

has_config tm5:o3fb || has_config tm5:ch4fb && oas_rst_ifs_tm5=$oas_rst_ifs_tm5' o3ch4.nc'
has_config tm5:aerfb && oas_rst_ifs_tm5=$oas_rst_ifs_tm5' C???????'

# C-cycle configuration
has_config tm5:co2 lpjg   && oas_rst_ifs_tm5=$oas_rst_ifs_tm5' l_co2.nc rlpjg.nc'
has_config tm5:co2 pisces && oas_rst_ifs_tm5=$oas_rst_ifs_tm5' o_co2.nc pisce.nc'
has_config tm5:co2fb      && oas_rst_ifs_tm5=$oas_rst_ifs_tm5' co2mx.nc'

# final list of files depends on the activated components - this is used in save_ic as well
#oas_rst_files="${oas_rst_ifs_nemo} ${oas_rst_ifs_tm5} vegin.nc lpjgv.nc"
oas_rst_files=""
has_config ifs nemo && oas_rst_files+=" ${oas_rst_ifs_nemo}"
has_config ifs lpjg && oas_rst_files+=" ${oas_rst_ifs_lpjg}"
has_config ifs tm5 && oas_rst_files+=" ${oas_rst_ifs_tm5}"

# Decide whether the OASIS weight files for interpolation should be linked from
# the setup directory (true) or not (false). In the latter case, the weights
# are re-computed at the start of the run.
oas_link_weights=true

# Flux correction for runoff (not calving) sent from Oasis to ocean.
# 1.07945 is computed to compensate for a P-E=-0.016 mm/day (valid for std res)
case "${ifs_grid}" in
    T159L* ) has_config nemo && oas_mb_fluxcorr=1.08652 ;;
    * ) has_config nemo && oas_mb_fluxcorr=1.07945 ;;
esac

# -----------------------------------------------------------------------------
# *** XIOS configuration
# -----------------------------------------------------------------------------

xio_exe_file=${ecearth_src_dir}/xios-2.5/bin/xios_server.exe

xio_numproc=95

# -----------------------------------------------------------------------------
# *** Extra initial conditions saved during the run
# -----------------------------------------------------------------------------
if has_config save_ic
then
    source ./libsave_ic.sh
    declare -a save_ic_date save_ic_date1 save_ic_sec save_ic_day save_ic_ppt_file save_ic_nemo_ts
    oas_rst_files="${oas_rst_ifs_nemo} ${oas_rst_ifs_tm5} vegin.nc lpjgv.nc"
fi

# -----------------------------------------------------------------------------
# *** Carbon cycle configuration
# -----------------------------------------------------------------------------
# set to true to write co2 fluxes sent to TM5
ccycle_debug_fluxes=true

# =============================================================================
# *** END of User configuration
# =============================================================================

# =============================================================================
# *** This is where the code begins ...
# =============================================================================

# -----------------------------------------------------------------------------
# *** Create the run dir if necessary and go there
#     Everything is done from here.
# -----------------------------------------------------------------------------
if [ ! -d ${run_dir} ]
then
    mkdir -p ${run_dir}
fi
cd ${run_dir}

# -----------------------------------------------------------------------------
# Autosubmit sanity check
# -----------------------------------------------------------------------------
CHUNK=2
if [ -f ece.info ]; then
  ece_info_leg_number=$(grep leg_number ece.info | tail -n 1 | awk -F"=" '{print $2}')
  current_leg_number=$((ece_info_leg_number + 1))
  if [[ "${CHUNK}" != "${current_leg_number}" ]]; then
    echo "Runscript leg_number" $current_leg_number
    echo "Don't match with Autosubmit CHUNK" ${CHUNK}
    exit 1
  fi
fi

# -----------------------------------------------------------------------------
# *** Determine the time span of this run and whether it's a restart leg
# -----------------------------------------------------------------------------

# Regularise the format of the start and end date of the simulation
run_start_date=$(date -uR -d "${run_start_date}")
run_end_date=$(date -uR -d "${run_end_date}")


# -----------------------------------------------------------------------------
# *** Set path to grib_set
# -----------------------------------------------------------------------------

grib_set=${GRIB_BIN_PATH}${GRIB_BIN_PATH:+/}grib_set

# Loop over the number of legs
for (( ; run_num_legs>0 ; run_num_legs-- ))
do

    # Check for restart information file and set the current leg start date
    #   Ignore restart information file if force_run_from_scratch is true
    if ${force_run_from_scratch} || ! [ -r ${ece_info_file} ]
    then
        leg_is_restart=false
        leg_start_date=${run_start_date}
        leg_number=1
    else
        leg_is_restart=true
        . ./${ece_info_file}
        leg_start_date=${leg_end_date}
        leg_number=$((leg_number+1))
    fi

    # Compute the end date of the current leg
    if [ -n "${rst_freq}" ]
    then
        leg_end_date=$(date -uR -d "${leg_start_date} + ${rst_freq}")
    else
        leg_end_date=${run_end_date}
    fi

    # Check if legs are integer multiples of full years if LPJG is used
    if has_config lpjg
    then
        
        if [[ $(date +%m%d%T -u -d "${leg_start_date}") != "010100:00:00" || \
            $(date +%m%d%T -u -d "${leg_start_date} + ${rst_freq}") != "010100:00:00" ]]
        then
            error "LPJ-GUESS runs must start on Jan 1 and end on Dec 31. Multi-year legs are allowed."
        fi
    fi              

    if [[ "TRUE" == "TRUE" ]]
    then
        leg_end_date=${run_end_date}
        ifs_lastout=true
    fi

    # Some time variables needed later
    leg_length_sec=$(( $(date -u -d "${leg_end_date}" +%s) - $(date -u -d "${leg_start_date}" +%s) ))
    leg_start_sec=$(( $(date -u -d "${leg_start_date}" +%s) - $(date -u -d "${run_start_date}" +%s) ))
    leg_end_sec=$(( $(date -u -d "${leg_end_date}" +%s) - $(date -u -d "${run_start_date}" +%s) ))
    leg_start_date_yyyymmdd=$(date -u -d "${leg_start_date}" +%Y%m%d)
    leg_start_date_yyyy=$(date -u -d "${leg_start_date}" +%Y)
    leg_end_date_yyyy=$(date -u -d "${leg_end_date}" +%Y)

    # Check whether there's actually time left to simulate - exit otherwise
    if [ ${leg_length_sec} -le 0 ]
    then
        info "Leg start date equal to or after end of simulation."
        info "Nothing left to do. Exiting."
        exit 0
    fi

    # Initial conditions saved during the run
    do_save_ic=false
    save_ic_custom=false
    has_config save_ic && save_ic_get_config
    # if you do not use an option with save_ic, you must define 'do_save_ic' and
    # 'save_ic_date_offset' here or in ../libsave_ic.sh/save_ic_get_config()
    # with AS runtime, no need to edit the script, set SAVE_IC_OFFSET (and optionally SAVE_IC_COND)
    if $save_ic_custom
    then
        [[ "true" = "" ]] && save_ic_cond=true || save_ic_cond='true'
        if eval $save_ic_cond ; then do_save_ic=true ; else do_save_ic=false ; fi
        save_ic_date_offset=(  )
    fi
    ${do_save_ic} && save_ic_define_vars

    # -------------------------------------------------------------------------
    # *** Prepare the run directory for a run from scratch
    # -------------------------------------------------------------------------
    if ! $leg_is_restart
    then
        # ---------------------------------------------------------------------
        # *** Check if run dir is empty. If not, and if we are allowed to do so
        #     by ${force_run_from_scratch}, remove everything
        # ---------------------------------------------------------------------
        if $(ls * >& /dev/null)
        then
            if ${force_run_from_scratch}
            then
                rm -fr ${run_dir}/*
            else
                error "Run directory not empty and \$force_run_from_scratch not set."
            fi
        fi

        # ---------------------------------------------------------------------
        # *** Copy executables of model components
        # *** Additionally, create symlinks to the original place for reference
        # ---------------------------------------------------------------------
        cp    ${ifs_exe_file} .
        ln -s ${ifs_exe_file} $(basename ${ifs_exe_file}).lnk

        if $(has_config amip)
        then
            cp    ${amip_exe_file} .
            ln -s ${amip_exe_file} $(basename ${amip_exe_file}).lnk
        fi

        if $(has_config nemo)
        then
            cp    ${nem_exe_file} .
            ln -s ${nem_exe_file} $(basename ${nem_exe_file}).lnk

            cp    ${rnf_exe_file} .
            ln -s ${rnf_exe_file} $(basename ${rnf_exe_file}).lnk

            cp    ${xio_exe_file} .
            ln -s ${xio_exe_file} $(basename ${xio_exe_file}).lnk
        fi

        if $(has_config lpjg)
        then
            cp    ${lpjg_exe_file} .
            ln -s ${lpjg_exe_file} $(basename ${lpjg_exe_file}).lnk
        fi

        if $(has_config tm5)
        then
            cp    ${tm5_exe_file} .
            ln -s ${tm5_exe_file} $(basename ${tm5_exe_file}).lnk
        fi

        # ---------------------------------------------------------------------
        # *** Files needed for IFS (linked)
        # ---------------------------------------------------------------------

        # Initial data
        ln -s \
        ${ini_data_dir}/ifs/${ifs_grid}/${leg_start_date_yyyymmdd}/ICMGGECE3INIUA \
                                                            ICMGG${exp_name}INIUA
        ln -s \
        ${ini_data_dir}/ifs/${ifs_grid}/${leg_start_date_yyyymmdd}/ICMSHECE3INIT \
                                                            ICMSH${exp_name}INIT
        rm -f ICMGG${exp_name}INIT
        cp ${ini_data_dir}/ifs/${ifs_grid}/${leg_start_date_yyyymmdd}/ICMGGECE3INIT \
                                                            ICMGG${exp_name}INIT

        # add bare_soil_albedo to ICMGG*INIT
        tempfile=tmp.$$
        ${grib_set} -s dataDate=$(date -u -d "$run_start_date" +%Y%m%d) \
            ${ini_data_dir}/ifs/${ifs_grid}/climate/bare_soil_albedos.grb \
            ${tempfile}

        cat ${tempfile} >> ICMGG${exp_name}INIT
        rm -f ${tempfile}

        # add land ice mask if needed
        if ${ifs_landice}
        then
            tempfile=tmp.$$
            cdo divc,10 -setcode,82 -selcode,141 ICMGG${exp_name}INIT ${tempfile}
            ${grib_set} -s gridType=reduced_gg ${tempfile} ${tempfile}
            cat ${tempfile} >> ICMGG${exp_name}INIT
            rm -f ${tempfile}
        fi

        # Other stuff
        ln -s ${ini_data_dir}/ifs/rtables/* .
      
        if $(has_config atmnudg) ; then
            ln -s ${ini_data_dir}/rlxml* .
        fi
        
        # Output control (ppt files)
        if [ ! -f ${output_control_files_dir}/pptdddddd0600 ] &&  [ ! -f ${output_control_files_dir}/pptdddddd0300 ];then
           echo "Error from ece-esm.sh: Neither the file pptdddddd0600 or pptdddddd0300 exists in the directory:"
           echo " " ${output_control_files_dir}
           exit -1
        fi
        mkdir postins
        cp ${output_control_files_dir}/ppt* postins/
        if [ -f postins/pptdddddd0600 ];then
           ln -s pptdddddd0600 postins/pptdddddd0000
           ln -s pptdddddd0600 postins/pptdddddd1200
           ln -s pptdddddd0600 postins/pptdddddd1800
        fi
        if [ -f postins/pptdddddd0300 ];then
           ln -s pptdddddd0300 postins/pptdddddd0900
           ln -s pptdddddd0300 postins/pptdddddd1500
           ln -s pptdddddd0300 postins/pptdddddd2100
           if [ ! -f postins/pptdddddd0600 ];then
               ln -s pptdddddd0300 postins/pptdddddd0000
               ln -s pptdddddd0300 postins/pptdddddd0600
               ln -s pptdddddd0300 postins/pptdddddd1200
               ln -s pptdddddd0300 postins/pptdddddd1800
           fi
        fi
        /bin/ls -1 postins/* > dirlist

        # ---------------------------------------------------------------------
        # *** Files needed for LPJ-GUESS
        # ---------------------------------------------------------------------
        if $(has_config lpjg)
        then
            # Check for valid grid
            if [ $lpjg_res != "T255" -a $lpjg_res != "T159" ]
            then
                error "LPJG-gridlist doesn't exist for ifs-grid: ${ifs_grid}" 
            fi
            # Initial data - saved state for LPJ-GUESS (.bin format)
            lpjgstartdir=$(printf "lpjg_state_%04d" $leg_start_date_yyyy)
            ln -sf ${ini_data_dir}/lpjg/ini_state/${lpjg_res}/${lpjgstartdir} ${run_dir}/${lpjgstartdir}

            # Control files (i.e. .ins, landuse, N deposition, soil type files etc.)
            cp  -f ${ecearth_src_dir}/lpjg/data/ins/*.ins .
            # activate the new litterfall scheme for C4MIP - for the coupled model this is done when both pisces and lpjg are activated
            has_config pisces lpjg && echo -e "!override for EC-Earth-CC in runscript\nifpftlitterfall 1\ncalc_phen_after_restart 0" >> global.ins
            mkdir -p ${run_dir}/landuse

        fi

        # ---------------------------------------------------------------------
        # *** Files needed for NEMO (linked)
        # ---------------------------------------------------------------------
        if $(has_config nemo)
        then
            # Link initialisation files for matching ORCA grid
            for f in \
                bathy_meter.nc coordinates.nc \
                ahmcoef.nc \
                K1rowdrg.nc M2rowdrg.nc mask_itf.nc \
                decay_scale_bot.nc decay_scale_cri.nc \
                mixing_power_bot.nc mixing_power_cri.nc mixing_power_pyc.nc \
                runoff_depth.nc subbasins.nc
            do
                [ -f ${ini_data_dir}/nemo/initial/${nem_grid}/$f ] && ln -s ${ini_data_dir}/nemo/initial/${nem_grid}/$f
            done

            # Copying the time independent NEMO files for the matching ORCA grid in order to facilitate cmorisation:
            for f in \
                bathy_meter.nc subbasins.nc
            do
                mkdir -p output/nemo/ofx-data
                [ -f ${ini_data_dir}/nemo/initial/${nem_grid}/$f ] && cp -f ${ini_data_dir}/nemo/initial/${nem_grid}/$f output/nemo/ofx-data/
            done

            # Link geothermal heating file (independent of grid) and matching weight file
            ln -s ${ini_data_dir}/nemo/initial/Goutorbe_ghflux.nc
            ln -s ${ini_data_dir}/nemo/initial/weights_Goutorbe1_2_orca${nem_res_hor}_bilinear.nc

            # Link the salinity climatology file (needed for diagnostics)
            ln -s ${ini_data_dir}/nemo/climatology/${nem_grid}/sali_ref_clim_monthly.nc

            # Link either restart files or climatology files for the initial state
            if $(has_config nemo:start_from_restart)
            then
                # When linking restart files, we accept three options:
                # (1) Merged files for ocean and ice, i.e.
                #     restart_oce.nc and restart_ice.nc
                # (2) One-file-per-MPI-rank, i.e.
                #     restart_oce_????.nc and restart_ice_????.nc
                #     No check is done whether the number of restart files agrees
                #     with the number of MPI ranks for NEMO!
                # (3) One-file-per-MPI-rank with a prefix, i.e.
                #     <exp_name>_<time_step>_restart_oce_????.nc (similar for the ice)
                #     The prefix is ignored.
                # The code assumes that one of the options can be applied! If more
                # options are applicable, the first is chosen. If none of the
                # options apply, NEMO will crash with missing restart file.
                if   ls -U ${nem_restart_file_path}/restart_[oi]ce.nc > /dev/null 2>&1
                then
                    ln -s ${nem_restart_file_path}/restart_[oi]ce.nc ./

                elif ls -U ${nem_restart_file_path}/restart_[oi]ce_????.nc > /dev/null 2>&1
                then
                    ln -s ${nem_restart_file_path}/restart_[oi]ce_????.nc ./

                else
                    for f in ${nem_restart_file_path}/????_????????_restart_[oi]ce_????.nc
                    do
                        ln -s $f $(echo $f | sed 's/.*_\(restart_[oi]ce_....\.nc\)/\1/')
                    done
                fi
            else

                # Temperature and salinity files for initialisation
                ln -s ${ini_data_dir}/nemo/climatology/absolute_salinity_WOA13_decav_Reg1L75_clim.nc
                ln -s ${ini_data_dir}/nemo/climatology/conservative_temperature_WOA13_decav_Reg1L75_clim.nc
                ln -s ${ini_data_dir}/nemo/climatology/weights_WOA13d1_2_orca${nem_res_hor}_bilinear.nc

                # Grid dependent runoff files
                case ${nem_grid} in
                    ORCA1*)   ln -s ${ini_data_dir}/nemo/climatology/runoff-icb_DaiTrenberth_Depoorter_ORCA1_JD.nc ;;
                    ORCA025*) ln -s ${ini_data_dir}/nemo/climatology/ORCA_R025_runoff_v1.1.nc ;;
                esac
            fi

            # for ocean_nudging
            if $(has_config nemo:ocenudg) ; then
                ln -s ${ini_data_dir}/nemo/oce_nudg/resto.nc
            fi

            # XIOS files
            . ${ctrl_file_dir}/iodef.xml.sh > iodef.xml
            ln -s ${ctrl_file_dir}/context_nemo.xml
            ln -s ${ctrl_file_dir}/domain_def_nemo.xml
            ln -s ${ctrl_file_dir}/axis_def_nemo.xml
            ln -s ${ctrl_file_dir}/grids_def_nemo.xml
            ln -s ${ctrl_file_dir}/field_def_nemo-lim.xml
            ln -s ${ctrl_file_dir}/field_def_nemo-opa.xml
            ln -s ${ctrl_file_dir}/field_def_nemo-pisces.xml
            ln -s ${ctrl_file_dir}/field_def_nemo-inerttrc.xml
            ln -s ${output_control_files_dir}/file_def_nemo-lim3.xml file_def_nemo-lim.xml
            ln -s ${output_control_files_dir}/file_def_nemo-opa.xml
            ln -s ${output_control_files_dir}/file_def_nemo-pisces.xml

            if [ -f ${ini_data_dir}/xios/ORCA${nem_res_hor}/coordinates_xios.nc ]
            then
                cp ${ini_data_dir}/xios/ORCA${nem_res_hor}/coordinates_xios.nc ./
            else
                info "File 'coordinates_xios.nc' not found. NEMO can not be run with land domain removal!"
            fi

            # Files needed for TOP/PISCES
            if $(has_config pisces)
            then
                ln -fs ${ini_data_dir}/nemo/pisces/dust_INCA_ORCA_R1.nc
                ln -fs ${ini_data_dir}/nemo/pisces/ndeposition_Duce_ORCA_R1.nc
                ln -fs ${ini_data_dir}/nemo/pisces/pmarge_etopo_ORCA_R1.nc
                ln -fs ${ini_data_dir}/nemo/pisces/river_global_news_ORCA_R1.nc
                ln -fs ${ini_data_dir}/nemo/pisces/Solubility_T62_Mahowald_ORCA_R1.nc

                ln -fs ${ini_data_dir}/nemo/pisces/par_fraction_gewex_clim90s00s_ORCA_R1.nc
                ln -fs ${ini_data_dir}/nemo/pisces/DIC_GLODAP_annual_ORCA_R1.nc
                ln -fs ${ini_data_dir}/nemo/pisces/Alkalini_GLODAP_annual_ORCA_R1.nc
                ln -fs ${ini_data_dir}/nemo/pisces/O2_WOA2009_monthly_ORCA_R1.nc
                ln -fs ${ini_data_dir}/nemo/pisces/PO4_WOA2009_monthly_ORCA_R1.nc
                ln -fs ${ini_data_dir}/nemo/pisces/Si_WOA2009_monthly_ORCA_R1.nc
                ln -fs ${ini_data_dir}/nemo/pisces/DOC_PISCES_monthly_ORCA_R1.nc
                ln -fs ${ini_data_dir}/nemo/pisces/Fer_PISCES_monthly_ORCA_R1.nc
                ln -fs ${ini_data_dir}/nemo/pisces/NO3_WOA2009_monthly_ORCA_R1.nc

                # create co2 concentration file atcco2.txt if required
                if { [ $ifs_cmip_fixyear -gt 0 ] || [[ "${ifs_A4xCO2}" = "TRUE" ]]; } && [[ "${bgc_1PCTCO2}" = "FALSE" ]]
                then
                    rm -f atcco2.txt
                elif [[ "${bgc_1PCTCO2}" = "TRUE" ]]
                then
                    cp -f ${ini_data_dir}/nemo/pisces/mole-fraction-of-carbon-dioxide-in-air_1pctCO2_1849-2016.txt atcco2.txt
                else
                    # determine scenario-name and co2-file middle-fix
                    case $(echo ${ifs_cmip6_scenario} | tr '[:upper:]' '[:lower:]') in
                        hist*)     pis_scen="ssp585"; pis_sco2_mfix="REMIND-MAGPIE-ssp585-1-2-1";;
                        ssp2-4.5*) pis_scen="ssp245"; pis_sco2_mfix="MESSAGE-GLOBIOM-ssp245-1-2-1";;
                        ssp5-3.4*) pis_scen="ssp534os"; pis_sco2_mfix="REMIND-MAGPIE-ssp534-over-1-2-1";;
                        ssp5-8.5*) pis_scen="ssp585"; pis_sco2_mfix="REMIND-MAGPIE-ssp585-1-2-1";;
                        *)  error "Scenario ${ifs_cmip6_scenario} not defined for PISCES" ;;
                    esac

                    # concatenate historic and scenario (2015+) co2 concentration file
                    pis_sco2_pfix="${ini_data_dir}/nemo/pisces/mole-fraction-of-carbon-dioxide-in-air_input4MIPs_GHGConcentrations"
                    cat ${pis_sco2_pfix}_CMIP_UoM-CMIP-1-2-0_gr1-GMNHSH_1849-2014.txt ${pis_sco2_pfix}_ScenarioMIP_UoM-${pis_sco2_mfix}_gr1-GMNHSH_2015-2500.txt > atcco2.txt
                fi
            fi

            #linking surface boundary conditions for CFCs (even if CFCs are not included)
            ln -fs ${ini_data_dir}/nemo/cfc/CFCs_CDIAC_extension_1637_2019.dat CFCs_CDIAC.dat

            if $(has_config pisces:start_from_restart)
            then
            # Same three options as for nemo:start_from_restart
                if   ls -U ${nem_restart_file_path}/restart_trc.nc > /dev/null 2>&1
                then
                    ln -s ${nem_restart_file_path}/restart_trc.nc ./

                elif ls -U ${nem_restart_file_path}/restart_trc_????.nc > /dev/null 2>&1
                then
                    ln -s ${nem_restart_file_path}/restart_trc_????.nc ./

                else
                    for f in ${nem_restart_file_path}/????_????????_restart_trc_????.nc
                    do
                        ln -s $f $(echo $f | sed 's/.*_\(restart_trc_....\.nc\)/\1/')
                    done
                fi
            fi

        fi

        # ---------------------------------------------------------------------
        # *** Files needed for the Runoff mapper (linked)
        # ---------------------------------------------------------------------

        has_config rnfmapper && \
            ln -s ${ini_data_dir}/runoff-mapper/runoff_maps.nc

        # -------------------------------------------------------------------------
        # *** File and dir needed for TM5
        # -------------------------------------------------------------------------
        if $(has_config tm5)
        then
            tm5_istart=33

            case ${tm5_istart} in
                33|32) ln -s \
                    ${tm5_restart_file_path}/TM5_restart_${leg_start_date_yyyymmdd}_0000_glb300x200.nc
                    ;;
                31) ln -s ${tm5_restart_file_path}/tm5_save.hdf
                    ;;
                5)  ln -s ${tm5_restart_file_path}/tm5_mmix.hdf
                    ;;
                2|9) 
                    ;;
                *)  error "Unsupported initial fields option (TM5): ${tm5_istart}"
                    ;;
            esac

            # spectral info
            ln -s ${ini_data_dir}/tm5/TM5_INPUT/T${ifs_res_hor}_info.txt

            # Profiling dir for TM5
            mkdir -p ${run_dir}/tm5_profile
        fi

        # ---------------------------------------------------------------------
        # *** Files needed for OASIS (linked)
        # ---------------------------------------------------------------------

        # Name table file
        ln -s ${ini_data_dir}/oasis/cf_name_table.txt

        # -- Get grid definition and weight files for IFS/NEMO or IFS/AMIP coupling
        has_config nemo && \
            oas_grid_dir=${ini_data_dir}/oasis/T${ifs_res_hor}-ORCA${nem_res_hor} && \
            mycp='cp'

        has_config amip && \
            oas_grid_dir=${ini_data_dir}/oasis/AMIP && \
            mycp='cdo -f nc copy' # to enforce nc format, needed for 'cdo merge' to work (have nc4c with Primavera files)

        # Grid definition files
        if $(has_config tm5)
        then
            ${mycp} ${oas_grid_dir}/areas.nc gcm_areas.nc
            ${mycp} ${oas_grid_dir}/grids.nc gcm_grids.nc
            ${mycp} ${oas_grid_dir}/masks.nc gcm_masks.nc
        else
            ln -s ${oas_grid_dir}/areas.nc
            ln -s ${oas_grid_dir}/grids.nc
            ln -s ${oas_grid_dir}/masks.nc
        fi

        # Weight files
        case ${ifs_res_hor} in
            159)  oas_agrd=080
                  ;;
            255)  oas_agrd=128
                  ;;
            511)  oas_agrd=256
                  ;;
            799)  oas_agrd=400
                  ;;
            *)    error "Unsupported horizontal resolution (IFS): ${ifs_res_hor}"
                  ;;
        esac

        if $(has_config nemo)
        then
            case ${nem_res_hor} in
                1)  oas_ogrd=O1t0
                    ;;
                025)  oas_ogrd=Ot25
                    ;;
                *)  error "Unsupported horizontal resolution (NEMO): ${nem_res_hor}"
                    ;;
            esac
        fi

        if ${oas_link_weights}
        then
            for f in ${oas_grid_dir}/rmp_????_to_????_GAUSWGT.nc
            do
                ln -s $f
            done
        fi

        if $(has_config ifs nemo)
        then
            for f in ${oas_rst_ifs_nemo}
            do
                cp ${oas_grid_dir}/rst/$f .
            done
        fi

        # -- Get grid definition, weight and restart files for TM5 coupling
        if $(has_config tm5)
        then
            oas_grid_dir=${ini_data_dir}/oasis/T${ifs_res_hor}-TM5-LPJG

            cp ${oas_grid_dir}/tm5_areas.nc .
            cp ${oas_grid_dir}/tm5_grids.nc .
            cp ${oas_grid_dir}/tm5_masks.nc .

            if ${oas_link_weights}
            then
                for f in ${oas_grid_dir}/rmp_????_to_????_*.nc
                do
                    ln -s $f
                done
            fi

            # -- Get restart files for TM5-IFS/LPJG/PISCES 
            for f in ${oas_rst_ifs_tm5}
            do
                cp ${oas_grid_dir}/rst/${tm5_exch_nlevs}-levels/$f .
            done

            # -- Merge grid definition files
            cdo merge gcm_areas.nc tm5_areas.nc areas.nc
            cdo merge gcm_grids.nc tm5_grids.nc grids.nc
            cdo merge gcm_masks.nc tm5_masks.nc masks.nc
        fi

    else # i.e. $leg_is_restart == true

        # ---------------------------------------------------------------------
        # *** Remove all leftover output files from previous legs
        # ---------------------------------------------------------------------

        # IFS files
        rm -f ICM{SH,GG}${exp_name}+??????

        # NEMO files
        rm -f ${exp_name}_??_????????_????????_{grid_U,grid_V,grid_W,grid_T,icemod,SBC,scalar,SBC_scalar,diad_T}.nc

        # TM5 restart file type
        tm5_istart=33

        if [ $tm5_istart -eq 31 ] && $(has_config tm5)
        then
            ln -sf save_${leg_start_date_yyyymmdd}00_glb300x200.hdf tm5_save.hdf
        fi

    fi # ! $leg_is_restart

    #--------------------------------------------------------------------------
    # *** Surface restoring and ocean nudging options
    #--------------------------------------------------------------------------
    if $(has_config nemo:ocenudg) ; then
        ln -fs ${ini_data_dir}/nemo/oce_nudg/temp_sal*.nc ./
    fi

    if $(has_config nemo:surfresto) ; then
        ln -fs ${ini_data_dir}/nemo/surface_restoring/sss_restore_data*.nc  ./
        ln -fs ${ini_data_dir}/nemo/surface_restoring/sst_restore_data*.nc  ./
        ln -fs ${ini_data_dir}/nemo/surface_restoring/mask_restore*.nc ./
    fi

    # -------------------------------------------------------------------------
    # *** Remove land grid-points
    # -------------------------------------------------------------------------
    if $(has_config nemo:elpin)
    then
        if [ ! -f coordinates_xios.nc ]
        then
            error "ELpIN requested, but file 'coordinates_xios.nc' was not found"
        fi
        jpns=($(${ecearth_src_dir}/util/ELPiN/ELPiNv2.cmd ${nem_numproc}))
        info "nemo domain decompostion from ELpIN: ${jpns[@]}"
        nem_numproc=${jpns[0]}
        nem_jpni=${jpns[1]}
        nem_jpnj=${jpns[2]}
    elif has_config nemo
    then
        info "nemo original domain decomposition (not using ELPiN)"
    fi

    # -------------------------------------------------------------------------
    # *** Initial conditions saved during the run
    # -------------------------------------------------------------------------
    ${do_save_ic} && save_ic_prepare_output

    # -------------------------------------------------------------------------
    # *** Create some control files
    # -------------------------------------------------------------------------

    # Create TM5 runtime rcfile
    tm5_start_date=$(date -u -d "${leg_start_date}" +%F\ %T)
    tm5_end_date=$(date -u -d "${leg_end_date}" +%F\ %T)

    if $(has_config tm5)
    then
        cp -f ${ctrl_file_dir}/tm5-config-run.rc ${run_dir}
        ${ecearth_src_dir}/tm5mp/setup_tm5 --no-compile \
            --time-start="${tm5_start_date}" --time-final="${tm5_end_date}" \
            --istart=${tm5_istart} ${run_dir}/tm5-config-run.rc
    fi

    # IFS frequency output for namelist
    if [ -f postins/pptdddddd0300 ]
    then
        ifs_output_freq=$(( 3 * 3600 / ifs_time_step_sec ))
    elif [ -f postins/pptdddddd0600 ]
    then
        ifs_output_freq=$(( 6 * 3600 / ifs_time_step_sec ))
    else
        error "IFS output frequency undefined."
    fi

    # IFS, NEMO, LIM, AMIP namelist and OASIS namcouple files
    has_config ifs       && . ${ctrl_file_dir}/namelist.ifs.sh                          > fort.4
    has_config nemo      && . ${ctrl_file_dir}/namelist.nemo.ref.sh                     > namelist_ref
    has_config ifs nemo  && . ${ctrl_file_dir}/namelist.nemo-${nem_grid}-coupled.cfg.sh > namelist_cfg
    has_config lim3      && . ${ctrl_file_dir}/namelist.lim3.ref.sh                     > namelist_ice_ref
    has_config lim3      && . ${ctrl_file_dir}/namelist.lim3-${nem_grid}.cfg.sh         > namelist_ice_cfg
    has_config rnfmapper && . ${ctrl_file_dir}/namelist.runoffmapper.sh                 > namelist.runoffmapper
    has_config amip      && . ${ctrl_file_dir}/namelist.amip.sh                         > namelist.amip
    has_config pisces    && . ${ctrl_file_dir}/namelist.nemo.top.ref.sh                 > namelist_top_ref
    has_config pisces    && . ${ctrl_file_dir}/namelist.nemo.top.cfg.sh                 > namelist_top_cfg
    has_config pisces    && . ${ctrl_file_dir}/namelist.nemo.pisces.ref.sh              > namelist_pisces_ref
    has_config pisces    && . ${ctrl_file_dir}/namelist.nemo.pisces.cfg.sh              > namelist_pisces_cfg
    has_config nemo      && . ${ctrl_file_dir}/namelist.nemo.age.ref.sh                 > namelist_age_ref
    has_config nemo      && . ${ctrl_file_dir}/namelist.nemo.age.cfg.sh                 > namelist_age_cfg
    #include CFCs namelist even if CFCs are not included
    has_config nemo      && . ${ctrl_file_dir}/namelist.nemo.cfc.ref.sh                 > namelist_cfc_ref
    has_config nemo      && . ${ctrl_file_dir}/namelist.nemo.cfc.cfg.sh                 > namelist_cfc_cfg
    # C-cycle - overwrite coupled nemo namelist
    has_config pisces tm5:co2  && \
        . ${ctrl_file_dir}/namelist.nemo-${nem_grid}-carboncycle.cfg.sh > namelist_cfg

    lucia=
    . ${ctrl_file_dir}/namcouple.sh > namcouple

    # -------------------------------------------------------------------------
    # *** LPJ-GUESS initial data
    # -------------------------------------------------------------------------
    if $(has_config lpjg)
    then
        # LPJG runtime rcfile - update with leg dates
        . ${ctrl_file_dir}/namelist.lpjg.sh > lpjg_steps.rc

        # determine lpjg scenario-name and co2-file middle-fix
        case $(echo ${ifs_cmip6_scenario} | tr '[:upper:]' '[:lower:]') in
            hist*)     lpjg_scen="ssp370"; lu_src="AIM"    ; lpjg_sco2_mfix="AIM-ssp370-1-2-1"            ; lu_file_posfix="2018_10_08.txt";;
            ssp1-1.9*) lpjg_scen="ssp119"; lu_src="IMAGE"  ; lpjg_sco2_mfix="IMAGE-ssp119-1-2-1"          ; lu_file_posfix="2019_03_13.txt";;
            ssp1-2.6*) lpjg_scen="ssp126"; lu_src="IMAGE"  ; lpjg_sco2_mfix="IMAGE-ssp126-1-2-1"          ; lu_file_posfix="2018_10_08.txt";;
            ssp2-4.5*) lpjg_scen="ssp245"; lu_src="MESSAGE"; lpjg_sco2_mfix="MESSAGE-GLOBIOM-ssp245-1-2-1"; lu_file_posfix="2018_10_08.txt";;
            ssp3-7.0*) lpjg_scen="ssp370"; lu_src="AIM"    ; lpjg_sco2_mfix="AIM-ssp370-1-2-1"            ; lu_file_posfix="2018_10_08.txt";;
            ssp4-3.4*) lpjg_scen="ssp434"; lu_src="GCAM"   ; lpjg_sco2_mfix="GCAM4-ssp434-1-2-1"            ; lu_file_posfix="2018_10_08.txt";;
            ssp5-3.4*) lpjg_scen="ssp534os"; lu_src="MAGPIE"; lpjg_sco2_mfix="REMIND-MAGPIE-ssp534-over-1-2-1"            ; lu_file_posfix="2019_05_10.txt";;
            ssp5-8.5*) lpjg_scen="ssp585"; lu_src="MAGPIE" ; lpjg_sco2_mfix="REMIND-MAGPIE-ssp585-1-2-1"  ; lu_file_posfix="2018_10_08.txt";;
            *)  error "Scenario ${ifs_cmip6_scenario} not defined for LPJ-GUESS" ;;
        esac

        lpjg_scenario_new="historical + $lpjg_sco2_mfix"
        lpjg_scenario_info=${run_dir}/lpjg_scenario.info

        if [ -f $lpjg_scenario_info ]
        then
            source $lpjg_scenario_info
            if [ "$lpjg_scenario_new" = "$lpjg_scenario" ]
            then
                lpjg_copy_rte=false
            else
                lpjg_copy_rte=true
            fi
        else
            lpjg_copy_rte=true
        fi

        # copy RTE only if necessary (at beginning of a run or when scenario changes)
        if $lpjg_copy_rte
        then
            # write info about installed scenarios to file
            echo "lpjg_scenario=\"historical + $lpjg_sco2_mfix\"" > $lpjg_scenario_info
            # set file prefixes depending on scenario
            lu_file_prefix="1850_2100_luh2_Hist_ScenarioMIP_UofMD"
            lu_file_midfix="2_1_f"

            lu_path="${ini_data_dir}/lpjg/landuse/${lpjg_res}/${lpjg_scen}"

            # copy and reference-link landuse,  gross transitions, crops, n-fertilisation
            for inp in lu gross crop nfert
            do
                if [ $inp == "crop" -o $inp == "nfert" ]
                then
                    lu_src_file="${lu_path}/${inp}_rfirr_${lu_file_prefix}_${lu_src}_${lpjg_scen}_${lu_file_midfix}_${lpjg_res}_${lu_file_posfix}"
                else
                    lu_src_file="${lu_path}/${inp}_${lu_file_prefix}_${lu_src}_${lpjg_scen}_${lu_file_midfix}_${lpjg_res}_${lu_file_posfix}"
                fi
                cp -f $lu_src_file ${run_dir}/landuse/${inp}_luh2.txt
                ln -fs $lu_src_file ${run_dir}/landuse/${inp}_luh2.txt.lnk
            done
            
            # nitrogen deposition files
            mkdir -p ${run_dir}/ndep
            for inp in drynhx2 drynoy2 wetnhx2 wetnoy2
            do
                ndep_src_file="${ini_data_dir}/lpjg/ndep/${lpjg_res}/${lpjg_scen}/${lpjg_scen}_${lpjg_res}_${inp}.nc"
                cp -f  $ndep_src_file ${run_dir}/ndep/${inp}.nc
                ln -fs  $ndep_src_file ${run_dir}/ndep/${inp}.nc.lnk
            done

            # concatenate historic and scenario (2015+) co2 concentration file
            # hist co2 file 
            lpjg_hco2_file="${ini_data_dir}/ifs/cmip6-data/mole-fraction-of-carbon-dioxide-in-air_input4MIPs_GHGConcentrations_CMIP_UoM-CMIP-1-2-0_gr1-GMNHSH_0000-2014.nc"
            # scenario co2 file 
            lpjg_sco2_file="${ini_data_dir}/ifs/cmip6-data/mole-fraction-of-carbon-dioxide-in-air_input4MIPs_GHGConcentrations_ScenarioMIP_UoM-${lpjg_sco2_mfix}_gr1-GMNHSH_2015-2500.nc"
            # combined file
            lpjg_co2_file="${run_dir}/mole_fraction_of_carbon_dioxide_in_air_input4MIPs_lpjg.nc"
            rm -f $lpjg_co2_file
            cdo mergetime $lpjg_hco2_file $lpjg_sco2_file $lpjg_co2_file
        fi

        # Populate or update LPJG run directories
        for (( n=1; n<=${lpjg_numproc}; n++ ))
        do
            # if run from scratch or number of procs has been extended
            if ! $leg_is_restart || [ ! -d ${run_dir}/run${n} ]
            then
                # Make output directories
                mkdir -p ${run_dir}/run${n}/output

                # Copy *.ins, lpjg_steps.rc and OASIS-MCT restart files
                cp ${run_dir}/*.ins ${run_dir}/run${n}

                # Copy output control files
                cp ${output_control_files_dir}/lpjg_cmip6_output.ins ${run_dir}/run${n}
                ln -s ${output_control_files_dir}/lpjg_cmip6_output.ins ${run_dir}/run${n}/lpjg_cmip6_output.ins.lnk

                cp ${ini_data_dir}/lpjg/oasismct/ghg*.txt ${run_dir}/run${n}
                cp ${ini_data_dir}/lpjg/oasismct/${lpjg_res}/ece_gridlist_${lpjg_res}.txt ${run_dir}/run${n}/ece_gridlist.txt
                ln -s ${ini_data_dir}/lpjg/oasismct/${lpjg_res}/ece_gridlist_${lpjg_res}.txt ${run_dir}/run${n}/ece_gridlist.txt.lnk

                # Data only needed by master
                if [ $n == 1 ]
                then
                    cp ${ini_data_dir}/lpjg/oasismct/${lpjg_res}/*.nc ${run_dir}
                    cp ${ini_data_dir}/lpjg/oasismct/lpjgv.txt ${run_dir}/run${n}
                fi
            fi
            # Refresh output-dirs after they hav been removed at end of the last leg
            mkdir -p ${run_dir}/run${n}/output/CMIP6
            mkdir -p ${run_dir}/run${n}/output/CRESCENDO
        done

        if $leg_is_restart
        then
            lpjg_restart_dir="restart/lpjg/$(printf %03d $((leg_number-1)))"
            lpjg_rst_state="${lpjg_restart_dir}/lpjg_state_${leg_start_date_yyyy}"
            if [ -d "$lpjg_rst_state" ]
            then
                ln -sf $lpjg_rst_state
            else
                echo "lpjg restart dir $lpjg_rst_state not available"
                exit -1
            fi
        fi
    fi


    # -------------------------------------------------------------------------
    # *** Create ICMCL file with vegetation fields
    #     not needed if LPJG is used with feedback
    # -------------------------------------------------------------------------
    tempfile=tmp.$$

    case ${ifs_veg_source} in
    "ifs" )
        # Vegetation from IFS (climatology)

        icmclfile=${ini_data_dir}/ifs/${ifs_grid}/climate/ICMCL_ONLY_VEG_PD

        # Create data for december, the year before the leg starts
        ${grib_set} \
            -s dataDate=$(printf "%04d" $((leg_start_date_yyyy-1)))1215 \
            ${icmclfile}-12 ICMCL${exp_name}INIT

        # Create data for all month in the years of the leg
        for (( y=${leg_start_date_yyyy} ; y<=${leg_end_date_yyyy} ; y++ ))
        do
            yy=$(printf "%04d" $y)
            for m in {1..12}
            do
                mm=$(printf "%02d" $m)
                ${grib_set} -s dataDate=${yy}${mm}15 ${icmclfile}-${mm} ${tempfile}
                cat ${tempfile} >> ICMCL${exp_name}INIT
            done
        done

        # Create data for january, the year after the leg ends
        ${grib_set} \
            -s dataDate=$(printf "%04d" $((leg_end_date_yyyy+1)))0115 \
            ${icmclfile}-01 ${tempfile}
        cat ${tempfile} >> ICMCL${exp_name}INIT
        ;;
    "era20c"|"cmip6"|"custom_"* )
        # Vegetation from a LPJG run (off-line or EC-Earth3-Veg)

        rm -f ICMCL${exp_name}INIT

        # Create data for all years of the leg, including one year
        # before and one year after
        for (( yr=leg_start_date_yyyy-1 ; yr<=leg_end_date_yyyy+1 ; yr+=1 ))
        do

            case ${ifs_veg_source} in
            'era20c' )
                # no scenario needed with era20c
                icmcl_scenario="" ;;
            'custom_'* )
                # no scenario implemented yet with custom_dir
                icmcl_scenario="" ;;
            'cmip6' )
                # select scenario, use SSP3-7.0 as default
                # if not otherwise specified
                icmcl_scenario="historical"
                if ( [ $ifs_cmip_fixyear -le 0 ] && [ $yr -ge 2015 ] ) || \
                     [ $ifs_cmip_fixyear -ge 2015 ]
                then
                    [[ ${ifs_cmip6_scenario} =~ ^SSP ]] \
                        && icmcl_scenario=${ifs_cmip6_scenario} \
                        || if [ ${ifs_covid19}  == TRUE ]
                           then
                               icmcl_scenario='SSP2-4.5'
                           else
                               icmcl_scenario='SSP3-7.0'
                           fi
                fi ;;
            esac
            
            if [ $ifs_cmip_fixyear -le 0 ] || [[ ${ifs_veg_source} == custom_* ]]
            then
                cat ${ini_data_dir}/ifs/${ifs_grid}/icmcl_${veg_version}/${icmcl_scenario}/icmcl_$yr.grb >> ICMCL${exp_name}INIT
            else
                # Fixed year forcing, requires cdo! (only when not using ifs_veg_source=custom_exp*)
                # If cdo is not available at runtime you need to fix proper
                # icmcl files beforehand and use them here
                cdo setyear,$yr ${ini_data_dir}/ifs/${ifs_grid}/icmcl_${veg_version}/${icmcl_scenario}/icmcl_${ifs_cmip_fixyear}.grb ${tempfile}
                cat ${tempfile} >> ICMCL${exp_name}INIT
            fi
        done
        ;;
    "none" )
        info "no ICMCL file is created"
        ;;
    * )
        error "Vegetation from ${ifs_veg_source} not implemented"
        ;;
    esac

    # Clean up
    rm -f ${tempfile}

    # -------------------------------------------------------------------------
    # *** Link the appropriate NEMO restart files of the previous leg
    # -------------------------------------------------------------------------
    if $leg_is_restart && $(has_config nemo)
    then
        ns=$(printf %08d $(( leg_start_sec / nem_time_step_sec - nem_restart_offset )))
        for (( n=0 ; n<nem_numproc ; n++ ))
        do
            np=$(printf %04d ${n})
            ln -fs ${exp_name}_${ns}_restart_oce_${np}.nc restart_oce_${np}.nc
            ln -fs ${exp_name}_${ns}_restart_ice_${np}.nc restart_ice_${np}.nc
            has_config pisces && \
                ln -fs ${exp_name}_${ns}_restart_trc_${np}.nc restart_trc_${np}.nc
        done

        # Make sure there are no global restart files
        # If links are found, they will be removed. We are cautious and do
        # _not_ remove real files! However, if real global restart files are
        # present, NEMO/LIM will stop because time stamps will not match.
        [ -h restart_oce.nc ] && rm restart_oce.nc
        [ -h restart_ice.nc ] && rm restart_ice.nc
        [ -h restart_trc.nc ] && rm restart_trc.nc
    fi

    # -------------------------------------------------------------------------
    # *** Remove some OASIS files of the previous leg
    # -------------------------------------------------------------------------
    if $leg_is_restart
    then
        rm -f anaisout_*
    fi

    # -------------------------------------------------------------------------
    # *** Remove any ccycle debug output files
    # -------------------------------------------------------------------------
    if ${ccycle_debug_fluxes} && $leg_is_restart && $(has_config tm5:co2)
    then
      if $(has_config lpjg)
      then
          rm -f GUE_{CNAT,CANT,CNPP}_*.nc run1/GUE_{CNAT,CANT,CNPP}_*.nc
          rm -f TM5_Land{CNAT,CANT,CNPP}_*.nc
      fi
      if $(has_config pisces)
      then
          rm -f O_CO2FLX_*.nc
          rm -f TM5_OceCFLX_*.nc
      fi
    fi

    # -------------------------------------------------------------------------
    # *** Restart sanity check before launch
    # -------------------------------------------------------------------------
    # This code must run before launch command don't put anything in between

    echo "Restart files sanity check before launch:"
    if $leg_is_restart  ; then
      # oasis
      for oasis_restart_file in $(ls restart/oasis/$(printf %03d $((leg_number)))/*); do
        [ -n "$( diff $(basename ${oasis_restart_file}) ${oasis_restart_file} -q )" ] && \
        cp -f ${oasis_restart_file} . || true
      done
      # ifs rcf
      rcf_restart_file=restart/ifs/$(printf %03d $((leg_number)))/rcf
      [ -n "$(diff $(basename ${rcf_restart_file}) ${rcf_restart_file} -q )" ] && \
      cp -f ${rcf_restart_file} . || true
    fi
    # -------------------------------------------------------------------------
    # *** End restart sanity check before launch
    # -------------------------------------------------------------------------
    # -------------------------------------------------------------------------
    # *** Start the run
    # -------------------------------------------------------------------------
    export DR_HOOK_IGNORE_SIGNALS='-1'
    export CPLNG='active'

    # Use the launch function from the platform configuration file
    has_config nemo && \
        cmd="${xio_numproc} ${xio_exe_file} -- \
             ${nem_numproc} ${nem_exe_file} -- \
             ${ifs_numproc} ${ifs_exe_file} -v ecmwf -e ${exp_name}" || \
        cmd="${ifs_numproc} ${ifs_exe_file} -v ecmwf -e ${exp_name}"

    has_config lpjg && cmd=${cmd}" -- ${lpjg_numproc} ${lpjg_exe_file} guess.ins -parallel"
    has_config tm5  && cmd=${cmd}" -- ${tm5_numproc}  ${tm5_exe_file} tm5-run.rc"
    has_config amip && cmd=${cmd}" -- ${amip_numproc} ${amip_exe_file}"
    has_config nemo && cmd=${cmd}" -- ${rnf_numproc} ${rnf_exe_file}" 

    t1=$(date +%s)
    launch $cmd
    t2=$(date +%s)

    tr=$(date -d "0 -$t1 sec + $t2 sec" +%T)

    # -------------------------------------------------------------------------
    # *** Check for signs of success
    #     Note the tests provide no guarantee that things went fine! They are
    #     just based on the IFS, NEMO and TM5 log files. More tests (e.g. checking
    #     restart files) could be implemented.
    # -------------------------------------------------------------------------

    # Checking for IFS success
    if [ -f ifs.stat ]
    then
        if [ "$(awk 'END{print $3}' ifs.stat)" == "CNT0" ]
        then
            info "Leg successfully completed according to IFS log file 'ifs.stat'."
        else
            error "Leg not completed according to IFS log file 'ifs.stat'."
        fi
    else
        error "IFS log file 'ifs.stat' not found after run."
    fi

    # Check for NEMO success
    if $(has_config nemo)
    then
        if [ -f ocean.output ]
        then
            if [ "$(sed -n '/New day/h; ${g;s:.*\([0-9/]\{10\}\).*:\1:;p;}' ocean.output)" == "$(date -u -d "${leg_end_date} - 1 day" +%Y/%m/%d)" ]
            then
                info "Leg successfully completed according to NEMO log file 'ocean.output'."
            else
                error "Leg not completed according to NEMO log file 'ocean.output'."
            fi
        else
            error "NEMO log file 'ocean.output' not found after run."
        fi
    fi

    # Check for TM5 success
    if $(has_config tm5)
    then
        if [ -f tm5.ok ]
        then
            info "Leg successfully completed according to existing TM5 file 'tm5.ok'."
        else
            error "Leg not completed according to non-existing TM5 file 'tm5.ok'."
        fi
    fi

    # -------------------------------------------------------------------------
    # *** Post-process initial conditions saved during the run if requested
    # -------------------------------------------------------------------------
    ${do_save_ic} && save_ic_postproc

    # -------------------------------------------------------------------------
    # *** Move IFS output files to archive directory
    # -------------------------------------------------------------------------
    outdir="output/ifs/$(printf %03d $((leg_number)))"
    mkdir -p ${outdir}

    prv_leg=$(printf %03d $((leg_number-1)))

    # This takes care of a special IFS feature: The output for the last time
    # step of each leg is written at the first time step of the new leg. The
    # following code makes sure that the output is appended to the appropriate
    # file. Since GRIB files are just streams, its done with a simple cat
    # command.
    for f in ICMSH${exp_name}+?????? ICMGG${exp_name}+??????
    do
        if [ -f output/ifs/${prv_leg}/${f} ]
        then
            cat ${f} >> output/ifs/${prv_leg}/${f}
            rm -f ${f}
        else
            mv ${f} ${outdir}
        fi
    done

    # -------------------------------------------------------------------------
    # *** Move NEMO output files to archive directory
    # -------------------------------------------------------------------------
    if $(has_config nemo)
    then
        outdir="output/nemo/$(printf %03d $((leg_number)))"
        mkdir -p ${outdir}

        for v in grid_U grid_V grid_W grid_T icemod SBC scalar SBC_scalar diad_T ptrc_T bioscalar \
                 grid_T_2D grid_U_2D grid_V_2D grid_W_2D grid_T_3D grid_U_3D grid_V_3D grid_W_3D \
                 grid_T_SFC grid_1point grid_T_3D_ncatice vert_sum \
                 grid_ptr_W_3basin_3D grid_ptr_T_3basin_2D grid_ptr_T_2D \
                 zoom_700_sum zoom_300_sum zoom_2000_sum
        do
            for f in ${exp_name}_*_????????_????????_*${v}.nc
            do
                test -f $f && mv $f $outdir/
            done
        done
    fi

    # -------------------------------------------------------------------------
    # *** Move LPJ-GUESS output files to archive directory
    # -------------------------------------------------------------------------
    if $(has_config lpjg)
    then
        outdir="output/lpjg/$(printf %03d $((leg_number)))"
        if [ -d ${outdir} ]
        then
            rm -rf  ${outdir}
        fi
        mkdir -p ${outdir}

        # LPJG run directories
        # concatenate *.out (or compressed *.out.gz) files from each run* into output dir
        flist=$(cd ${run_dir}/run1/output && find *.out.gz -type f 2>/dev/null || true)
        if [ "$flist" = "" ]
        then
            lpjg_compress_output=false
            flist=$(cd ${run_dir}/run1/output && find *.out -type f 2>/dev/null)
        else
            lpjg_compress_output=true
        fi

        mkdir ${outdir}/CMIP6

        for (( n=1; n<=${lpjg_numproc}; n++ ))
        do
            for ofile in $flist
            do
                if $lpjg_compress_output
                then
                    [ $n == 1 ] && gzip -c ${run_dir}/run${n}/output/`basename ${ofile} .gz`.hdr > ${outdir}/$ofile
                    cat ${run_dir}/run${n}/output/${ofile} >> ${outdir}/$ofile
                else
                    if (( n == 1 ))
                    then
                        cat ${run_dir}/run${n}/output/${ofile} > ${outdir}/$ofile
                    else
                        awk '(FNR!=1){print $0}' ${run_dir}/run${n}/output/${ofile} >> ${outdir}/$ofile
                    fi
                fi
            done
            rm -rf ${run_dir}/run${n}/output
        done
        
        # move monthly file if available
        if [ -f ${run_dir}/LPJ-GUESS_monthlyoutput.txt ]
        then
            mv ${run_dir}/LPJ-GUESS_monthlyoutput.txt ${outdir}
        fi
    fi

    # -------------------------------------------------------------------------
    # *** Move TM5 output files to archive directory
    # -------------------------------------------------------------------------
    if $(has_config tm5)
    then
        outdir="output/tm5/$(printf %03d $((leg_number)))"
        mkdir -p ${outdir}

        set +e
        mv budget_??????????_??????????_global.hdf      ${outdir}
        mv j_statistics_??????????_??????????.hdf       ${outdir}
        mv mmix_??????????_??????????_glb???x???.hdf    ${outdir}
        mv aerocom?_TM5_*_????????_daily.nc             ${outdir}
        mv aerocom?_TM5_*_??????_monthly.nc             ${outdir}
        mv AOD_????_??_??.nc                            ${outdir}
        mv -f TM5MP_${exp_name}_griddef.nc              ${outdir}
        mv TM5MP_${exp_name}_TP_????_??_??.nc           ${outdir}
        mv TM5MP_${exp_name}_vmr3_????_??_??.nc         ${outdir}
        mv general_TM5_${exp_name}_??????????_hourly.nc ${outdir}
        mv general_TM5_${exp_name}_??????_monthly.nc    ${outdir}
        mv *EC-Earth3-*_${exp_name}_*.nc                ${outdir}
        set -e

        # move profiling files if any
        if [ "$(ls -A ${run_dir}/tm5_profile)" ]
        then
            outdir="output/tm5/profile_$(printf %03d $((leg_number)))"
            mkdir -p ${outdir}

            for f in ${run_dir}/tm5_profile/*
            do
                test -f ${f} && mv $f ${outdir}
            done
        fi
    fi

    # -------------------------------------------------------------------------
    # *** Move IFS restart files to archive directory
    # -------------------------------------------------------------------------
    if $leg_is_restart
    then
        outdir="restart/ifs/$(printf %03d $((leg_number)))"
        mkdir -p ${outdir}

        # Figure out the time part of the restart files (cf. CTIME on rcf files)
        # NOTE: Assuming that restarts are at full days (time=0000) only!
        nd="$(printf %06d $((leg_start_sec/(24*3600))))0000"

        mv srf${nd}.???? ${outdir}

    fi

    # -------------------------------------------------------------------------
    # *** Move ccycle debug output files to archive directory
    # -------------------------------------------------------------------------
    if ${ccycle_debug_fluxes} && $(has_config tm5:co2)
    then
      outdir="output/tm5/$(printf %03d $((leg_number)))"
      mkdir -p ${outdir}
      if $(has_config lpjg)
      then
          for f in CNAT CANT CNPP ; do
              mv TM5_Land${f}_*.nc ${outdir}
              rm -f GUE_${f}_*.nc run1/GUE_${f}_*.nc
              #gf=`ls -1 GUE_${f}_*.nc | head -n 1`
              #cdo mergetime ${gf} run1/${gf} ${outdir}/${gf}
          done
      fi
      if $(has_config pisces)
      then
          mv TM5_OceCFLX_*.nc ${outdir}
          rm -f O_CO2FLX_*.nc
          #mv O_CO2FLX_*.nc ${outdir}
      fi
    fi

    # -------------------------------------------------------------------------
    # *** Move LPJ-GUESS restart files to archive directory
    # -------------------------------------------------------------------------
    if $(has_config lpjg)
    then
        outdir="restart/lpjg/$(printf %03d $((leg_number)))"
        if [ -d ${outdir} ]
        then
            rm -rf  ${outdir}
        fi
        mkdir -p ${outdir}

        state_dir="./lpjg_state_$(printf %04d $((leg_end_date_yyyy)))"
        mv ${state_dir} ${outdir}
        # LPJG writes into run1 dir, so mv to main rundir
        mv -f run1/lpjgv.nc .
        has_config tm5:co2 lpjg && mv -f run1/rlpjg.nc .

        # remove restart link
        if $leg_is_restart
        then
            old_state_dir="./lpjg_state_$(printf %04d $((leg_start_date_yyyy)))"
            if [ -L $old_state_dir ]
            then
                rm -f "$old_state_dir"
            fi
        fi
    fi

    # -------------------------------------------------------------------------
    # *** Move NEMO restart files to archive directory
    # -------------------------------------------------------------------------
    if $leg_is_restart && $(has_config nemo)
    then
        outdir="restart/nemo/$(printf %03d $((leg_number)))"
        mkdir -p ${outdir}

        ns=$(printf %08d $(( leg_start_sec / nem_time_step_sec - nem_restart_offset )))
        for f in oce ice
        do
            mv ${exp_name}_${ns}_restart_${f}_????.nc ${outdir}
        done

        if has_config pisces
        then
            mv ${exp_name}_${ns}_restart_trc_????.nc ${outdir}
        fi
    fi

    # -------------------------------------------------------------------------
    # *** Move TM5 restart file to archive directory
    # -------------------------------------------------------------------------
    if $leg_is_restart && $(has_config tm5)
    then
        outdir="restart/tm5/$(printf %03d $((leg_number)))"
        mkdir -p ${outdir}

        case ${tm5_istart} in
            33|32) f=TM5_restart_${leg_start_date_yyyymmdd}_0000_glb300x200.nc
                ;;
            31) f=save_${leg_start_date_yyyymmdd}00_glb300x200.hdf
                ;;
        esac

        mv $f ${outdir}
    fi

    # -------------------------------------------------------------------------
    # *** Copy OASIS restart files to archive directory
    #     NOTE: These files are copied and not moved as they are used in the
    #           next leg!
    #           Note also that the OASIS restart files present at the end of
    #           the leg correspond to the start of the next leg!
    # -------------------------------------------------------------------------
    outdir="restart/oasis/$(printf %03d $((leg_number+1)))"
    mkdir -p ${outdir}

    for f in ${oas_rst_files}
    do
        test -f ${f} && cp ${f} ${outdir}
    done

    # -------------------------------------------------------------------------
    # *** Copy rcf files to the archive directory (of the next leg!)
    # -------------------------------------------------------------------------
    outdir="restart/ifs/$(printf %03d $((leg_number+1)))"
    mkdir -p ${outdir}

    for f in rcf
    do
        test -f ${f} && cp ${f} ${outdir}
    done

    # -------------------------------------------------------------------------
    # *** Move log files to archive directory
    # -------------------------------------------------------------------------
    outdir="log/$(printf %03d $((leg_number)))"
    mkdir -p ${outdir}

    for f in \
        ifs.log ifs.stat fort.4 ocean.output \
        time.step solver.stat guess.log run1/guess0.log \
        amip.log namelist.amip \
        nout.000000 debug.root.?? debug.??.?????? lucia.??.?????? \
        ctm.tm5.log.0
    do
        test -f ${f} && mv ${f} ${outdir}
    done
    has_config pisces && cp ocean.carbon ${outdir}

    for f in ctm.tm5.log.*
    do
        if [[ -f ${f} ]]
        then
            [[ -s ${f} ]] && mv ${f} ${outdir} || \rm -f ${f}
        fi
    done

    # -------------------------------------------------------------------------
    # *** Write the restart control file
    # -------------------------------------------------------------------------

    # Compute CPMIP performance
    sypd="$(cpmip_sypd $leg_length_sec $(($t2 - $t1)))"
    ncores=0
    has_config nemo      && (( ncores+=${nem_numproc}  )) || :
    has_config ifs       && (( ncores+=${ifs_numproc}  )) || :
    has_config xios      && (( ncores+=${xio_numproc}  )) || :
    has_config rnfmapper && (( ncores+=${rnf_numproc}  )) || :
    has_config lpjg      && (( ncores+=${lpjg_numproc} )) || :
    has_config tm5       && (( ncores+=${tm5_numproc}  )) || :
    has_config amip      && (( ncores+=${amip_numproc} )) || :
    chpsy="$(cpmip_chpsy  $leg_length_sec $(($t2 - $t1)) $ncores)"

    echo "#"                                             | tee -a ${ece_info_file}
    echo "# Finished leg at `date '+%F %T'` after ${tr} (hh:mm:ss)" \
                                                         | tee -a ${ece_info_file}
    echo "# CPMIP performance: $sypd SYPD   $chpsy CHPSY"| tee -a ${ece_info_file}
    echo "leg_number=${leg_number}"                      | tee -a ${ece_info_file}
    echo "leg_start_date=\"${leg_start_date}\""          | tee -a ${ece_info_file}
    echo "leg_end_date=\"${leg_end_date}\""              | tee -a ${ece_info_file}

    # Need to reset force_run_from_scratch in order to avoid destroying the next leg
    force_run_from_scratch=false

done # loop over legs

# -----------------------------------------------------------------------------
# *** Platform dependent finalising of the run
# -----------------------------------------------------------------------------
finalise

###################
# Autosubmit tailer
###################
set -xuve
echo $(date +%s) >> ${job_name_ptrn}_STAT
touch ${job_name_ptrn}_COMPLETED
exit 0

