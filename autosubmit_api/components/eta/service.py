import traceback

from autosubmit_api.builders.experiment_history_builder import (
    ExperimentHistoryBuilder,
    ExperimentHistoryDirector,
)
from autosubmit_api.components.eta.calculator import ExperimentEtaCalculator
from autosubmit_api.components.eta.strategies import (
    AvgByDirectTimeStrategy,
    FallbackStrategy,
)
from autosubmit_api.logger import logger


EMPTY_RESPONSE = {
    "eta_days": None,
    "chunks_total": None,
    "chunks_remaining": None,
    "avg_wallclock_per_chunk_hours": None,
}


class ExperimentEtaService:

    def __init__(self, expid: str):
        self.expid = expid

    def get_eta(self, chunk_unit: str, chunk_size: int, section: str = "SIM") -> dict:
        """Get the estimated time of arrival (remaining time) for an experiment.

        :param chunk_unit: The unit of the chunk e.g. "year", "month"...
        :type chunk_unit: str
        :param chunk_size: The size of the chunk e.g. 1, 2, 3...
        :type chunk_size: int
        :param section: The section of the experiment to calculate the ETA for (default is "SIM")
        :type section: str
        :return: A dictionary containing the estimated time of arrival (remaining time) for the experiment
        :rtype: dict
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
            return EMPTY_RESPONSE

        # Filter by section
        section_jobs = [job for job in all_jobs if job.section == section]
        if not section_jobs:
            return EMPTY_RESPONSE

        # Primary strategy: average wallclock per completed chunk
        strategy = AvgByDirectTimeStrategy()
        result = ExperimentEtaCalculator.calculate_eta(
            section_jobs, chunk_unit, chunk_size, strategy
        )

        # Fallback if no data
        if result["avg_wallclock_per_chunk_hours"] is None:
            strategy = FallbackStrategy()
            result = ExperimentEtaCalculator.calculate_eta(
                section_jobs, chunk_unit, chunk_size, strategy
            )

        return result
