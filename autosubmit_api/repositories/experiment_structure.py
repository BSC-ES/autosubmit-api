from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel
from sqlalchemy import Engine, Table, create_engine, select

from autosubmit_api.common.utils import is_db_version_4_2_0_or_higher
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.database import tables
from autosubmit_api.database.common import (
    create_sqlite_db_engine,
)
from autosubmit_api.persistance.experiment import ExperimentPaths
from autosubmit_api.repositories.experiment import create_experiment_repository


class ExperimentStructureModel(BaseModel):
    e_from: str
    e_to: str


class ExperimentStructureRepository(ABC):
    @abstractmethod
    def get_all(self) -> list[ExperimentStructureModel]:
        """
        Get all dependency job edges of the experiments structure

        :return experiments: The list of job edges
        """

    @abstractmethod
    def get_parents(self, job_name: str) -> list[str]:
        """
        Get the parent jobs of a given job

        :param job_name: The name of the job to get the parents for
        :return parents: The list of parent job names
        """

    @abstractmethod
    def get_children(self, job_name: str) -> list[str]:
        """
        Get the child jobs of a given job

        :param job_name: The name of the job to get the children for
        :return children: The list of child job names
        """


class ExperimentStructureSQLRepository(ExperimentStructureRepository):
    def __init__(
        self, expid: str, engine: Engine, valid_tables: Table | list[Table]
    ):
        self.expid = expid
        self.engine = engine

        if isinstance(valid_tables, list):
            self.table = tables.check_table_schema(self.engine, valid_tables)
            if self.table is None:
                if len(valid_tables) == 0:
                    raise ValueError("No valid tables provided.")
                self.table = valid_tables[0]
        else:
            self.table = valid_tables

    def get_all(self):
        with self.engine.connect() as conn:
            statement = select(self.table.c.e_from, self.table.c.e_to)
            result = conn.execute(statement).all()
        return [
            ExperimentStructureModel(e_from=row.e_from, e_to=row.e_to) for row in result
        ]

    def get_parents(self, job_name: str) -> list[str]:
        with self.engine.connect() as conn:
            statement = self.table.select().where(self.table.c.e_to == job_name)
            result = conn.execute(statement).all()
        return [row.e_from for row in result]

    def get_children(self, job_name: str) -> list[str]:
        with self.engine.connect() as conn:
            statement = self.table.select().where(self.table.c.e_from == job_name)
            result = conn.execute(statement).all()
        return [row.e_to for row in result]


def create_experiment_structure_repository(expid: str) -> ExperimentStructureRepository:
    if APIBasicConfig.DATABASE_BACKEND == "postgres":
        # Postgres
        _engine = create_engine(APIBasicConfig.DATABASE_CONN_URL)
        # Handle multiple schema versions by checking which one exists and using it
        _table = [
            tables.table_change_schema(expid, tables.ExperimentStructureV4_2_0),
            tables.table_change_schema(expid, tables.ExperimentStructureTable),
        ]
    else:
        # SQLite
        exp_paths = ExperimentPaths(expid)
        experiment = create_experiment_repository().get_by_expid(expid)
        if is_db_version_4_2_0_or_higher(experiment.autosubmit_version):
            _engine = create_sqlite_db_engine(exp_paths.job_list_db, read_only=True)
            _table = tables.ExperimentStructureV4_2_0
        else:
            _engine = create_sqlite_db_engine(exp_paths.structure_db, read_only=True)
            _table = tables.ExperimentStructureTable
    return ExperimentStructureSQLRepository(expid, _engine, _table)
