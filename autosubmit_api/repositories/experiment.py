from abc import ABC, abstractmethod
from typing import List, Optional

from pydantic import BaseModel
from sqlalchemy import Engine, Table, create_engine
from sqlalchemy.schema import CreateTable

from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.database import tables
from autosubmit_api.database.common import create_autosubmit_db_engine


class ExperimentModel(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    autosubmit_version: Optional[str] = None


class ExperimentRepository(ABC):
    @abstractmethod
    def get_all(self) -> List[ExperimentModel]:
        """
        Get all the experiments

        :return experiments: The list of experiments
        """
        pass

    @abstractmethod
    def get_by_expid(self, expid: str) -> ExperimentModel:
        """
        Get the experiment by expid

        :param expid: The experiment id
        :return experiment: The experiment
        :raises ValueError: If the experiment is not found
        """
        pass


class ExperimentSQLRepository(ExperimentRepository):
    def __init__(self, engine: Engine, table: Table):
        self.engine = engine
        self.table = table

        with self.engine.connect() as conn:
            conn.execute(CreateTable(self.table, if_not_exists=True))
            conn.commit()

    def get_all(self):
        with self.engine.connect() as conn:
            statement = self.table.select()
            result = conn.execute(statement).all()
        return [
            ExperimentModel(
                id=row.id,
                name=row.name,
                description=row.description,
                autosubmit_version=row.autosubmit_version,
            )
            for row in result
        ]

    def get_by_expid(self, expid: str):
        with self.engine.connect() as conn:
            statement = self.table.select().where(self.table.c.name == expid)
            result = conn.execute(statement).first()
        if result is None:
            raise ValueError(f"Experiment with id {expid} not found")
        return ExperimentModel(
            id=result.id,
            name=result.name,
            description=result.description,
            autosubmit_version=result.autosubmit_version,
        )


def create_experiment_repository() -> ExperimentRepository:
    if APIBasicConfig.DATABASE_BACKEND == "postgres":
        # PostgreSQL
        _engine = create_engine(APIBasicConfig.DATABASE_CONN_URL)
    else:
        # SQLite
        _engine = create_autosubmit_db_engine()
    _table = tables.ExperimentTable
    return ExperimentSQLRepository(_engine, _table)
