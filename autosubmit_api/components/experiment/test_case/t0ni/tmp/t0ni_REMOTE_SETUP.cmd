#!/bin/bash

###############################################################################
#                   REMOTE_SETUP t0ni EXPERIMENT
###############################################################################
#
#SBATCH --qos=bsc_es
#SBATCH -A bsc32
#
#
#
#SBATCH --cpus-per-task=1
#SBATCH -n 4
#SBATCH -t 2:00:00
#SBATCH -J t0ni_REMOTE_SETUP
#SBATCH --output=/gpfs/scratch/bsc32/bsc32627/t0ni/LOG_t0ni/t0ni_REMOTE_SETUP.cmd.out
#SBATCH --error=/gpfs/scratch/bsc32/bsc32627/t0ni/LOG_t0ni/t0ni_REMOTE_SETUP.cmd.err
#SBATCH -p interactive
#
###############################################################################
###################
# Autosubmit header
###################
set -xuve
job_name_ptrn='/gpfs/scratch/bsc32/bsc32627/t0ni/LOG_t0ni/t0ni_REMOTE_SETUP'
echo $(date +%s) > ${job_name_ptrn}_STAT

###################
# Autosubmit job
###################

#!/usr/bin/env bash
# remote_setup.sh:
# Extracts the sources from the Autosubmit project bundle and compiles EC-Earth

set -xuve

#
# Architecture
#

HPCARCH=marenostrum4
CURRENT_ROOTDIR=/gpfs/scratch/bsc32/bsc32627/t0ni
PROJECT_DESTINATION=auto-ecearth3
PROJECT_DIR=${CURRENT_ROOTDIR}/${PROJECT_DESTINATION}
TEMPLATE_NAME=ecearth3
IFS_resolution=T511L91
MAKE_NUMPROC=4
PROJDIR=/esarchive/autosubmit/t0ni/proj/auto-ecearth3
BSC_OUTCLASS=reduced
CMIP6_OUTCLASS=
PRODUCTION_EXP=FALSE
PRECOMPILED_VERSION=
TM5_NLEVS=34

# ==================================================
# functions
# ==================================================

function get_configuration_nemo (){
    NEMO_resolution=ORCA025L75
    if [[ -z ${NEMO_resolution-} ]] ; then
        echo "ERROR: nemo is requested but NEMO_resolution is not defined!"
        exit 1
    fi

    # Select correct nemo_config
    has_config pisces:offline ifs && echo "ERROR: cannot have pisces:offline and ifs in config!" && exit 1

    # this code adheres to the conventions in ece-esm.sh
    nem_grid=ORCA025L75

    nem_config=${nem_grid}
    has_config lim3           && nem_config=${nem_config}_LIM3
    has_config pisces:offline && nem_config=${nem_config}_OFF

    if $(has_config pisces tm5:co2) ; then
        nem_config=${nem_config}_CarbonCycle
    elif $(has_config pisces) ; then
        nem_config=${nem_config}_PISCES
    fi

    # TODO - nemo standalone configs are not accounted for in this script, but this would set the required nem_config
    ! has_config ifs && nem_config=${nem_config}_standalone

    NEMO_CONFIG=${nem_config}
}


function compile_nemo(){

    ########################
    # NEMO compilation key #
    ########################

    # Configuration to be compiled
    nemo_config_to_compile=$1
    new_nemo_compilation_keys=" key_init_alloc_zero ${extra_nemo_compilation_keys-}"
    fcm_file=$(ls ${SOURCE_FOLDER}/nemo-3.6/CONFIG/${nemo_config_to_compile}/*.fcm)

    for key in ${new_nemo_compilation_keys}; do
        if [[ $(grep ${key} ${fcm_file}) == "" ]] ; then
          echo adding ${key}
          sed -i -e 1's/$/'" "${key}' &/' ${fcm_file}
        fi
    done


    cd ${SOURCE_FOLDER}/nemo-3.6/CONFIG
    # remove old nemo executable to make sure compilation did not fail
    # workaround for the issue that make_nemo does not return an exit code on failure
    rm -f ${SOURCE_FOLDER}/nemo*/CONFIG/${nemo_config_to_compile}/BLD/bin/*.exe
    if ${MODEL_CLEAN} ; then ./makenemo -m ecconf -n ${nemo_config_to_compile} -j ${MAKE_NUMPROC} clean ; fi
    ./makenemo -m ecconf -n ${nemo_config_to_compile} -j ${MAKE_NUMPROC}
    [ -f ${SOURCE_FOLDER}/nemo*/CONFIG/${nemo_config_to_compile}/BLD/bin/*.exe ] || exit 1
}

function compile_tm5(){

  local tm5_version=$1
  export TM5_NLEVS=$2
  if [[ ${tm5_version} == "co2" ]] ; then
    ecconf_args+=" -o MOD:TM5:CO2_ONLY=True"
  elif [[ ${tm5_version} == "cb05" ]] ; then
    ecconf_args+=" -o MOD:TM5:CO2_ONLY=False" ;
  fi
  ecconf_args+=" -o MOD:TM5:NLEVS="${TM5_NLEVS}
  export tm5_exch_nlevs=${TM5_NLEVS}

  cd ${SOURCE_FOLDER}
  util/ec-conf/ec-conf --platform ${architecture} ${ecconf_args} config-build.xml

  tm5_exe_file=${SOURCE_FOLDER}/tm5mp/build-${tm5_version}-ml${tm5_exch_nlevs}/appl-tm5-${tm5_version}.x
  cd ${SOURCE_FOLDER}/tm5mp/

  if [ ! -f ${SOURCE_FOLDER}/tm5mp/setup_tm5 ] ; then
    ln -sf ${SOURCE_FOLDER}/tm5mp/bin/pycasso_setup_tm5 ${SOURCE_FOLDER}/tm5mp/setup_tm5
    chmod 755 setup_tm5
  fi

  if ${MODEL_CLEAN} ; then
    ./setup_tm5 -c -n -v -j ${MAKE_NUMPROC} ecconfig-ecearth3.rc
  else
    ./setup_tm5       -v -j ${MAKE_NUMPROC} ecconfig-ecearth3.rc
  fi
  [ -f ${tm5_exe_file} ] || exit 1

}

function compile_lpjg(){
    ifs_res=$1
    lpjg_res=T$(echo ${ifs_res} | sed 's:T\([0-9]\+\)L\([0-9]\+\):\1:')
    if [ $lpjg_res != "T255" -a $lpjg_res != "T159" ]
    then
      echo "LPJG not supported for ifs-grid: ${ifs_res}"
      exit 1
    else
        ecconf_args+=" -o MOD:LPJG:GRID=$lpjg_res "
    fi
    cd ${SOURCE_FOLDER}
    util/ec-conf/ec-conf --platform ${architecture} ${ecconf_args} config-build.xml
    cd ${SOURCE_FOLDER}/lpjg/build
    if ${MODEL_CLEAN} ; then
      rm -f CMakeCache.txt ;
    fi
    cmake ..
    if ${MODEL_CLEAN} ; then
      make clean ;
    fi
    make -j ${MAKE_NUMPROC}
    [ -f ${SOURCE_FOLDER}/lpjg/build/guess_${lpjg_res} ] || exit 1

    cd ${SOURCE_FOLDER}/lpjg/offline
    if ${MODEL_CLEAN} ; then
      make clean
    fi
    make
    [ -f ${SOURCE_FOLDER}/lpjg/offline/lpjg_forcing_ifs_${lpjg_res} ] || exit 1
}


# define which runtime we are using
use_autosubmit=true
[[ use_autosubmit && ${PROJECT_DESTINATION} == 'ecearth3' ]] && use_autosubmit_simple=true || use_autosubmit_simple=false
#when using the simplified AS runtime we use the same ECEARTH_SRC_DIR definition
#as in the full auto-ecearth AS runtime, to avoid having to change it in config-build and config-run
#TODO set PROJECT_DIR from ECEARTH_SRC_DIR, requires writing this script as an ec-conf template
if $use_autosubmit_simple ; then
  SOURCE_FOLDER=${CURRENT_ROOTDIR}/auto-ecearth3/sources/sources
else
  SOURCE_FOLDER=${PROJECT_DIR}/sources/sources
fi

# Variables that could be used from config-build.xml should be exported
export exp_name=t0ni

# these variables are to be used for development, allowing to retain any local
# changes to the sources and compile the model more quickly
# EXTRACT : extract files from uploaded .tar.gz file and copy runtime files (default:true)
# CLEAN   : do 'make clean' for all model components (default:true)
[ "TRUE" = FALSE ] && MODEL_EXTRACT=false || MODEL_EXTRACT=true
[ "TRUE" = FALSE ] && MODEL_CLEAN=false || MODEL_CLEAN=true

#
# get model config from AS variables (for compilation only)
#
#ifs
[[ "$TEMPLATE_NAME" = ecearth3* || "$TEMPLATE_NAME" = ifs3* ]] && ifs="ifs" || ifs=""
[[ "$TEMPLATE_NAME" = ifs3* ]] && amip="amip" ||  amip=""
#nemo
if [[ "$TEMPLATE_NAME" = ecearth3* || "$TEMPLATE_NAME" = nemo3* ]]; then nemo="nemo"; lim3="lim3"; xios="xios:detached"; else nemo=""; lim3=""; xios=""; fi
[[ "$TEMPLATE_NAME" = ecearth3* ]] && rnfmapper="rnfmapper" || rnfmapper=""
[[ "TRUE" = TRUE && ! -z $nemo ]] && elpin=":elpin" || elpin=""
[[ "FALSE" = TRUE ]] && { if [[ "FALSE" = TRUE ]] ; then pisces="pisces:offline" ; lim3="" ; else pisces="pisces" ; fi } || pisces=""
#others
[[ "$TEMPLATE_NAME" = lsm* || "FALSE" = TRUE ]] && lpjg=lpjg:fdbck || lpjg=""
[[ "$TEMPLATE_NAME" = lsm* || "FALSE" = TRUE ]] && osm="osm" || osm=""
[[ "FALSE" = TRUE ]] && tm5=tm5:chem,o3fb,ch4fb,aerfb || tm5=""
export config="${ifs} ${amip} ${nemo}${elpin} ${pisces} ${lim3} ${rnfmapper} ${xios} oasis ${lpjg} ${osm} ${tm5}"

#####################################################################################
# To re-define the components you want to build
#####################################################################################
# you can set here the components you want to build by uncommenting a line such as these
#config="ifs amip nemo pisces lim3 rnfmapper xios oasis lpjg ${tm5}" # for all components (esm runtime)
#config="osm oasis lpjg" # for lsm configuration

#####################################################################################
# 3.3.3.1 - To compile all components #
#####################################################################################
# Uncomment these lines to compile all components and all nemo resolutions and LPJG/TM5 versions
#config=compile_all
#PRECOMPILED_VERSION="NONE"
#PRODUCTION_EXP=TRUE
#

[[ -z ${PRECOMPILED_VERSION-} ]] && PRECOMPILED_VERSION="NONE"

#
# Loading of modules
#

set +xuve
export ecconf_args=""

if [ ${HPCARCH} == 'ecmwf-xc40' ]
then
  export architecture=ecmwf-cca-intel-mpi
  prgenvswitchto intel
  module load cray-hdf5-parallel/1.8.14
  module load cray-netcdf-hdf5parallel/4.3.3.1
  module unload eccodes
  module load grib_api/1.27.0

  # for tm5
  if has_config any compile_all tm5 ; then
    module load udunits
    module load hdf
  fi

  # for lpjg
  if has_config any compile_all lpjg ; then
    module load cmake
  fi
  rm -f ${CURRENT_ROOTDIR}/${PROJECT_DESTINATION}/sources/util/grib_table_126/define_table_126.sh
  export ecconf_args+=" -o PLT:ACTIVE:ECEARTH_SRC_DIR=${SCRATCH}/${exp_name}/auto-ecearth3/sources/sources" ;

elif [ ${HPCARCH} == 'nord3' ]
then
  export SCRATCH=/gpfs/scratch/`id -gn`/${USER}
  export architecture=bsc-nord3-intel-intelmpi
  module unload intel
  module load intel/2017.1

elif [ ${HPCARCH} == 'marenostrum4' ] ;  then
  export SCRATCH=/gpfs/scratch/`id -gn`/${USER}
  export architecture=bsc-marenostrum4-intel-intelmpi
  module purge
  module load intel/2017.4
  module load impi/2018.4
  module load perl/5.26
  module load mkl/2018.4 # require by python/2.7.14
  module load python/2.7.14
  # for lpjg
  if has_config any lpjg compile_all ; then
    module load cmake
    module load grib/1.14.0
  fi
 if [[ ${PRODUCTION_EXP-} == "TRUE" ]] ; then
    ecconf_args+='-o PLT:ACTIVE:OASIS_ADD_FFLAGS="-132" -o  PLT:ACTIVE:NEMO_ADD_FFLAGS="-fpe0" '
  fi
else
    error "Unsupported ec-conf architechture: ${HPCARCH}"
    exit 0
fi

module list
set -xuve

#
# Extract Model Sources and copy runtime, only if MODEL_EXTRACT=TRUE
#

if ${MODEL_EXTRACT} ; then
  #
  # Extract Model Sources
  #
  cd ${CURRENT_ROOTDIR}
  if [ -f ${PROJECT_DESTINATION}.tar.gz ]; then
    tar -xvf ${PROJECT_DESTINATION}.tar.gz
    rm ${PROJECT_DESTINATION}.tar.gz
    # move sources into auto-ecearth3/sources to make it consistent with ECEARTH_SRC_DIR
    if $use_autosubmit_simple
    then
        mkdir -p ${CURRENT_ROOTDIR}/auto-ecearth3
        mv ${PROJECT_DESTINATION} ${CURRENT_ROOTDIR}/auto-ecearth3/sources
        ln -sf ${CURRENT_ROOTDIR}/auto-ecearth3 ${PROJECT_DESTINATION}
    fi
  fi

  #
  # Copy runtime
  # TODO check if we can link instead of copy
  #
  cd ${CURRENT_ROOTDIR}
  ln -sf ${PROJECT_DESTINATION}/sources/runtime/autosubmit/ecconf.cfg .
  for ctrlfile in `( ls ${PROJECT_DESTINATION}/sources/runtime/classic/lib*.sh )`
  do
    ln -sf ${ctrlfile} .
  done
  ln -sf ${PROJECT_DESTINATION}/sources/runtime/classic/ctrl/ .

fi # $MODEL_EXTRACT

#
# librunscript defines some helper functions
#
source ${CURRENT_ROOTDIR}/librunscript.sh
# check for extra nemo compilation keys
extra_nemo_compilation_keys=""

# check for extra compilation keys for chosen BSC_OUTCLASS
if [[ -n "${BSC_OUTCLASS-}" && -d ${PROJECT_DESTINATION}/outclass/${BSC_OUTCLASS}/ ]]; then
    [ -f ${PROJECT_DESTINATION}/outclass/${BSC_OUTCLASS}/outclass_extra_nemo_compilation_keys.fcm ] && extra_nemo_compilation_keys+=" "$(cat ${PROJECT_DESTINATION}/outclass/${BSC_OUTCLASS}/outclass_extra_nemo_compilation_keys.fcm)
fi

# check if the experiment has an historical outclass and pisces is activated (requires key_cfc)
has_config pisces && [[ "piControl" = "historical" || "piControl" = "esm-hist" ]] && extra_nemo_compilation_keys+=" key_cfc "

# make sure we are not using precompiled binaries or compiling all binaries if special keys are necessary
# or maybe ignore the keys if we are compiling all?
if [[ "${extra_nemo_compilation_keys}" != "" ]] ; then
    has_config compile_all && [[ "${PRECOMPILED_VERSION-}" = "NONE" ]] && DO_EXIT="TRUE"
    if [[ "${PRECOMPILED_VERSION-}" != "NONE"  || "${DO_EXIT-}" == "TRUE" ]] ; then
        echo "PRECOMPILED_VERSION or compile_all not compatible with pisces historical runs or BSC_OUTCLASS with extra compilation keys"
        exit 1
    fi
fi

# report if no outclass was chosen
if [[ "${BSC_OUTCLASS-}" == "" ]] && [[ "${CMIP6_OUTCLASS-}" == "" ]] ; then
    echo "WARNING: you are using the outclass from ec-earth portal"
fi

if [[ "${PRECOMPILED_VERSION-}" == "NONE" ]] ; then

  cd ${SOURCE_FOLDER}
  util/ec-conf/ec-conf --platform ${architecture} ${ecconf_args} config-build.xml

  #
  # Check bin and lib directory (git-svn issue with empty folders)
  #
  cd ${SOURCE_FOLDER}
  if [ ! -d ifs-36r4/bin ]; then
    mkdir ifs-36r4/bin
    mkdir ifs-36r4/lib
  fi
  if [ ! -d runoff-mapper/bin ] ; then
    mkdir runoff-mapper/bin
    mkdir runoff-mapper/lib
  fi
  if [ ! -d amip-forcing/bin ] ; then
    mkdir amip-forcing/bin
    mkdir amip-forcing/lib
  fi
  if [ ! -d lpjg/build ] ; then
    mkdir lpjg/build
  fi

  #
  # Compilation of Model Sources
  #

  # 1) OASIS
  if $(has_config any oasis compile_all) ; then
    cd ${SOURCE_FOLDER}/oasis3-mct/util/make_dir
    if ${MODEL_CLEAN} ; then
      make realclean -f TopMakefileOasis3 BUILD_ARCH=ecconf ;
    fi
    make -f TopMakefileOasis3 -j ${MAKE_NUMPROC} BUILD_ARCH=ecconf
    # build lucia with the ifort compiler - modify this if you use another compiler
    cd ${SOURCE_FOLDER}/oasis3-mct/util/lucia
    F90=ifort ./lucia -c
    [ -f ${SOURCE_FOLDER}/oasis3-mct/util/lucia/lucia.exe ] || exit 1
  fi

  # 2) XIOS
  if $(has_config any xios compile_all) ; then
    cd ${SOURCE_FOLDER}/xios-2.5
    if ${MODEL_CLEAN} ; then
      ./make_xios --arch ecconf --use_oasis oasis3_mct --netcdf_lib netcdf4_par --job ${MAKE_NUMPROC} --full
    else
      ./make_xios --arch ecconf --use_oasis oasis3_mct --netcdf_lib netcdf4_par --job ${MAKE_NUMPROC}
    fi
    [ -f ${SOURCE_FOLDER}/xios-2.5/bin/xios_server.exe ] || exit 1
  fi

  # 3) Runoff-Mapper
  if $(has_config any rnfmapper compile_all) ; then
    cd ${SOURCE_FOLDER}/runoff-mapper/src
    if ${MODEL_CLEAN} ; then
      make clean ;
    fi
    make
    [ -f ${SOURCE_FOLDER}/runoff-mapper/bin/runoff-mapper.exe ] || exit 1
  fi

  # 4) NEMO
  if $(has_config any compile_all nemo) ; then

    NEMO_resolution=ORCA025L75
    if [[ -z ${NEMO_resolution-} ]] ; then
        echo "ERROR: nemo is requested but NEMO_resolution is not defined!"
        exit 1
    fi
    has_config pisces && [[ "piControl" = "historical" || "piControl" = "esm-hist" ]] && new_nemo_compilation_keys+=" key_cfc "

    # Select correct nemo_config
    has_config pisces:offline ifs && echo "ERROR: cannot have pisces:offline and ifs in config!" && exit 1
    # Determine proper NEMO configuration
    get_configuration_nemo
    # compilation step
    if $(has_config compile_all) ; then
        for NEMO_CONFIG in ORCA025L75_LIM3  ORCA025L75_LIM3_standalone  ORCA1L75_LIM3  ORCA1L75_LIM3_CarbonCycle  ORCA1L75_LIM3_PISCES  ORCA1L75_LIM3_PISCES_standalone  ORCA1L75_LIM3_standalone  ORCA1L75_OFF_PISCES_standalone ; do
            compile_nemo $NEMO_CONFIG
        done
    else
      compile_nemo $NEMO_CONFIG
    fi
  fi

  # 5) IFS
  if $(has_config any ifs compile_all) ; then
    set +xuve
    . ${SOURCE_FOLDER}/util/grib_table_126/define_table_126.sh
    set -xuve
    cd ${SOURCE_FOLDER}/ifs-36r4
    if ${MODEL_CLEAN} ; then
      make clean BUILD_ARCH=ecconf
      make realclean BUILD_ARCH=ecconf
      make dep-clean BUILD_ARCH=ecconf
    fi
    make -j ${MAKE_NUMPROC} BUILD_ARCH=ecconf lib
    make BUILD_ARCH=ecconf master
    [ -f ${SOURCE_FOLDER}/ifs*/bin/ifsmaster* ] || exit 1
  fi

  # 6) Amip
  if $(has_config any amip compile_all); then
    cd ${SOURCE_FOLDER}/amip-forcing/src
    if ${MODEL_CLEAN} ; then
      make clean
    fi
    make
    [ -f ${SOURCE_FOLDER}/amip*/bin/amip* ] || exit 1
  fi

  # 7) LPJG component
  if $(has_config any lpjg compile_all); then
    if $(has_config compile_all) ; then
      compile_lpjg "T255L91"
      compile_lpjg "T159L91"
    elif $(has_config lpjg) ; then
      compile_lpjg $IFS_resolution
    fi
  fi

  # 8) TM5
  if $(has_config any tm5 compile_all); then
    if $(has_config compile_all) ; then
      compile_tm5 "co2" 10
      compile_tm5 "cb05" 34
    elif $(has_config tm5) ; then
      tmversion="cb05"
      has_config tm5:co2 && tmversion="co2"
      compile_tm5 ${tmversion} ${TM5_NLEVS}
    fi
  fi

  # 9) ELPiN
  if $(has_config any elpin compile_all) ; then
    cd ${SOURCE_FOLDER}/util/ELPiN/
    make clean
    make
  fi

  # 10) OSM
  if $(has_config any osm compile_all) ; then
    cd ${SOURCE_FOLDER}/ifs-36r4/src/surf/offline/
    if [ ${HPCARCH} == 'marenostrum4' ] ; then
        export PATH=/gpfs/projects/bsc32/share/fcm-2017.10.0/bin:$PATH
    else
        # this works on CCA...
        module load fcm
    fi
    if ${MODEL_CLEAN} ; then
        fcm make -vvv -j ${MAKE_NUMPROC} --new
    else
        fcm make -vvv -j ${MAKE_NUMPROC}
    fi
    [ -f ${SOURCE_FOLDER}/ifs*/src/surf/offline/osm/build/bin/master1s.exe ] || exit 1
  fi
  echo "Finished compiling"
  set +xuve
  #
  # workaround for intelremotemond process started when compiling with
  # intel compilers (maybe only on MN3 ?)
  #
  set +e
  if [ ${HPCARCH} == 'nord3' ] ; then
    (! pidof intelremotemond) || killall -u ${USER} intelremotemond ;
  fi

else

   echo "Your experiment will use a precompiled binary version:" ${PRECOMPILED_VERSION-}

   # create links to the binaries
   cd ${PROJECT_DIR}/sources
   path_to_precompiled=/gpfs/projects/bsc32/models/ecearth/${PRECOMPILED_VERSION-}/make/MN4-intel-opt/sources/sources
   # Get defined configurations
   arrComponents=()
   if $(has_config nemo) ; then
      get_configuration_nemo
      arrComponents+=(nemo)
      nemo_exe_file=${path_to_precompiled}/nemo-3.6/CONFIG/${NEMO_CONFIG}/BLD/bin/nemo.exe
      nemo_dst_dir=./sources/nemo-3.6/CONFIG/${NEMO_CONFIG}/BLD/bin/
   fi

   if $(has_config ifs) ; then
      arrComponents+=(ifs)
      ifs_exe_file=${path_to_precompiled}/ifs-36r4/bin/ifsmaster-ecconf
      ifs_dst_dir=./sources/ifs-36r4/bin/
   fi

   if $(has_config xios) ; then
      arrComponents+=(xios)
      xios_exe_file=${path_to_precompiled}/xios-2.5/bin/xios_server.exe
      xios_dst_dir=./sources/xios-2.5/bin/
   fi

   if $(has_config osm) ; then
      arrComponents+=(osm)
      osm_exe_file=${path_to_precompiled}/ifs-36r4/src/surf/offline/osm/build/bin/master1s_cpl.exe
      osm_dst_dir=./sources/ifs-36r4/src/surf/offline/osm/build/bin/
   fi

   if $(has_config elpin) ; then
      arrComponents+=(elpin)
      elpin_exe_file=${path_to_precompiled}/util/ELPiN/bin/mpp_domain_decomposition.exe
      elpin_dst_dir=./sources/util/ELPiN/bin/
   fi

   if $(has_config lpjg) ; then
      arrComponents+=(lpjg)
      lpjg_exe_file=${path_to_precompiled}/lpjg/build/guess_T$(echo ${IFS_resolution} | sed 's:T\([0-9]\+\)L\([0-9]\+\):\1:')
      lpjg_dst_dir=./sources/lpjg/build/
   fi

   if $(has_config tm5) ; then
      arrComponents+=(tm5)
      tmversion="cb05"
      has_config tm5:co2 && tmversion="co2"
      tm5_exe_file=${path_to_precompiled}/tm5mp/build-${tmversion}-ml${TM5_NLEVS}/appl-tm5-${tmversion}.x
      tm5_dst_dir=./sources/tm5mp/build-${tmversion}-ml${TM5_NLEVS}/
   fi

   if $(has_config rnfmapper) ; then
       arrComponents+=(runoff_mapper)
       runoff_mapper_exe_file=${path_to_precompiled}/runoff-mapper/bin/runoff-mapper.exe
       runoff_mapper_dst_dir=./sources/runoff-mapper/bin/
   fi

   if $(has_config amip) ; then
       arrComponents+=(amip)
       amip_exe_file=${path_to_precompiled}/amip-forcing/bin/amip-forcing.exe
       amip_dst_dir=./sources/amip-forcing/bin/
   fi

   for component in ${arrComponents[@]} ; do
       exe=${component}_exe_file
       dst=${component}_dst_dir
       # we copy only the binary
       if [[ ! -d ${!dst} ]] ; then
          mkdir -p ${!dst}
       fi
       cp -f ${!exe} ${!dst}
       # get the enclosing folder of the target binaries folder that was just copied
       ln -sf ${!exe} ${!dst}/$(basename ${!exe}).lnk
   done

fi

###################
# Autosubmit tailer
###################
set -xuve
echo $(date +%s) >> ${job_name_ptrn}_STAT
touch ${job_name_ptrn}_COMPLETED
exit 0

