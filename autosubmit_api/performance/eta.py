from typing import Dict, Optional

from autosubmit_api.builders.experiment_history_builder import (
    ExperimentHistoryBuilder,
    ExperimentHistoryDirector,
)
from autosubmit_api.performance.utils import is_job_completed


class SectionNotFoundError(LookupError):
    """Raised when no jobs match the requested section for an experiment."""


_EMPTY_RESPONSE = {
    "eta_seconds": None,
    "chunks_total": None,
    "chunks_remaining": None,
    "avg_runtime_per_chunk_seconds": None,
}


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


def compute_experiment_eta(expid: str, section: str = "SIM") -> dict:
    """
    Load experiment history and compute ETA for the given section.

    Raises SectionNotFoundError if no jobs match the section.
    """
    history = ExperimentHistoryDirector(
        ExperimentHistoryBuilder(expid)
    ).build_reader_experiment_history()
    all_jobs = history.manager.get_all_last_job_data_dcs()
    
    section_jobs = [job for job in all_jobs if job.section == section]
    if not section_jobs:
        raise SectionNotFoundError(
            f"No jobs found for section '{section}' in experiment '{expid}'"
        )

    return calculate_eta(section_jobs)
