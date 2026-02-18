import datetime

from autosubmit_api.builders import BaseBuilder
from autosubmit_api.database.models import ExperimentModel
from autosubmit_api.logger import logger
from autosubmit_api.repositories.experiment import create_experiment_repository
from autosubmit_api.repositories.experiment_details import (
    create_experiment_details_repository,
)
from autosubmit_api.repositories.jobs import create_jobs_repository


class ExperimentBuilder(BaseBuilder):
    def produce_pkl_modified_time(self):
        """
        Get the modified time of the pkl file.
        """
        try:
            job_list_repo = create_jobs_repository(self._product.name)
            self._product.modified = datetime.datetime.fromtimestamp(
                job_list_repo.get_last_modified_timestamp(), tz=datetime.timezone.utc
            ).isoformat()
        except Exception:
            self._product.modified = None

    def produce_base_from_dict(self, obj: dict):
        """
        Produce the Experiment from a dictionary, validating it first.
        """
        self._product: ExperimentModel = ExperimentModel.model_validate(obj)

    def produce_base(self, expid):
        """
        Produce basic information from the main experiment table
        """
        result = create_experiment_repository().get_by_expid(expid)

        # Set new product
        self._product = ExperimentModel(
            id=result.id,
            name=result.name,
            description=result.description,
            autosubmit_version=result.autosubmit_version,
        )

    def produce_details(self):
        """
        Produce data from the details table
        """
        exp_id = self._product.id

        try:
            result = create_experiment_details_repository().get_by_exp_id(exp_id)

            # Set details props
            self._product.user = result.user
            self._product.created = result.created
            self._product.model = result.model
            self._product.branch = result.branch
            self._product.hpc = result.hpc
        except Exception:
            logger.error(f"Error getting details for exp_id {exp_id}")

    @property
    def product(self) -> ExperimentModel:
        """
        Returns the Experiment final product.
        """
        return super().product
