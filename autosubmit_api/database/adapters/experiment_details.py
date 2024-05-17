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

    def create_table(self):
        """
        Create the details table.
        """
        with self.table_manager.get_connection() as conn:
            self.table_manager.create_table(conn)

    def delete_all(self) -> int:
        """
        Clear the details table.
        """
        with self.table_manager.get_connection() as conn:
            rowcount = self.table_manager.delete_all(conn)
        return rowcount

    def insert_many(self, values: List[Dict[str, Any]]) -> int:
        """
        Insert many rows into the details table.
        """
        with self.table_manager.get_connection() as conn:
            rowcount = self.table_manager.insert_many(conn, values)
        return rowcount

    def get_by_exp_id(self, exp_id: int) -> Dict[str, Any]:
        """
        Get experiment details by the numerical exp_id.
        """
        with self.table_manager.get_connection() as conn:
            row = conn.execute(
                self.table_manager.table.select().where(
                    tables.DetailsTable.exp_id == exp_id
                )
            ).one()
        return row._mapping
