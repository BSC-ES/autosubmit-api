from types import SimpleNamespace

from autosubmit_api.builders.experiment_history_builder import (
    ExperimentHistoryBuilder,
    ExperimentHistoryDirector,
)
from autosubmit_api.estimation.eta import calculate_eta
from autosubmit_api.models.responses import ExperimentEtaResponse
from autosubmit_api.repositories.jobs import JobsRepository


class SectionNotFoundError(LookupError):
    """Raised when no jobs match the requested section for an experiment."""


class SectionNotChunkedError(LookupError):
    """Raised when the section exists but is not configured with RUNNING: chunk."""


class ExperimentEtaService:

    def __init__(self, jobs_repo: JobsRepository, expid: str):
        self.jobs_repo = jobs_repo
        self.expid = expid

    def compute_experiment_eta(self, section: str = "SIM") -> ExperimentEtaResponse:
        """
        Get the estimated time of arrival (remaining time) for the given section.

        Merges last job data with the historical database to get
        the actual jobs that last run and the start and finish timestamps for
        those jobs. Then computes the ETA.

        Raises SectionNotFoundError if no jobs match the section.
        Raises SectionNotChunkedError if the section has no chunked jobs.
        """
        current_jobs = self.jobs_repo.get_all()
        section_jobs = [job for job in current_jobs if job.section == section]
        if not section_jobs:
            raise SectionNotFoundError(
                f"No jobs found for section '{section}' in experiment '{self.expid}'"
            )

        if not any(job.chunk is not None for job in section_jobs):
            raise SectionNotChunkedError(
                f"Section '{section}' in experiment '{self.expid}' has no chunked jobs"
            )

        history = ExperimentHistoryDirector(
            ExperimentHistoryBuilder(self.expid)
        ).build_reader_experiment_history()
        history_jobs = history.manager.get_all_last_job_data_dcs()
        history_by_name = {j.job_name: j for j in history_jobs}

        merged_jobs = []
        for job in section_jobs:
            hist = history_by_name.get(job.name)
            merged_jobs.append(
                SimpleNamespace(
                    chunk=job.chunk,
                    status=job.status,
                    start=hist.start if hist else 0,
                    finish=hist.finish if hist else 0,
                )
            )

        return ExperimentEtaResponse(**calculate_eta(merged_jobs))
