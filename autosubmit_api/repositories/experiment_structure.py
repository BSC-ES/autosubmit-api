from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

from pydantic import BaseModel
from sqlalchemy import Engine, Table, create_engine, select

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


class ExperimentStructureSQLRepository(ExperimentStructureRepository):
    def __init__(self, expid: str, engine: Engine, table: Table):
        self.expid = expid
        self.engine = engine
        self.table = table

    def get_all(self):
        with self.engine.connect() as conn:
            statement = select(self.table.c.e_from, self.table.c.e_to)
            result = conn.execute(statement).all()
        return [
            ExperimentStructureModel(e_from=row.e_from, e_to=row.e_to) for row in result
        ]


def create_experiment_structure_repository(expid: str) -> ExperimentStructureRepository:
    if APIBasicConfig.DATABASE_BACKEND == "postgres":
        # Postgres
        _engine = create_engine(APIBasicConfig.DATABASE_CONN_URL)
        # Critical TODO: Handle newer schema tables.ExperimentStructureDBTable
        _table = tables.table_change_schema(expid, tables.ExperimentStructureTable)
    else:
        # SQLite
        exp_paths = ExperimentPaths(expid)
        if Path(exp_paths.db_dir).exists() and Path(exp_paths.job_list_db).exists():
            _engine = create_sqlite_db_engine(exp_paths.job_list_db, read_only=True)
            _table = tables.ExperimentStructureDBTable
        else:
            _engine = create_sqlite_db_engine(exp_paths.structure_db, read_only=True)
            _table = tables.ExperimentStructureTable
    return ExperimentStructureSQLRepository(expid, _engine, _table)
