from typing import Optional

from autosubmit_api.components.eta.strategies import is_job_completed


class ExperimentEtaCalculator:

    @staticmethod
    def _get_chunks_info(jobs_data: list) -> tuple[Optional[int], Optional[int]]:
        """Get the total number of chunks and the number of remaining chunks for an experiment.

        :param jobs_data: A list of job data for the experiment
        :type jobs_data: list
        :return: A tuple containing the total number of chunks and the number of remaining chunks for the experiment
        :rtype: tuple[Optional[int], Optional[int]]
        """
        if not jobs_data:
            return None, None

        chunks = {job.chunk for job in jobs_data if job.chunk is not None}
        if not chunks:
            return None, None

        total_chunks = max(chunks)

        # Current chunk: highest chunk with at least one non-completed job
        active_chunks = {
            job.chunk
            for job in jobs_data
            if job.chunk is not None and not is_job_completed(job)
        }
        current_chunk = max(active_chunks) if active_chunks else total_chunks

        return total_chunks, current_chunk

    @staticmethod
    def calculate_eta(
        cls, jobs_data: list, chunk_unit: str, chunk_size: int, strategy
    ) -> dict:
        """Return a dict with the ETA response fields for an experiment.

        :param jobs_data: A list of job data for the experiment
        :type jobs_data: list
        :param chunk_unit: The unit of the chunk e.g. "year", "month"...
        :type chunk_unit: str
        :param chunk_size: The size of the chunk e.g. 1, 2, 3...
        :type chunk_size: int
        :param strategy: The strategy to use for calculating the average runtime per chunk unit
        :type strategy: RuntimePerChunkStrategy
        :return: A dictionary containing the estimated time of arrival (remaining time) for the experiment
        :rtype: dict
        """
        total_chunks, current_chunk = cls._get_chunks_info(jobs_data)
        if total_chunks is None or current_chunk is None:
            return {
                "eta_days": None,
                "chunks_total": None,
                "chunks_remaining": None,
                "avg_wallclock_per_chunk_hours": None,
            }
        # If the exp is completed
        if current_chunk >= total_chunks and all(
            is_job_completed(job) for job in jobs_data
        ):
            return {
                "eta_days": 0.0,
                "chunks_total": total_chunks,
                "chunks_remaining": 0,
                "avg_wallclock_per_chunk_hours": 0.0,
            }

        chunks_remaining = total_chunks - current_chunk

        avg_wallclock_per_chunk_hours = strategy.calculate(
            jobs_data, chunk_unit, chunk_size
        )

        if avg_wallclock_per_chunk_hours is None or chunks_remaining <= 0:
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
