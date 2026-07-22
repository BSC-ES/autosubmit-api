#!/usr/bin/env python
from autosubmit_api.common.utils import SECONDS_IN_A_DAY, Status, datechunk_to_year


def _get_status_code(job) -> int:
    """
    Normalize job status to an integer code.
    """
    raw = getattr(job, "status_code", None)
    if raw is None:
        raw = getattr(job, "status", Status.UNKNOWN)
    if isinstance(raw, str):
        return Status.STRING_TO_CODE.get(raw, Status.UNKNOWN)
    return raw


def is_job_completed(job) -> bool:
    """
    Check whether a job is completed, handling both string and integer status.
    """
    return _get_status_code(job) == Status.COMPLETED


def calculate_SYPD_perjob(
    run_time: int,
    chunk_unit: str,
    chunk_size: int,
    job_chunk: int = 1,
    status: int = Status.COMPLETED,
    splits: int = 1,
) -> float:
    """
    Generalization of SYPD at job level.
    """
    if status == Status.COMPLETED and job_chunk and job_chunk > 0:
        years_per_sim = datechunk_to_year(chunk_unit, chunk_size)
        if run_time > 0:
            if not isinstance(splits, int) or splits <= 0:
                splits = 1
            return (years_per_sim * SECONDS_IN_A_DAY / splits) / run_time
    return None


def calculate_ASYPD_perjob(
    queue_run_time: int,
    average_post: float,
    chunk_unit: str,
    chunk_size: int,
    job_chunk: int = 1,
    status: int = Status.COMPLETED,
    splits: int = 1,
) -> float:
    """
    Generalization of ASYPD at job level
    """
    if status == Status.COMPLETED and job_chunk and job_chunk > 0:
        years_per_sim = datechunk_to_year(chunk_unit, chunk_size)
        # print("YPS in ASYPD calculation: {}".format(years_per_sim))
        divisor = queue_run_time + average_post
        if divisor > 0.0:
            if not isinstance(splits, int) or splits <= 0:
                splits = 1
            return (years_per_sim * SECONDS_IN_A_DAY / splits) / divisor
    return None
