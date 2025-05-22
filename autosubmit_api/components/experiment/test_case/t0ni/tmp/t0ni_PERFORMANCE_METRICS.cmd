#!/bin/bash

###############################################################################
#                   PERFORMANCE_METRICS t0ni EXPERIMENT
###############################################################################
###################
# Autosubmit header
###################
set -xuve
job_name_ptrn='/esarchive/autosubmit/t0ni/tmp/LOG_t0ni/t0ni_PERFORMANCE_METRICS'
echo $(date +%s) > ${job_name_ptrn}_STAT

###################
# Autosubmit job
###################

#!/bin/bash

if [[ "marenostrum4" != "marenostrum4" ]]; then
  echo local " is not supported please remove PERFORMANCE_METRICS job from your workflow"
  exit 1
fi
set -xuve
seconds_in_one_day=86400
ROOTDIR=/esarchive/autosubmit/t0ni
log_dir=${ROOTDIR}/tmp/LOG_t0ni

#
# CPMIP: real computational performance of EC-Earth for CMIP6
# related issue https://dev.ec-earth.org/issues/532
#
# Paper: CPMIP: measurements of real computational performance of Earth system models in CMIP6
# Venkatramani et all https://www.geosci-model-dev.net/10/19/2017/gmd-10-19-2017.pdf
#
function year_factor() {

  CHUNKSIZEUNIT=month
  case "${CHUNKSIZEUNIT}" in
  day) year_factor=365 ;;
  month) year_factor=12 ;;
  year) year_factor=1 ;;
  *) error "Unexpected option ${CHUNKSIZE}" ;;
  esac

  export year_factor
}

function real_jules_per_simulated_year() {

  year_factor

  job_id=$(grep SLURM /esarchive/autosubmit/t0ni/tmp/LOG_t0ni/*SIM*.out | sort -n | head -n 1 | awk '{print $2}')
  one_chunk_energy_consumed=$(ssh bsc32627@mn1.bsc.es "sacct -j ${job_id} --noheader --format=ConsumedEnergy --noconvert | head -n 1 |  tr -d "[:space:]"")

  real_jules_per_simulated_year=$(echo "scale=0;( ${year_factor}*${one_chunk_energy_consumed} )" | bc)
  export real_jules_per_simulated_year
}

function theoretical_jules_per_simulated_year() {

  #  MareNostrum 4 total cores: 153216 , consumption (linpack) : 1632.00kW
  theoretical_jules_per_simulated_year=$(echo "scale=0;(${core_hours_per_simulated_year}*3600.0*1632000.0/153216.0 )" | bc)

  export theoretical_jules_per_simulated_year

}

function years_simulated() {

  year_factor

  CHUNKSIZEUNIT=month
  NUMCHUNKS=2
  CHUNKSIZE=1
  years_simulated=$(echo "scale=2; ${CHUNKSIZE}*${NUMCHUNKS}/${year_factor}" | bc)

  export years_simulated
}

#set -vx
cd /esarchive/autosubmit/t0ni/tmp
#
# Get remote ece.info
#
for file in $(ssh bsc32627@mn1.bsc.es "ls -rt /gpfs/scratch/bsc32/bsc32627/t0ni/*/*/runtime/ece.info"); do
  date=$(echo ${file} | awk -F'/' '{print $(NF-3)}')
  member=$(echo ${file} | awk -F'/' '{print $(NF-2)}')
  filename=t0ni_${date}_${member}_ece.info
  rsync -avz bsc32627@mn1.bsc.es:${file} ${filename}
done
{
  #
  echo
  echo "# CPMIP performance metrics for CMIP6"
  echo
  echo "[METRICS]"
  #
  # SYPD
  #
  # SYPD are simulated years per day for the ESM in a 24 h period on a given platform. This should be collected by
  # timing a segment of a production run (usually at least a
  # month, often 1 or more years), not from short test runs.
  # This is because short runs can give excessive weight to
  # startup and shutdown costs, and distort the results following Amdahl’s law. This is measured separately in
  # throughput and speed mode.
  sim_count=$(grep CPMIP *_ece.info | wc -l)
  sypd_cumul=$(grep SYPD *_ece.info | awk '{s+=$4}END{print s}')
  chpsy_cumul=$(grep CHPSY *_ece.info | awk '{s+=$6}END{print s}')
  sypd=$(echo "scale=2;(${sypd_cumul}/${sim_count})" | bc)
  core_hours_per_simulated_year=$(echo "scale=2;(${chpsy_cumul}/${sim_count})" | bc)
  rem=${core_hours_per_simulated_year}
  echo "# Simulated years per day"
  echo "SYPD = "${sypd}
  echo "# Core hours per simulated year"
  # CHSY are core hours per simulated year. This is measured
  # as the product of the model runtime for 1 SY and the
  # number of cores allocated.4 This is measured separately
  # in throughput and speed mode

  echo "CHSY = "${core_hours_per_simulated_year}

  # JPSY is the energy cost of a simulation, measured in Joules
  # per simulated year. Energy is one of the key drivers of computing architecture design in the current era.
  # While direct instrumentation of energy consumption on a chip is still something in development, we generally
  # have access to the energy cost associated with a platform (including cooling, disks, and so on), measured in
  # kWh (= 3.6×106 Joules) over a month or a year. Given  the energy E in Joules consumed over a budgeting interval
  # T (generally 1 month or 1 year, in units of hours), and the aggregate compute hours A on a system (total
  # cores ×T ) over the same interval T , we can measure the
  # cost associated with 1 year of a simulation as follows:
  # JPSY ≡ CHSY × E/A. (6)
  # Note that this is a very broad measure, and simply proportional to CHSY on a given machine. But it still
  # is a basis of comparison across machines (as E will vary). In future years as on-chip energy metering matures
  # and is standardized, we can imagine adding an “actual Joules per SY (AJPSY)” measure, which takes
  # into account the actual energy used by the model and
  # its workflow across the simulation lifecycle, including
  # computation, data movement, and storage. These measures are similar in spirit to some prior measures of
  # “energy to solution” (Bekas and Curioni, 2010; Cumming
  # et al., 2014; Charles et al., 2015). The FTTSE metric of
  # Bekas and Curioni (2010) is very similar to the AJPSY
  # metric proposed here, and which we believe will replace
  # JPSY in due course, when direct metering becomes routinely available.

  # Theoretical Joules per simulated year use the linpack results

  theoretical_jules_per_simulated_year
  echo "# Theoretical Joules per simulated year "
  echo "TJPSY = " ${theoretical_jules_per_simulated_year}

  # Real Joules per simulated year use the scheduler information
  real_jules_per_simulated_year
  echo "# Real Joules per simulated year "
  echo "RJPSY = " ${real_jules_per_simulated_year}

  #
  # PSYPD Post simulated years per day
  #
  # PSYPD is the actual SYPD obtained from a typical longrunning simulation with the model. This number may
  # be lower than SYPD because of system interruptions,
  # queue wait time, or issues with the model workflow.
  # This is measured for a long production run by measuring the time between first submission and the date of
  # arrival of the last history file on the storage file system.
  # This is measured separately in throughput and speed
  # mode. For a run of N years in length, PSYPD ≡ N / ( tN − t0 )
  # where t0 is the time of submission of the first job in the
  # experiment, and tN is the time stamp of the history file
  # for year N.

  years_simulated

  years_simulated_in_seconds=$(echo "scale=2; ${years_simulated}*${seconds_in_one_day}" | bc)

  start_date=$(cat *_SIM_STAT | sort -n | head -n1)
  end_date=$(cat *_POST_STAT | sort -n | tail -n1)
  PSYPD=$(echo "scale=2;(${years_simulated_in_seconds}/(${end_date}-${start_date}))" | bc)
  echo "# Post simulated years per day"
  echo "PSYPD = "${PSYPD}
  #
  # RSYPD
  #
  start_date=$(cat *_SIM_STAT | sort -n | head -n1)
  end_date=$(cat *_POST_STAT | sort -n | tail -n1)
  rsypd=$(echo "scale=2;(${years_simulated_in_seconds}/(${end_date}-${start_date}))" | bc)
  echo "# Real simulated years per day"
  echo "RSYPD = "${rsypd}
  #
  # Memory bloat
  #
  # Ideal from previous measurement (in Mb)
  # see paper in the header
  # TODO FIXME
  ideal=2258
  rss=$(cat *_SIM*.out | grep "Max Memory :" | tail -n1 | awk '{print $4}')
  membl=$(echo "scale=2;$rss/$ideal" | bc)
  echo "# Memory bloat"
  echo "Memory bloat = "${membl}
  #
  # Data Output Cost
  #
  # Data output cost is the cost of performing I/O, and is the
  # difference in cost between model runs with and without I/O. This is measured as the ratio of CHSY with
  # and without I/O. This is measured differently for systems with synchronous and asynchronous I/O. For synchronous I/O where the computational PEs also perform
  # I/O, it requires a separate “No I/O” run where we measure the fractional difference in cost:
  # D ≡ (CHSY − CHSYno I/O) / CHSY  (Eq. 10)
  # For models using asynchronous I/O such as XIOS, a
  # separate bank of PEs is allotted for I/O. In this case, it
  # may be possible to measure it by simply looking at the
  # allocation fraction of the I/O server, without needing a
  # second “no I/O” run.
  # D ≡ ( PM − PI/O ) / PM   (Eq. 11)
  # However, there may be additional computations performed solely for diagnostic purposes; thus, the method
  # of Eq. 10 is likely more accurate. Note also that if the
  # machine allocates by node, we need to account for the
  # number of nodes, not PEs, allocated for I/O.

  io_cores=$(grep "xio_numproc=" ${ROOTDIR}/tmp/*_SIM*.cmd | head -n1 | awk -F= '{print $2}')
  total_cores=$(grep "#SBATCH -n" ${ROOTDIR}/tmp/*_SIM*.cmd | head -n1 | awk '{print $3}')
  data_outpu_cost=$(echo "scale=2;100-100*(${total_cores}-${io_cores})/${total_cores}" | bc)

  echo "# Data Output cost (%)"
  echo "Data Output cost (%) = "${data_outpu_cost}
  #
  # Data intensity
  #
  # It is the measure of data produced per compute hour, in GB/CH (core hours).
  # This is measured as the quotient of data produced per SY,
  # examining  the output directories and divided by CHSY (core hours per simulated year)

  year_factor

  output_one_chunk_in_bytes=$(grep output $(ls -1 ${log_dir}/*POST* | tail -n 1) | awk '{print $5}')
  output_one_year_in_bytes=$(echo "scale=0;( ${year_factor}*${output_one_chunk_in_bytes} )" | bc)
  output_one_year_in_GB=$(echo "scale=2; ${output_one_year_in_bytes}/1000000" | bc)

  data_intensity=$(echo "scale=3; ${output_one_year_in_GB}/${core_hours_per_simulated_year}" | bc)

  echo "# Data intensity (MB/CH)"
  echo "Data intensity (MB/CH) = "${data_intensity}
  echo
  echo "# Job statistics"
  echo
  #
  # Jobs summary
  #
  echo "[JOB_STATS]"
  printf "Job name \t = \t Queue time (H:M:S) \t Run time (H:M:S) \n"
  for file in $(find . -name '*TOTAL_STATS' -not -name 't0ni_PERFORMANCE_METRICS_TOTAL_STATS*'); do
    if [[ $(tail -1 ${file} | awk '{print NF}') -lt 4 ]]; then
      continue
    fi
    ts_submit=$(tail -1 ${file} | awk '{print "\x27"substr($1,0,8)" "substr($1,9,2)":"substr($1,11,2)":"substr($1,13,2)"\x27 +%s"}' | xargs date -d)
    ts_start=$(tail -1 ${file} | awk '{print "\x27"substr($2,0,8)" "substr($2,9,2)":"substr($2,11,2)":"substr($2,13,2)"\x27 +%s"}' | xargs date -d)
    ts_end=$(tail -1 ${file} | awk '{print "\x27"substr($3,0,8)" "substr($3,9,2)":"substr($3,11,2)":"substr($3,13,2)"\x27 +%s"}' | xargs date -d)
    tq=$(date -d "0 -${ts_submit} sec + ${ts_start} sec" +%T)
    tr=$(date -d "0 -${ts_start} sec + ${ts_end} sec" +%T)
    j=$(basename ${file/_TOTAL_STATS/})
    printf '%36s = \t %10s \t %10s \n' ${j} ${tq} ${tr}
  done
} >t0ni_GENERAL_STATS
#
# Jobs average time
#
{
  echo
  echo "# Jobs average time"
  echo
  echo "[QUEUE_TIME_AVG]"

  time_avg=$(grep "SIM =" t0ni_GENERAL_STATS | awk '{print $3}' | awk -F':' 'BEGIN{total=0;} {total+=(($1*3600)+($2*60)+$3);} END{a=(total/NR); printf "%02d:%02d:%02d\n",(a/3600),((a/60)%60),(a%60)}')
  echo "# SIM jobs queue time average (H:M:S)"
  echo "SIM_QUEUE_TIME_AVG = "${time_avg}

  time_avg=$(grep "POST =" t0ni_GENERAL_STATS | awk '{print $3}' | awk -F':' 'BEGIN{total=0;} {total+=(($1*3600)+($2*60)+$3);} END{a=(total/NR); printf "%02d:%02d:%02d\n",(a/3600),((a/60)%60),(a%60)}')
  echo "# POST jobs queue time average (H:M:S)"
  echo "POST_QUEUE_TIME_AVG = "${time_avg}

  time_avg=$(grep "CLEAN =" t0ni_GENERAL_STATS | awk '{print $3}' | awk -F':' 'BEGIN{total=0;} {total+=(($1*3600)+($2*60)+$3);} END{a=(total/NR); printf "%02d:%02d:%02d\n",(a/3600),((a/60)%60),(a%60)}')
  echo "# CLEAN jobs queue time average (H:M:S)"
  echo "CLEAN_QUEUE_TIME_AVG = "${time_avg}

  transfer_stats=$(grep "TRANSFER =" t0ni_GENERAL_STATS) && returncode=$? || returncode=$?
  if [ ${returncode} -eq 0 ]; then
    if [[ -n "${transfer_stats-}" ]]; then
      time_avg=$(grep "TRANSFER =" t0ni_GENERAL_STATS | awk '{print $3}' | awk -F':' 'BEGIN{total=0;} {total+=(($1*3600)+($2*60)+$3);} END{a=(total/NR); printf "%02d:%02d:%02d\n",(a/3600),((a/60)%60),(a%60)}')
      echo "# TRANSFER jobs queue time average (H:M:S)"
      echo "TRANSFER_QUEUE_TIME_AVG = "${time_avg}
    fi
  fi

  echo
  echo "[RUN_TIME_AVG]"

  time_avg=$(grep "SIM =" t0ni_GENERAL_STATS | awk '{print $4}' | awk -F':' 'BEGIN{total=0;} {total+=(($1*3600)+($2*60)+$3);} END{a=(total/NR); printf "%02d:%02d:%02d\n",(a/3600),((a/60)%60),(a%60)}')
  echo "# SIM jobs run time average (H:M:S)"
  echo "SIM_RUN_TIME_AVG = "${time_avg}

  time_avg=$(grep "POST =" t0ni_GENERAL_STATS | awk '{print $4}' | awk -F':' 'BEGIN{total=0;} {total+=(($1*3600)+($2*60)+$3);} END{a=(total/NR); printf "%02d:%02d:%02d\n",(a/3600),((a/60)%60),(a%60)}')
  echo "# POST jobs run time average (H:M:S)"
  echo "POST_RUN_TIME_AVG = "${time_avg}

  time_avg=$(grep "CLEAN =" t0ni_GENERAL_STATS | awk '{print $4}' | awk -F':' 'BEGIN{total=0;} {total+=(($1*3600)+($2*60)+$3);} END{a=(total/NR); printf "%02d:%02d:%02d\n",(a/3600),((a/60)%60),(a%60)}')
  echo "# CLEAN jobs run time average (H:M:S)"
  echo "CLEAN_RUN_TIME_AVG = "${time_avg}

  if [[ -n "${transfer_stats-}" ]]; then
    time_avg=$(grep "TRANSFER =" t0ni_GENERAL_STATS | awk '{print $4}' | awk -F':' 'BEGIN{total=0;} {total+=(($1*3600)+($2*60)+$3);} END{a=(total/NR); printf "%02d:%02d:%02d\n",(a/3600),((a/60)%60),(a%60)}')
    echo "# TRANSFER jobs run time average (H:M:S)"
    echo "TRANSFER_RUN_TIME_AVG = "${time_avg}
  fi
  #
  # Jobs cumulated time
  #
  total_sec=0
  echo
  echo "# Jobs cumulated time"
  echo
  echo "[QUEUE_TIME_CUM]"

  time_cum=$(grep "${member}_.*_SIM =" t0ni_GENERAL_STATS | awk '{print $3}' | awk -F':' 'BEGIN{total=0;} {total+=(($1*3600)+($2*60)+$3);} END{a=(total); printf "%02d:%02d:%02d\n",(a/3600),((a/60)%60),(a%60)}')
  sec_cum=$(echo $time_cum | awk -F: '{ print ($1 * 3600) + ($2 * 60) + $3 }')
  total_sec=$(echo "$sec_cum+$total_sec" | bc)
  echo "# SIM jobs queue time cumulated (H:M:S)"
  echo "SIM_QUEUE_TIME_CUM = "${time_cum}

  time_cum=$(grep "${member}_.*_POST =" t0ni_GENERAL_STATS | awk '{print $3}' | awk -F':' 'BEGIN{total=0;} {total+=(($1*3600)+($2*60)+$3);} END{a=(total); printf "%02d:%02d:%02d\n",(a/3600),((a/60)%60),(a%60)}')
  echo "# POST jobs queue time cumulated (H:M:S)"
  echo "POST_QUEUE_TIME_CUM = "${time_cum}

  time_cum=$(grep "${member}_.*_CLEAN =" t0ni_GENERAL_STATS | awk '{print $3}' | awk -F':' 'BEGIN{total=0;} {total+=(($1*3600)+($2*60)+$3);} END{a=(total); printf "%02d:%02d:%02d\n",(a/3600),((a/60)%60),(a%60)}')
  echo "# CLEAN jobs queue time cumulated (H:M:S)"
  echo "CLEAN_QUEUE_TIME_CUM = "${time_cum}

  time_cum=$(grep "${member}_.*_TRANSFER =" t0ni_GENERAL_STATS | awk '{print $3}' | awk -F':' 'BEGIN{total=0;} {total+=(($1*3600)+($2*60)+$3);} END{a=(total); printf "%02d:%02d:%02d\n",(a/3600),((a/60)%60),(a%60)}')
  echo "# TRANSFER jobs queue time cumulated (H:M:S)"
  echo "TRANSFER_QUEUE_TIME_CUM = "${time_cum}

  echo
  echo "[RUN_TIME_CUM]"

  time_cum=$(grep "${member}_.*_SIM =" t0ni_GENERAL_STATS | awk '{print $4}' | awk -F':' 'BEGIN{total=0;} {total+=(($1*3600)+($2*60)+$3);} END{a=(total); printf "%02d:%02d:%02d\n",(a/3600),((a/60)%60),(a%60)}')
  sec_cum=$(echo $time_cum | awk -F: '{ print ($1 * 3600) + ($2 * 60) + $3 }')
  total_sec=$(echo "$sec_cum+$total_sec" | bc)
  echo "# SIM jobs run time cumulated (H:M:S)"
  echo "SIM_RUN_TIME_CUM = "${time_cum}

  time_cum=$(grep "${member}_.*_POST =" t0ni_GENERAL_STATS | awk '{print $4}' | awk -F':' 'BEGIN{total=0;} {total+=(($1*3600)+($2*60)+$3);} END{a=(total); printf "%02d:%02d:%02d\n",(a/3600),((a/60)%60),(a%60)}')
  echo "# POST jobs run time average (H:M:S)"
  echo "POST_RUN_TIME_CUM = "${time_cum}

  time_cum=$(grep "${member}_.*_CLEAN =" t0ni_GENERAL_STATS | awk '{print $4}' | awk -F':' 'BEGIN{total=0;} {total+=(($1*3600)+($2*60)+$3);} END{a=(total); printf "%02d:%02d:%02d\n",(a/3600),((a/60)%60),(a%60)}')
  echo "# CLEAN jobs run time average (H:M:S)"
  echo "CLEAN_RUN_TIME_CUM = "${time_cum}

  time_cum=$(grep "${member}_.*_TRANSFER =" t0ni_GENERAL_STATS | awk '{print $4}' | awk -F':' 'BEGIN{total=0;} {total+=(($1*3600)+($2*60)+$3);} END{a=(total); printf "%02d:%02d:%02d\n",(a/3600),((a/60)%60),(a%60)}')
  echo "# TRANSFER jobs run time average (H:M:S)"
  echo "TRANSFER_RUN_TIME_CUM = "${time_cum}

} \
  >>t0ni_GENERAL_STATS

#
# sum 1 POST
#
time_cum=$(grep "${member}_1_POST =" t0ni_GENERAL_STATS | awk '{print $3}' | awk -F':' 'BEGIN{total=0;} {total+=(($1*3600)+($2*60)+$3);} END{a=(total); printf "%02d:%02d:%02d\n",(a/3600),((a/60)%60),(a%60)}')
sec_cum=$(echo $time_cum | awk -F: '{ print ($1 * 3600) + ($2 * 60) + $3 }')
total_sec=$(echo "$sec_cum+$total_sec" | bc)
time_cum=$(grep "${member}_1_POST =" t0ni_GENERAL_STATS | awk '{print $4}' | awk -F':' 'BEGIN{total=0;} {total+=(($1*3600)+($2*60)+$3);} END{a=(total); printf "%02d:%02d:%02d\n",(a/3600),((a/60)%60),(a%60)}')
sec_cum=$(echo $time_cum | awk -F: '{ print ($1 * 3600) + ($2 * 60) + $3 }')
total_sec=$(echo "$sec_cum+$total_sec" | bc)
#
# recompute PSYPD
#
PSYPD=$(echo "scale=2;(${years_simulated_in_seconds}/(${total_sec}))" | bc)
sed -i "s/\(^PSYPD =\).*/PSYPD = $PSYPD/" t0ni_GENERAL_STATS

###################
# Autosubmit tailer
###################
set -xuve
echo $(date +%s) >> ${job_name_ptrn}_STAT
touch ${job_name_ptrn}_COMPLETED
exit 0

