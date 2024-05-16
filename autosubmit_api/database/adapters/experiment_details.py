from typing import Any, Dict, List
from autosubmit.database.db_manager import create_db_table_manager
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.database import tables


class ExperimentDetailsDbAdapter:
    def __init__(self) -> None:
        APIBasicConfig.read()
        self.table_manager = create_db_table_manager(
            table=tables.DetailsTable,
            db_filepath=APIBasicConfig.DB_PATH,
        )

    def delete_all(self) -> int:
        with self.table_manager.get_connection() as conn:
            rowcount = self.table_manager.delete_all(conn)
        return rowcount

    def insert_many(self, values: List[Dict[str, Any]]) -> int:
        with self.table_manager.get_connection() as conn:
            rowcount = self.table_manager.insert_many(conn, values)
        return rowcount
