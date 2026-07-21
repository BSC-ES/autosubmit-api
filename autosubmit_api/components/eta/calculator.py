from typing import Optional

from autosubmit_api.components.eta.strategies import (
    group_jobs_by_chunk,
    is_job_completed,
)


EMPTY_RESPONSE = {
    "eta_seconds": None,
    "chunks_total": None,
    "chunks_remaining": None,
    "avg_runtime_per_chunk_seconds": None,
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
    chunks to complete and the average runtime time per chunk in seconds.
    """
    total_chunks, completed_chunks_count = get_chunks_info(jobs_data)

    if total_chunks is None or completed_chunks_count is None:
        return dict(EMPTY_RESPONSE)

    chunks_remaining = total_chunks - completed_chunks_count

    avg_runtime_per_chunk_seconds = strategy.calculate(
        jobs_data, chunk_unit, chunk_size
    )

    # All chunks completed
    if chunks_remaining == 0 and all(
        is_job_completed(job) for job in jobs_data
    ):
        eta_seconds = 0.0
    elif avg_runtime_per_chunk_seconds is None:
        eta_seconds = None
    else:
        eta_seconds = round(
            (avg_runtime_per_chunk_seconds * chunks_remaining), 4
        )

    return {
        "eta_seconds": eta_seconds,
        "chunks_total": total_chunks,
        "chunks_remaining": chunks_remaining,
        "avg_runtime_per_chunk_seconds": avg_runtime_per_chunk_seconds,
    }
