import traceback

from autosubmit_api.builders.experiment_history_builder import (
    ExperimentHistoryBuilder,
    ExperimentHistoryDirector,
)
from autosubmit_api.components.eta.calculator import EMPTY_RESPONSE, calculate_eta
from autosubmit_api.components.eta.strategies import AvgByDirectTimeStrategy
from autosubmit_api.logger import logger


class ExperimentEtaService:
    """Orchestrates data loading and ETA computation for an experiment."""

    def __init__(self, expid: str):
        self.expid = expid

    def get_eta(
        self, chunk_unit: str, chunk_size: int, section: str = "SIM"
    ) -> dict:
        """Return ETA dict for the given job section.

        Uses AvgByDirectTimeStrategy as the first ETA estimator. When
        no completed chunks exist, all fields are None.
        """
        try:
            history = ExperimentHistoryDirector(
                ExperimentHistoryBuilder(self.expid)
            ).build_reader_experiment_history()
            all_jobs = history.manager.get_all_last_job_data_dcs()
        except Exception:
            logger.error(
                f"Failed to load experiment history for {self.expid}: "
                f"{traceback.format_exc()}"
            )
            return dict(EMPTY_RESPONSE)

        section_jobs = [job for job in all_jobs if job.section == section]
        if not section_jobs:
            return dict(EMPTY_RESPONSE)

        return calculate_eta(
            section_jobs,
            chunk_unit,
            chunk_size,
            AvgByDirectTimeStrategy(),
        )
