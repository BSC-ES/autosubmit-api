from autosubmit_api.database.table_manager import create_db_table_manager
from autosubmit_api.database import tables
from autosubmit_api.persistance.experiment import ExperimentPaths
from typing import Any, Dict, List


class ExpGraphDrawDBRepository:
    def __init__(self, expid: str) -> None:
        self.expid = expid
        self.table_manager = create_db_table_manager(
            table=tables.GraphDataTable,
            db_filepath=ExperimentPaths(expid).graph_data_db,
            schema=expid,
        )

    def create_table(self):
        """
        Create the graph data table.
        """
        with self.table_manager.get_connection() as conn:
            self.table_manager.create_table(conn)

    def get_all(self) -> List[Dict[str, Any]]:
        with self.table_manager.get_connection() as conn:
            result = self.table_manager.select_all(conn)
        return [x._asdict() for x in result]

    def delete_all(self) -> int:
        with self.table_manager.get_connection() as conn:
            rowcount = self.table_manager.delete_all(conn)
        return rowcount

    def insert_many(self, values: List[Dict[str, Any]]) -> int:
        with self.table_manager.get_connection() as conn:
            rowcount = self.table_manager.insert_many(conn, values)
        return rowcount
