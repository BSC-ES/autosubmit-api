from typing import Dict, Optional
from autosubmit.database.db_manager import create_db_table_manager
from sqlalchemy import select

from autosubmit_api.database import tables
from autosubmit_api.persistance.experiment import ExperimentPaths


class ExperimentRunDbAdapter:
    def __init__(self, expid: str) -> None:
        self.expid = expid
        self.table_manager = create_db_table_manager(
            table=tables.experiment_run_table,
            db_filepath=ExperimentPaths(expid).graph_data_db,
            schema=expid,
        )

    def get_last_run(self) -> Optional[Dict[str,str]]:
        """
        Gets last run of the experiment
        """
        with self.table_manager.get_connection() as conn:
            row = conn.execute(
                select(self.table_manager.table)
                .order_by(tables.ExperimentRunTable.run_id.desc())
                .limit(1)
            ).one_or_none()

        return row._mapping if row else None
