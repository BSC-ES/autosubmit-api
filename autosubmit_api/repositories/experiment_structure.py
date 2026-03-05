from abc import ABC, abstractmethod
from typing import List

from pydantic import BaseModel
from sqlalchemy import Engine, Table, create_engine

from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.database import tables
from autosubmit_api.database.common import (
    create_sqlite_db_engine,
)
from autosubmit_api.persistance.experiment import ExperimentPaths


class ExperimentStructureModel(BaseModel):
    e_from: str
    e_to: str


class ExperimentStructureRepository(ABC):
    @abstractmethod
    def get_all(self) -> List[ExperimentStructureModel]:
        """
        Get all dependency job edges of the experiments structure

        :return experiments: The list of job edges
        """

    @abstractmethod
    def get_parents(self, job_name: str) -> List[str]:
        """
        Get the parent jobs of a given job

        :param job_name: The name of the job to get the parents for
        :return parents: The list of parent job names
        """

    @abstractmethod
    def get_children(self, job_name: str) -> List[str]:
        """
        Get the child jobs of a given job

        :param job_name: The name of the job to get the children for
        :return children: The list of child job names
        """


class ExperimentStructureSQLRepository(ExperimentStructureRepository):
    def __init__(self, expid: str, engine: Engine, table: Table):
        self.expid = expid
        self.engine = engine
        self.table = table

    def get_all(self):
        with self.engine.connect() as conn:
            statement = self.table.select()
            result = conn.execute(statement).all()
        return [
            ExperimentStructureModel(e_from=row.e_from, e_to=row.e_to) for row in result
        ]

    def get_parents(self, job_name: str) -> List[str]:
        with self.engine.connect() as conn:
            statement = self.table.select().where(self.table.c.e_to == job_name)
            result = conn.execute(statement).all()
        return [row.e_from for row in result]

    def get_children(self, job_name: str) -> List[str]:
        with self.engine.connect() as conn:
            statement = self.table.select().where(self.table.c.e_from == job_name)
            result = conn.execute(statement).all()
        return [row.e_to for row in result]


def create_experiment_structure_repository(expid: str) -> ExperimentStructureRepository:
    if APIBasicConfig.DATABASE_BACKEND == "postgres":
        # Postgres
        _engine = create_engine(APIBasicConfig.DATABASE_CONN_URL)
        _table = tables.table_change_schema(expid, tables.ExperimentStructureTable)
    else:
        # SQLite
        _engine = create_sqlite_db_engine(
            ExperimentPaths(expid).structure_db, read_only=True
        )
        _table = tables.ExperimentStructureTable
    return ExperimentStructureSQLRepository(expid, _engine, _table)
