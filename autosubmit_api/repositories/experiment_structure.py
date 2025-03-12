from abc import ABC, abstractmethod
from typing import List
from pydantic import BaseModel
from sqlalchemy.schema import CreateTable
from sqlalchemy import Engine, Table
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

        # Initialize the table
        with self.engine.connect() as conn:
            conn.execute(CreateTable(self.table, if_not_exists=True))
            conn.commit()

    def get_all(self):
        with self.engine.connect() as conn:
            statement = self.table.select()
            result = conn.execute(statement).all()
        return [
            ExperimentStructureModel(e_from=row.e_from, e_to=row.e_to) for row in result
        ]


def create_experiment_structure_repository(expid: str) -> ExperimentStructureRepository:
    engine = create_sqlite_db_engine(ExperimentPaths(expid).structure_db)
    table = tables.ExperimentStructureTable
    return ExperimentStructureSQLRepository(expid, engine, table)
