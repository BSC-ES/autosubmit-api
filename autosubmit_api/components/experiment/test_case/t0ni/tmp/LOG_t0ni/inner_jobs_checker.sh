
cd /gpfs/scratch/bsc32/bsc32627/t0ni/LOG_t0ni
for job in t0ni_19931101_fc0_2_SIM
do
    if [ -f "${job}_STAT" ]
    then
            echo ${job} $(head ${job}_STAT)
    else
            echo ${job}
    fi
done
