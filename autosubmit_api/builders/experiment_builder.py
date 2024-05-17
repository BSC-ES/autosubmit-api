import datetime
from autosubmit_api.builders import BaseBuilder
from autosubmit_api.builders.configuration_facade_builder import (
    AutosubmitConfigurationFacadeBuilder,
    ConfigurationFacadeDirector,
)
from autosubmit_api.database import tables
from autosubmit_api.database.common import (
    create_autosubmit_db_engine,
)
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
        with create_autosubmit_db_engine().connect() as conn:
            result = conn.execute(
                tables.experiment_table.select().where(
                    tables.experiment_table.c.name == expid
                )
            ).one()

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
        with create_autosubmit_db_engine().connect() as conn:
            result = conn.execute(
                tables.details_table.select().where(
                    tables.details_table.c.exp_id == exp_id
                )
            ).one_or_none()

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

    @property
    def product(self) -> ExperimentModel:
        """
        Returns the Experiment final product.
        """
        return super().product
