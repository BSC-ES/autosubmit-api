from abc import ABC, abstractmethod
from typing import Dict, List, Any
from sqlalchemy import Engine, Table
from autosubmit_api.database import tables
from autosubmit_api.database.common import create_autosubmit_db_engine


class ExperimentDetailsRepository(ABC):
    @abstractmethod
    def insert_many(self, values: List[Dict[str, Any]]) -> int:
        """
        Insert many rows into the details table.
        """

    @abstractmethod
    def delete_all(self) -> int:
        """
        Clear the details table.
        """


class ExperimentDetailsSQLRepository(ExperimentDetailsRepository):
    def __init__(self, engine: Engine, table: Table):
        self.engine = engine
        self.table = table

    def insert_many(self, values: List[Dict[str, Any]]) -> int:
        with self.engine.connect() as conn:
            statement = self.table.insert()
            result = conn.execute(statement, values)
            conn.commit()
        return result.rowcount

    def delete_all(self) -> int:
        with self.engine.connect() as conn:
            statement = self.table.delete()
            result = conn.execute(statement)
            conn.commit()
        return result.rowcount


def create_experiment_details_repository() -> ExperimentDetailsRepository:
    engine = create_autosubmit_db_engine()
    return ExperimentDetailsSQLRepository(engine, tables.details_table)
