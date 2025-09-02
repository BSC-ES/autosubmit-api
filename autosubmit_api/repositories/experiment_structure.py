from abc import ABC, abstractmethod
from pathlib import Path
from typing import List

from pydantic import BaseModel
from sqlalchemy import Engine, Table, select

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
    exp_paths = ExperimentPaths(expid)

    if Path(exp_paths.db_dir).exists():
        engine = create_sqlite_db_engine(exp_paths.job_list_db, read_only=True)
        table = tables.ExperimentStructureDBTable
    else:
        engine = create_sqlite_db_engine(exp_paths.structure_db, read_only=True)
        table = tables.ExperimentStructureTable
    return ExperimentStructureSQLRepository(expid, engine, table)
