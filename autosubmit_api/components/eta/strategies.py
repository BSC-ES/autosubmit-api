from abc import ABC, abstractmethod
from typing import Dict, Optional

from autosubmit_api.common.utils import Status


def _get_status_code(job) -> int:
    """Normalize job status to an integer code."""
    raw = getattr(job, "status_code", job.status)
    if isinstance(raw, str):
        return Status.STRING_TO_CODE.get(raw, Status.UNKNOWN)
    return raw


def is_job_completed(job) -> bool:
    """Check whether a job is completed, handling both string and integer status."""
    return _get_status_code(job) == Status.COMPLETED


def group_jobs_by_chunk(jobs_data: list) -> Dict[Optional[int], list]:
    """Group a list of jobs by their chunk."""
    chunks: Dict[Optional[int], list] = {}
    for job in jobs_data:
        if job.chunk is None:
            continue
        chunks.setdefault(job.chunk, []).append(job)
    return chunks


def compute_chunk_wallclock_seconds(chunk_jobs: list) -> Optional[float]:
    """Wallclock for a completed chunk = max(finish) - min(start) in seconds.

    Returns None if timestamps are missing or inconsistent.
    """
    start = min(
        (j.start for j in chunk_jobs if j.start is not None and j.start > 0),
        default=None,
    )
    finish = max(
        (j.finish for j in chunk_jobs if j.finish is not None and j.finish > 0),
        default=None,
    )
    if start is not None and finish is not None and finish > start:
        return finish - start
    return None


class RuntimePerChunkStrategy(ABC):
    """Interface for calculating the average runtime per chunk unit."""

    @abstractmethod
    def calculate(
        self, jobs_data: list, chunk_unit: str, chunk_size: int
    ) -> Optional[float]: ...


class AvgByDirectTimeStrategy(RuntimePerChunkStrategy):
    """Averages the wallclock time of each completed chunk.

    For each completed chunk computes max(finish) - min(start).
    """

    def calculate(
        self, jobs_data: list, chunk_unit: str, chunk_size: int
    ) -> Optional[float]:
        # Wallclock is measured per chunk, not per unit. 
        # Keep chunk_unit and chunk_size for future strategies.
        _ = chunk_unit, chunk_size

        chunks = group_jobs_by_chunk(jobs_data)

        wallclocks = []
        for chunk_jobs in chunks.values():
            if all(is_job_completed(j) for j in chunk_jobs):
                wallclock = compute_chunk_wallclock_seconds(chunk_jobs)
                if wallclock is not None:
                    wallclocks.append(wallclock)

        if not wallclocks:
            return None

        avg_seconds = sum(wallclocks) / len(wallclocks)
        return round(avg_seconds / 3600.0, 4)