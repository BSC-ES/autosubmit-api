from datetime import datetime
import os
from typing import Dict, List
from autosubmit.database.db_manager import create_db_table_manager
from sqlalchemy import delete, insert, select
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.database import tables


class ExperimentStatusDbAdapter:
    def __init__(self) -> None:
        APIBasicConfig.read()
        self.table_manager = create_db_table_manager(
            table=tables.ExperimentStatusTable,
            db_filepath=os.path.join(APIBasicConfig.DB_DIR, APIBasicConfig.AS_TIMES_DB),
        )

    def create_table(self):
        """
        Create the experiment_status table.
        """
        with self.table_manager.get_connection() as conn:
            self.table_manager.create_table(conn)

    def get_all_dict(self) -> Dict[str, str]:
        """
        Gets table experiment_status as dictionary {expid: status}
        """
        result = dict()
        with self.table_manager.get_connection() as conn:
            cursor = conn.execute(select(self.table_manager.table))
            for row in cursor:
                result[row.name] = row.status
        return result

    def get_only_running_expids(self) -> List[str]:
        """
        Gets list of running experiments
        """
        with self.table_manager.get_connection() as conn:
            rows = conn.execute(
                select(self.table_manager.table).where(
                    self.table_manager.table.c.status == "RUNNING"
                )
            ).all()
        return [row.name for row in rows]

    def get_status(self, expid: str) -> str:
        """
        Gets the current status of one experiment
        """
        with self.table_manager.get_connection() as conn:
            row = conn.execute(
                select(self.table_manager.table).where(
                    self.table_manager.table.c.name == expid
                )
            ).one_or_none()
        return row.status if row else "NOT RUNNING"

    def upsert_status(self, exp_id: int, expid: str, status: str):
        """
        Upsert (Delete/Insert) the status of one experiment
        """
        with self.table_manager.get_connection() as conn:
            del_stmnt = delete(tables.ExperimentStatusTable).where(
                tables.ExperimentStatusTable.name == expid
            )
            ins_stmnt = insert(tables.ExperimentStatusTable).values(
                exp_id=exp_id,
                name=expid,
                status=status,
                seconds_diff=0,
                modified=datetime.now().isoformat(sep="-", timespec="seconds"),
            )
            conn.execute(del_stmnt)
            result = conn.execute(ins_stmnt)
            conn.commit()

        return result.rowcount
