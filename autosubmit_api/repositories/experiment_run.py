from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, List

from pydantic import BaseModel
from sqlalchemy import Engine, Table, create_engine, inspect

from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.database import tables
from autosubmit_api.database.common import create_sqlite_db_engine
from autosubmit_api.exceptions import ExperimentRunNotFoundError
from autosubmit_api.persistance.experiment import ExperimentPaths


class ExperimentRunModel(BaseModel):
    run_id: Any
    created: Any
    modified: Any
    start: Any
    finish: Any
    chunk_unit: Any
    chunk_size: Any
    completed: Any
    total: Any
    failed: Any
    queuing: Any
    running: Any
    submitted: Any
    suspended: Any
    metadata: Any


class ExperimentRunRepository(ABC):
    @abstractmethod
    def get_all(self) -> List[ExperimentRunModel]:
        """
        Gets all runs of the experiment
        """

    @abstractmethod
    def get_last_run(self) -> ExperimentRunModel:
        """
        Gets last run of the experiment.

        :raises ExperimentRunNotFoundError: If the experiment has no run data
        """

    @abstractmethod
    def get_run_by_id(self, run_id: int) -> ExperimentRunModel:
        """
        Gets run by id.

        :raises ExperimentRunNotFoundError: If the experiment has no run data
        :raises ValueError: If the run id is not found
        """


class ExperimentRunSQLRepository(ExperimentRunRepository):
    def __init__(self, expid: str, engine: Engine, table: Table):
        self.engine = engine
        self.table = table
        self.expid = expid

    def _has_run_data(self) -> bool:
        """
        Whether the experiment has run data at all: the job data file for the
        sqlite backend, or the experiment run table for postgres.
        """
        if APIBasicConfig.DATABASE_BACKEND == "postgres":
            return inspect(self.engine).has_table(self.table.name, self.table.schema)
        return Path(ExperimentPaths(self.expid).job_data_db).exists()

    def get_all(self):
        """
        Gets all runs of the experiment.

        :raises ExperimentRunNotFoundError: If the experiment has no run data
        """
        if not self._has_run_data():
            raise ExperimentRunNotFoundError(self.expid)

        with self.engine.connect() as conn:
            statement = self.table.select()
            result = conn.execute(statement).all()

        return [
            ExperimentRunModel.model_validate(row, from_attributes=True)
            for row in result
        ]

    def get_last_run(self):
        """
        Gets last run of the experiment.

        :raises ExperimentRunNotFoundError: If the experiment has no run data
        """
        if not self._has_run_data():
            raise ExperimentRunNotFoundError(self.expid)

        with self.engine.connect() as conn:
            statement = self.table.select().order_by(self.table.c.run_id.desc())
            result = conn.execute(statement).first()
        if result is None:
            raise ExperimentRunNotFoundError(self.expid)
        return ExperimentRunModel.model_validate(result, from_attributes=True)

    def get_run_by_id(self, run_id: int):
        """
        Gets run by id.

        :raises ExperimentRunNotFoundError: If the experiment has no run data
        :raises ValueError: If the run id is not found
        """
        if not self._has_run_data():
            raise ExperimentRunNotFoundError(self.expid)

        with self.engine.connect() as conn:
            statement = self.table.select().where(self.table.c.run_id == run_id)
            result = conn.execute(statement).first()
        if result is None:
            raise ValueError(
                f"Run with id {run_id} not found for experiment {self.expid}"
            )
        return ExperimentRunModel.model_validate(result, from_attributes=True)


def create_experiment_run_repository(expid: str):
    if APIBasicConfig.DATABASE_BACKEND == "postgres":
        # Postgres
        _engine = create_engine(APIBasicConfig.DATABASE_CONN_URL)
        _table = tables.table_change_schema(expid, tables.ExperimentRunTable)
    else:
        # SQLite
        _engine = create_sqlite_db_engine(
            ExperimentPaths(expid).job_data_db, read_only=True
        )
        _table = tables.ExperimentRunTable
    return ExperimentRunSQLRepository(expid, _engine, _table)
