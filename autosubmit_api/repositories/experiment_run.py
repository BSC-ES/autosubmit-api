from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel
from sqlalchemy import Engine, Table, create_engine, inspect

from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.database import tables
from autosubmit_api.database.common import create_sqlite_db_engine
from autosubmit_api.exceptions import RunNotFoundError
from autosubmit_api.persistance.experiment import ExperimentPaths


class ExperimentRunModel(BaseModel):
    run_id: int
    created: str | None = None
    modified: str | None = None
    start: int | None = None
    finish: int | None = None
    chunk_unit: str | None = None
    chunk_size: int | None = None
    completed: int | None = None
    total: int | None = None
    failed: int | None = None
    queuing: int | None = None
    running: int | None = None
    submitted: int | None = None
    suspended: int | None = None
    metadata: Any = None


class ExperimentRunRepository(ABC):
    @abstractmethod
    def get_all(self) -> list[ExperimentRunModel]:
        """Gets all runs of the experiment, newest first.
        
        :return: List of runs, or empty list if the experiment has no runs.
        """

    @abstractmethod
    def get_last_run(self) -> ExperimentRunModel:
        """Gets last run of the experiment.

        :raises RunNotFoundError: If the experiment has no runs.
        """

    @abstractmethod
    def get_run_by_id(self, run_id: int) -> ExperimentRunModel:
        """Gets run by id.
        
        :raises RunNotFoundError: If the run does not exist.
        """


class ExperimentRunSQLRepository(ExperimentRunRepository):
    def __init__(self, expid: str, engine: Engine, table: Table):
        self.engine = engine
        self.table = table
        self.expid = expid

    def get_all(self) -> list[ExperimentRunModel]:
        with self.engine.connect() as conn:
            # The historical database of an experiment that has not recorded a run
            # yet may not have the table. That is not an error: it has no runs.
            if not inspect(conn).has_table(self.table.name, self.table.schema):
                return []

            # Newest first: consumers list the runs from the most recent one
            statement = self.table.select().order_by(self.table.c.run_id.desc())
            result = conn.execute(statement).all()

        return [
            ExperimentRunModel.model_validate(row, from_attributes=True)
            for row in result
        ]

    def get_last_run(self) -> ExperimentRunModel:
        with self.engine.connect() as conn:
            if not inspect(conn).has_table(self.table.name, self.table.schema):
                raise RunNotFoundError(self.expid)
            statement = self.table.select().order_by(self.table.c.run_id.desc())
            result = conn.execute(statement).first()
        if result is None:
            raise RunNotFoundError(self.expid)
        return ExperimentRunModel.model_validate(result, from_attributes=True)

    def get_run_by_id(self, run_id: int) -> ExperimentRunModel:
        with self.engine.connect() as conn:
            if not inspect(conn).has_table(self.table.name, self.table.schema):
                raise RunNotFoundError(self.expid, run_id)
            statement = self.table.select().where(self.table.c.run_id == run_id)
            result = conn.execute(statement).first()
        if result is None:
            raise RunNotFoundError(self.expid, run_id)
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
