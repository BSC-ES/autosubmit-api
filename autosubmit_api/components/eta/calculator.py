from typing import Optional

from autosubmit_api.components.eta.strategies import (
    group_jobs_by_chunk,
    is_job_completed,
)


EMPTY_RESPONSE = {
    "eta_days": None,
    "chunks_total": None,
    "chunks_remaining": None,
    "avg_wallclock_per_chunk_hours": None,
}


def get_chunks_info(
    jobs_data: list,
) -> tuple[Optional[int], Optional[int]]:
    """Returns (total_chunks, completed_chunks_count).

    Total_chunks is the count of unique chunks present in the data.
    Completed_chunks_count is the number of chunks where all
    jobs are completed.
    """
    if not jobs_data:
        return None, None

    chunk_jobs = group_jobs_by_chunk(jobs_data)
    if not chunk_jobs:
        return None, None

    total_chunks = len(chunk_jobs)
    completed_chunks_count = sum(
        1
        for jobs in chunk_jobs.values()
        if all(is_job_completed(j) for j in jobs)
    )
    return total_chunks, completed_chunks_count


def calculate_eta(
    jobs_data: list,
    chunk_unit: str,
    chunk_size: int,
    strategy,
) -> dict:
    """Compute ETA dict from job data and a selected strategy.

    The dict contains the estimated time remaining in days,
    the total number of chunks in the experiment, the remaining
    chunks to complete and the average wallclock time per chunk in hours.
    """
    total_chunks, completed_chunks_count = get_chunks_info(jobs_data)

    if total_chunks is None or completed_chunks_count is None:
        return dict(EMPTY_RESPONSE)

    chunks_remaining = total_chunks - completed_chunks_count

    avg_wallclock_per_chunk_hours = strategy.calculate(
        jobs_data, chunk_unit, chunk_size
    )

    # All chunks completed
    if chunks_remaining == 0 and all(
        is_job_completed(job) for job in jobs_data
    ):
        eta_days = 0.0
    elif avg_wallclock_per_chunk_hours is None:
        eta_days = None
    else:
        eta_days = round(
            (avg_wallclock_per_chunk_hours * chunks_remaining) / 24.0, 2
        )

    return {
        "eta_days": eta_days,
        "chunks_total": total_chunks,
        "chunks_remaining": chunks_remaining,
        "avg_wallclock_per_chunk_hours": avg_wallclock_per_chunk_hours,
    }
