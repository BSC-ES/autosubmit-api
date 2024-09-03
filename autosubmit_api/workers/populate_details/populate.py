import textwrap

from sqlalchemy import text
from autosubmit_api.logger import logger
from autosubmit_api.database import tables

from autosubmit_api.database.common import create_autosubmit_db_engine
from autosubmit_api.builders.configuration_facade_builder import (
    ConfigurationFacadeDirector,
    AutosubmitConfigurationFacadeBuilder,
)
from autosubmit_api.config.basicConfig import APIBasicConfig
from collections import namedtuple
from typing import List


ExperimentDetails = namedtuple(
    "ExperimentDetails", ["owner", "created", "model", "branch", "hpc"]
)
Experiment = namedtuple("Experiment", ["id", "name"])


class DetailsProcessor:
    def __init__(self, basic_config: APIBasicConfig):
        self.basic_config = basic_config
        self.main_db_engine = create_autosubmit_db_engine()

    def process(self):
        new_details = self._get_all_details()
        self.create_details_table_if_not_exists()
        self._clean_table()
        return self._insert_many_into_details_table(new_details)

    def _get_experiments(self) -> List[Experiment]:
        experiments = []
        with self.main_db_engine.connect() as conn:
            query_result = conn.execute(tables.experiment_table.select()).all()

        for exp in query_result:
            experiments.append(
                Experiment(exp._mapping.get("id"), exp._mapping.get("name"))
            )

        return experiments

    def _get_details_data_from_experiment(self, expid: str) -> ExperimentDetails:
        autosubmit_config = ConfigurationFacadeDirector(
            AutosubmitConfigurationFacadeBuilder(expid)
        ).build_autosubmit_configuration_facade(self.basic_config)
        return ExperimentDetails(
            autosubmit_config.get_owner_name(),
            autosubmit_config.get_experiment_created_time_as_datetime(),
            autosubmit_config.get_model(),
            autosubmit_config.get_branch(),
            autosubmit_config.get_main_platform(),
        )

    def _get_all_details(self) -> List[dict]:
        experiments = self._get_experiments()
        result = []
        exp_ids = set()
        for experiment in experiments:
            try:
                detail = self._get_details_data_from_experiment(experiment.name)
                if experiment.id not in exp_ids:
                    result.append(
                        {
                            "exp_id": experiment.id,
                            "user": detail.owner,
                            "created": detail.created,
                            "model": detail.model,
                            "branch": detail.branch,
                            "hpc": detail.hpc,
                        }
                    )
                    exp_ids.add(experiment.id)
            except Exception as exc:
                logger.warning(
                    ("Error on experiment {}: {}".format(experiment.name, str(exc)))
                )
        return result

    def _insert_many_into_details_table(self, values: List[dict]) -> int:
        with self.main_db_engine.connect() as conn:
            result = conn.execute(
                tables.details_table.insert(), values
            )  # Executemany style https://docs.sqlalchemy.org/en/20/tutorial/data_insert.html#insert-usually-generates-the-values-clause-automatically
            conn.commit()
        return result.rowcount

    def create_details_table_if_not_exists(self):
        create_table_query = textwrap.dedent(
            """
            CREATE TABLE
            IF NOT EXISTS details (
            exp_id integer PRIMARY KEY,
            user text NOT NULL,
            created text NOT NULL,
            model text NOT NULL,
            branch text NOT NULL,
            hpc text NOT NULL,
            FOREIGN KEY (exp_id) REFERENCES experiment (id)
            );
        """
        )
        with self.main_db_engine.connect() as conn:
            conn.execute(text(create_table_query))
            conn.commit()

    def _clean_table(self):
        with self.main_db_engine.connect() as conn:
            with conn.execution_options(isolation_level="AUTOCOMMIT"):
                conn.execute(tables.details_table.delete())
                conn.execute(text("VACUUM;"))
