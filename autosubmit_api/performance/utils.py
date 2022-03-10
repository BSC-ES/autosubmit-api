#!/usr/bin/env pytthon
from autosubmitAPIwu.job.job_common import Status

def calculate_SYPD_perjob(chunk_unit, chunk_size, job_chunk, run_time, status):
    # type: (str, int, int, int, int) -> float
    """
    Generalization of SYPD at job level.
    """
    if status == Status.COMPLETED and job_chunk and job_chunk > 0:
        years_per_sim = datechunk_to_year(chunk_unit, chunk_size)
        if run_time > 0:
            return round((years_per_sim * 86400) / run_time, 2) 
    return None


def calculate_ASYPD_perjob(chunk_unit, chunk_size, job_chunk, queue_run_time, average_post, status):
    # type: (str, int, int, int, float, int) -> float
    """
    Generalization of ASYPD at job level
    """
    if status == Status.COMPLETED and job_chunk and job_chunk > 0:
        years_per_sim = datechunk_to_year(chunk_unit, chunk_size)
        # print("YPS in ASYPD calculation: {}".format(years_per_sim))
        divisor = queue_run_time + average_post
        if divisor > 0.0:
            return round((years_per_sim * 86400) / divisor, 2)        
    return None

def datechunk_to_year(chunk_unit, chunk_size):
    """
    Gets chunk unit and size and returns the value in years

    :return: years  
    :rtype: float
    """
    # type : (int, int) -> float
    chunk_size = chunk_size * 1.0
    options = ["year", "month", "day", "hour"]
    if (chunk_unit == "year"):
        return chunk_size
    elif (chunk_unit == "month"):
        return chunk_size / 12
    elif (chunk_unit == "day"):
        return chunk_size / 365
    elif (chunk_unit == "hour"):
        return chunk_size / 8760
    else:
        return 0.0