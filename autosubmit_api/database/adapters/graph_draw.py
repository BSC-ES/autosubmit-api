from autosubmit.database.db_manager import create_db_table_manager
from autosubmit_api.database import tables
from autosubmit_api.persistance.experiment import ExperimentPaths
from typing import Any, Dict, List


class ExpGraphDrawDBAdapter:
    def __init__(self, expid: str) -> None:
        self.expid = expid
        self.graph_db_manager = create_db_table_manager(
            table=tables.GraphDataTable,
            db_filepath=ExperimentPaths(expid).graph_data_db,
            schema=expid,
        )

    def get_all(self) -> List[Dict[str, Any]]:
        with self.graph_db_manager.get_connection() as conn:
            result = self.graph_db_manager.select_all(conn)
        return [x._mapping for x in result]

    def delete_all(self) -> int:
        with self.graph_db_manager.get_connection() as conn:
            rowcount = self.graph_db_manager.delete_all(conn)
        return rowcount

    def insert_many(self, values: List[Dict[str, Any]]) -> int:
        with self.graph_db_manager.get_connection() as conn:
            rowcount = self.graph_db_manager.insert_many(conn, values)
        return rowcount
