from abc import ABC, abstractmethod
from typing import Optional

from autosubmit_api.common.utils import Status


def _get_status_code(job) -> int:
    """Normalize job status to an integer code.

    History JobData stores status as a string ("COMPLETED") but has a
    ``status_code`` property that returns the int. Pkl JobData stores
    status as an int directly.
    """
    raw = getattr(job, "status_code", job.status)
    if isinstance(raw, str):
        return Status.STRING_TO_CODE.get(raw, Status.UNKNOWN)
    return raw


def is_job_completed(job) -> bool:
    """Check whether a job is completed, handling both string and integer status."""
    return _get_status_code(job) == Status.COMPLETED


class RuntimePerChunkStrategy(ABC):
    """Interface for calculating the average runtime per chunk unit."""

    @abstractmethod
    def calculate(
        self, jobs_data: list, chunk_unit: str, chunk_size: int
    ) -> Optional[float]: ...


class AvgByDirectTimeStrategy(RuntimePerChunkStrategy):
    """Groups jobs by chunk, calculates wallclock = max(finish) - min(start)
    for each fully-completed chunk, and then averages across them."""

    def calculate(
        self, jobs_data: list, chunk_unit: str, chunk_size: int
    ) -> Optional[float]:
        # Group by chunk
        chunks = {}
        for job in jobs_data:
            if job.chunk is None:
                continue
            chunks.setdefault(job.chunk, []).append(job)

        # For each fully completed chunk, compute wallclock
        wallclocks = []
        for chunk_id, jobs in chunks.items():
            if all(is_job_completed(j) for j in jobs):
                start = min(j.start for j in jobs if j.start is not None and j.start > 0)
                finish = max(j.finish for j in jobs if j.finish is not None and j.finish > 0)
                if start > 0 and finish > 0:
                    wallclocks.append(finish - start)

        if not wallclocks:
            return None

        avg_seconds = sum(wallclocks) / len(wallclocks)
        avg_hours = avg_seconds / 3600.0

        # Normalize by chunk size
        if chunk_size and chunk_size > 0:
            return avg_hours / chunk_size
        return avg_hours


class FallbackStrategy(RuntimePerChunkStrategy):
    """Fallback strategy that returns None when there is not enough data
    to calculate the average runtime per chunk unit."""

    def calculate(
        self, jobs_data: list, chunk_unit: str, chunk_size: int
    ) -> Optional[float]:
        return None
