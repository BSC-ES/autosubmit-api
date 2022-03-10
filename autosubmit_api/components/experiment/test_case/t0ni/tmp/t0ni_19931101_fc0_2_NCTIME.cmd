#!/bin/bash

###############################################################################
#                   NCTIME t0ni EXPERIMENT
###############################################################################
#
#BSUB -q bsc_es
#BSUB -J t0ni_19931101_fc0_2_NCTIME
#BSUB -oo /gpfs/scratch/bsc32/bsc32627/t0ni/LOG_t0ni/t0ni_19931101_fc0_2_NCTIME.cmd.out
#BSUB -eo /gpfs/scratch/bsc32/bsc32627/t0ni/LOG_t0ni/t0ni_19931101_fc0_2_NCTIME.cmd.err
#BSUB -W 01:00
#BSUB -n 1


#
###############################################################################
###################
# Autosubmit header
###################
set -xuve
job_name_ptrn='/gpfs/scratch/bsc32/bsc32627/t0ni/LOG_t0ni/t0ni_19931101_fc0_2_NCTIME'
echo $(date +%s) > ${job_name_ptrn}_STAT

###################
# Autosubmit job
###################

set -v
#
# Architecture
#
CHUNK=2
Chunk_end_date=19931231
Chunk_start_date=19931201
EXPID=t0ni
HPCARCH=marenostrum4
CURRENT_ARCH=nord3
HPCPROJ=bsc32
HPCUSER=bsc32627
JOBNAME=t0ni_19931101_fc0_2_NCTIME
MEMBER=fc0
MODEL=ecearth
PROJDIR=/esarchive/autosubmit/t0ni/proj/auto-ecearth3
PROJ=bsc32
CHUNKSIZE=1
MEMBER=fc0
CMOR_REALIZATION_INDEX=""
START_date=19931101

export HPCPROJ
# load components & libraries
. ${PROJDIR}/platforms/${CURRENT_ARCH}/configure.sh
configure_nctime
. ${PROJDIR}/plugins/cmorization.sh
member_index=$(echo $((10#$(echo ${MEMBER} | cut -c3-) + 1)))
cmor_realization_indexing

#Monthly instantaneous variables. Require special treatment because the CMOR files don't have the name Chunk_start_date-Chunk_end_date
#If nctime fails this might be due to a new instantaneous variable. Original files should be checked and the variable eventually added to this list. More details in https://earth.bsc.es/gitlab/es/auto-ecearth3/-/issues/1450#note_109064
varlist_monthly_instant="SImon/sidivvel"
varlist_ignored="Eyr/fracLut Eyr/cVeg Eyr/cSoil Eyr/cLitter Eyr/cProduct"
frequency_nctime=$(sed -n '/\[NCTIME\]/,/\[/p' /esarchive/autosubmit/${EXPID}/conf/jobs_${EXPID}.conf | grep "^FREQUENCY =" | cut -f2 -d"=" | cut -f2 -d" ")
[[ -z $frequency_nctime ]] && frequency_nctime=1

cd /esarchive/exp/ecearth/${EXPID}/original_files/cmorfiles/

for i in $(seq $CHUNK -1 $(($CHUNK - $frequency_nctime + 1))); do
  ii=$(printf "%03d" ${i})
  if [[ -n $(ls CMOR_${EXPID}_${START_date}_${MEMBER}_${ii}_*.tar) ]]; then
    tar xvf $(ls CMOR_${EXPID}_${START_date}_${MEMBER}_${ii}_*.tar) --strip-components=10
    rm -f CMOR_${EXPID}_${START_date}_${MEMBER}_${ii}*.tar
  fi
done

if [[ -z $(ls -d /esarchive/exp/ecearth/${EXPID}/original_files/cmorfiles/*/*/*/*/r${realization_index}i1p1f1) ]]; then
  echo "No cmor outputs found"
  exit 1
else
  cd /esarchive/exp/ecearth/${EXPID}/original_files/cmorfiles
  for cmor_directory in $(find . -maxdepth 9 -mindepth 9 -type d | grep "r${realization_index}i1p1f1" | grep -vE "fx"); do
    #for monthly instantaneous variables, the date of the cmor files is shifted of one month ahead compared to the real chunk date
    freq_var=$(echo $cmor_directory | cut -f7-8 -d"/")
    if [[ -z $( echo $varlist_ignored | grep ${freq_var} ) ]]; then
      if [[ -n $(echo ${varlist_monthly_instant} | grep ${freq_var}) ]] ; then
        previous_chunk_start_date=$(date --date "$Chunk_start_date  - $((2 * ($frequency_nctime) * $CHUNKSIZE - $CHUNKSIZE - 1)) months" +%Y%m)01
      else
        previous_chunk_start_date=$(date --date "$Chunk_start_date  - $((2 * ($frequency_nctime) * $CHUNKSIZE - $CHUNKSIZE)) months" +%Y%m)01
      fi
      mkdir -p ${nctime_tmpdir}/${MEMBER}/$cmor_directory
      for index_month in $(seq 1 $CHUNKSIZE $((2 * $frequency_nctime * $CHUNKSIZE))); do
        date=$(date -u --date "$previous_chunk_start_date + $((index_month - 1)) months " +%Y%m) #every yearmonth since the beginning of previous chunk start date to 2 * $CHUNKSIZE -1
        year=$(date -u --date "$previous_chunk_start_date + $((index_month - 1)) months" +%Y)    #every yearmonth since the beginning of previous chunk start date to 2 * $CHUNKSIZE -1
        list_cmorfiles=""
        if [[ ${date}01 -ge ${START_date} ]]; then
          if [[ ! -z $(echo $cmor_directory | grep -vE "Oyr|Eyr") ]]; then
            if  [[ -n $(ls ${cmor_directory}/*g?_${date}*nc) ]]; then
              list_cmorfiles="$(ls ${cmor_directory}/*g?_${date}*nc)"
            else
              [[ -n $( ls ${cmor_directory}/*_*_g?_${year}*.nc ) ]] && list_cmorfiles="${list_cmorfiles[@]} $(ls ${cmor_directory}/*_*_g?_${year}*.nc)"
            fi
          else
            if [[ $(echo ${START_date} | cut -c5-6) == "01" ]] && [[ ${CHUNKSIZE} == "12" ]]; then
              list_cmorfiles="${list_cmorfiles[@]}  $(ls ${cmor_directory}/*_*yr_*g?_${year}*.nc)"
            fi
          fi
          if [[ ! -z ${list_cmorfiles[@]} ]]; then
            for cmorfile in ${list_cmorfiles[@]}; do
              [[ -n $cmorfile ]] && ln -sf /esarchive/exp/ecearth/${EXPID}/original_files/cmorfiles/$cmorfile $nctime_tmpdir/$MEMBER/$cmor_directory/.
            done
          fi
        fi
      done
    fi
  done
  ls -lrt ${nctime_tmpdir}/${MEMBER}/*/*/*/*/*/*/*/*/*
  nctxck -i /esarchive/software/nctime --max-processes -1 ${nctime_tmpdir}/$MEMBER
  nctcck -i /esarchive/software/nctime --max-processes -1 ${nctime_tmpdir}/$MEMBER
  rm -rf ${nctime_tmpdir}
fi

###################
# Autosubmit tailer
###################
set -xuve
echo $(date +%s) >> ${job_name_ptrn}_STAT
touch ${job_name_ptrn}_COMPLETED
exit 0

