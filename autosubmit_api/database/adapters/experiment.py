from typing import Any, Dict, Optional
from autosubmit.database.db_manager import create_db_table_manager

from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.database import tables


class ExperimentDbAdapter:
    def __init__(self):
        self.table_manager = create_db_table_manager(
            table=tables.ExperimentTable,
            db_filepath=APIBasicConfig.DB_PATH,
        )

    def get_all(self):
        with self.table_manager.get_connection() as conn:
            rows = self.table_manager.select_all(conn)
        return rows

    def get_by_expid(self, expid) -> Optional[Dict[str, Any]]:
        with self.table_manager.get_connection() as conn:
            row = conn.execute(
                self.table_manager.table.select().where(
                    tables.ExperimentTable.name == expid
                )
            ).one_or_none()
        return row._mapping if row else None
