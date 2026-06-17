from autosubmit_api.components.eta.calculator import ExperimentEtaCalculator
from autosubmit_api.components.eta.strategies import FallbackStrategy
from autosubmit_api.repositories.jobs import create_jobs_repository


class ExperimentEtaService:

    def __init__(self, expid: str):
        self.expid = expid

    def get_eta(self, chunk_unit: str, chunk_size: int) -> dict:
        """Get the estimated time of arrival (remaining time) for an experiment.

        :param chunk_unit: The unit of the chunk e.g. "year", "month"...
        :type chunk_unit: str
        :param chunk_size: The size of the chunk e.g. 1, 2, 3...
        :type chunk_size: int
        :return: A dictionary containing the estimated time of arrival (remaining time) for the experiment
        :rtype: dict
        """

        empty_response = {
            "eta_days": None,
            "chunks_total": None,
            "chunks_remaining": None,
            "runtime_per_chunk_hours": None,
            "current_chunk": None,
        }
        # Load the experiment jobs
        try:
            jobs_repo = create_jobs_repository(self.expid)
            jobs_data = jobs_repo.get_all()
        except Exception:
            return empty_response

        if not jobs_data:
            return empty_response

        # TODO: For now just use the FallbackStrategy
        strategy = FallbackStrategy()
        result = ExperimentEtaCalculator.calculate_eta(
            jobs_data, chunk_unit, chunk_size, strategy
        )
        return result
