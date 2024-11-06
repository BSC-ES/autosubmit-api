from abc import ABC, abstractmethod
from typing import Any, Dict, List, Union
from pydantic import BaseModel
from sqlalchemy import Engine, Table
from sqlalchemy.schema import CreateTable
from autosubmit_api.database import tables
from autosubmit_api.database.common import create_sqlite_db_engine
from autosubmit_api.persistance.experiment import ExperimentPaths


class ExpGraphLayoutModel(BaseModel):
    id: Union[int, Any]
    job_name: Union[str, Any]
    x: Union[float, Any]
    y: Union[float, Any]


class ExpGraphLayoutRepository(ABC):
    @abstractmethod
    def get_all(self) -> List[ExpGraphLayoutModel]:
        """
        Get all the graph layout data.
        """

    def delete_all(self) -> int:
        """
        Delete all the graph layout data.
        """

    def insert_many(self, values: List[Dict[str, Any]]) -> int:
        """
        Insert many graph layout data.
        """


class ExpGraphLayoutSQLRepository(ExpGraphLayoutRepository):
    def __init__(self, expid: str, engine: Engine, table: Table):
        self.expid = expid
        self.engine = engine
        self.table = table

        with self.engine.connect() as conn:
            conn.execute(CreateTable(self.table, if_not_exists=True))
            conn.commit()

    def get_all(self) -> List[ExpGraphLayoutModel]:
        with self.engine.connect() as conn:
            statement = self.table.select()
            result = conn.execute(statement).all()
        return [ExpGraphLayoutModel.model_validate(row) for row in result]

    def delete_all(self) -> int:
        with self.engine.connect() as conn:
            statement = self.table.delete()
            result = conn.execute(statement)
            conn.commit()
        return result.rowcount

    def insert_many(self, values) -> int:
        with self.engine.connect() as conn:
            statement = self.table.insert()
            result = conn.execute(statement, values)
            conn.commit()
        return result.rowcount


def create_exp_graph_layout_repository(expid: str) -> ExpGraphLayoutRepository:
    engine = create_sqlite_db_engine(ExperimentPaths(expid).graph_data_db)
    return ExpGraphLayoutSQLRepository(expid, engine, tables.GraphDataTable)
