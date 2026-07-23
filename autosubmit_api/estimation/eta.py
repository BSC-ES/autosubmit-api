from typing import Dict, Optional

from autosubmit_api.common.utils import Status

_EMPTY_RESPONSE = {
    "eta_seconds": None,
    "chunks_total": None,
    "chunks_remaining": None,
    "avg_runtime_per_chunk_seconds": None,
}


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


def _compute_chunk_runtime_seconds(chunk_jobs: list) -> Optional[float]:
    """
    Runtime for a completed chunk = max(finish) - min(start) in seconds.

    Returns None if timestamps are missing, negative, or finish < start.
    """
    start = min(
        (j.start for j in chunk_jobs if j.start is not None and j.start > 0),
        default=None,
    )
    finish = max(
        (j.finish for j in chunk_jobs if j.finish is not None and j.finish > 0),
        default=None,
    )
    if start is not None and finish is not None and finish >= start:
        return finish - start
    return None


def calculate_eta(jobs_data: list) -> dict:
    """
    Compute ETA dict from job data.

    Groups jobs by chunk, computes the average runtime of completed chunks,
    and estimates remaining time as avg_runtime * remaining_chunks.
    """
    chunks: Dict[Optional[int], list] = {}
    for job in jobs_data:
        if job.chunk is not None:
            chunks.setdefault(job.chunk, []).append(job)

    if not chunks:
        return dict(_EMPTY_RESPONSE)

    total_chunks = len(chunks)
    completed_count = 0
    runtimes = []

    for chunk_jobs in chunks.values():
        chunk_completed = all(is_job_completed(j) for j in chunk_jobs)
        if chunk_completed:
            completed_count += 1
            runtime = _compute_chunk_runtime_seconds(chunk_jobs)
            if runtime is not None:
                runtimes.append(runtime)

    avg_runtime = sum(runtimes) / len(runtimes) if runtimes else None
    remaining = total_chunks - completed_count

    if remaining == 0 and all(is_job_completed(j) for j in jobs_data):
        eta_seconds = 0.0
    elif avg_runtime is None:
        eta_seconds = None
    else:
        eta_seconds = avg_runtime * remaining

    return {
        "eta_seconds": eta_seconds,
        "chunks_total": total_chunks,
        "chunks_remaining": remaining,
        "avg_runtime_per_chunk_seconds": avg_runtime,
    }
