from abc import ABC, abstractmethod
from typing import Any, List
from pydantic import BaseModel
from sqlalchemy import Engine, Table
from sqlalchemy.schema import CreateTable
from autosubmit_api.database import tables
from autosubmit_api.database.common import create_sqlite_db_engine
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
        Gets last run of the experiment. Raises ValueError if no runs found.
        """

    @abstractmethod
    def get_run_by_id(self, run_id: int) -> ExperimentRunModel:
        """
        Gets run by id. Raises ValueError if run not found.
        """


class ExperimentRunSQLRepository(ExperimentRunRepository):
    def __init__(self, expid: str, engine: Engine, table: Table):
        self.engine = engine
        self.table = table
        self.expid = expid

        with self.engine.connect() as conn:
            conn.execute(CreateTable(self.table, if_not_exists=True))
            conn.commit()

    def get_all(self):
        with self.engine.connect() as conn:
            statement = self.table.select()
            result = conn.execute(statement).all()

        return [
            ExperimentRunModel.model_validate(row, from_attributes=True)
            for row in result
        ]

    def get_last_run(self):
        with self.engine.connect() as conn:
            statement = (
                self.table.select().order_by(self.table.c.run_id.desc())
            )
            result = conn.execute(statement).first()
        if result is None:
            raise ValueError(f"No runs found for experiment {self.expid}")
        return ExperimentRunModel.model_validate(result, from_attributes=True)

    def get_run_by_id(self, run_id: int):
        with self.engine.connect() as conn:
            statement = self.table.select().where(self.table.c.run_id == run_id)
            result = conn.execute(statement).first()
        if result is None:
            raise ValueError(
                f"Run with id {run_id} not found for experiment {self.expid}"
            )
        return ExperimentRunModel.model_validate(result, from_attributes=True)


def create_experiment_run_repository(expid: str):
    engine = create_sqlite_db_engine(ExperimentPaths(expid).job_data_db)
    return ExperimentRunSQLRepository(expid, engine, tables.ExperimentRunTable)
