import datetime
from autosubmit_api.logger import logger
from autosubmit_api.builders import BaseBuilder
from autosubmit_api.builders.configuration_facade_builder import (
    AutosubmitConfigurationFacadeBuilder,
    ConfigurationFacadeDirector,
)
from autosubmit_api.database.repositories import ExperimentDbRepository, ExperimentDetailsDbRepository
from autosubmit_api.database.models import ExperimentModel


class ExperimentBuilder(BaseBuilder):

    def produce_base_from_dict(self, obj: dict):
        """
        Produce the Experiment from a dictionary, validating it first.
        """
        self._product: ExperimentModel = ExperimentModel.model_validate(obj)

    def produce_base(self, expid):
        """
        Produce basic information from the main experiment table
        """
        result = ExperimentDbRepository().get_by_expid(expid)

        # Set new product
        self._product = ExperimentModel(
            id=result["id"],
            name=result["name"],
            description=result["description"],
            autosubmit_version=result["autosubmit_version"],
        )

    def produce_details(self):
        """
        Produce data from the details table
        """
        exp_id = self._product.id
        result = None
        try:
            result = ExperimentDetailsDbRepository().get_by_exp_id(exp_id)
        except Exception:
            logger.error(f"Error getting details for exp_id {exp_id}")

        # Set details props
        if result:
            self._product.user = result.user
            self._product.created = result.created
            self._product.model = result.model
            self._product.branch = result.branch
            self._product.hpc = result.hpc

    def produce_config_data(self):
        """
        Produce data from the files
        """
        expid = self._product.name
        autosubmit_config_facade = ConfigurationFacadeDirector(
            AutosubmitConfigurationFacadeBuilder(expid)
        ).build_autosubmit_configuration_facade()

        # Set config props
        self._product.autosubmit_version = (
            autosubmit_config_facade.get_autosubmit_version()
        )
        self._product.user = autosubmit_config_facade.get_owner_name()
        self._product.hpc = autosubmit_config_facade.get_main_platform()
        self._product.wrapper = autosubmit_config_facade.get_wrapper_type()
        try:
            self._product.modified = datetime.datetime.fromtimestamp(
                autosubmit_config_facade.get_pkl_last_modified_timestamp()
            ).isoformat()
        except Exception:
            self._product.modified = None
            logger.error(f"Error getting modified date for expid {expid}")

    @property
    def product(self) -> ExperimentModel:
        """
        Returns the Experiment final product.
        """
        return super().product
