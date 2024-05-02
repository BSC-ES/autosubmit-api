from typing import Any, Dict, List, Optional
from autosubmit_api.database.table_manager import create_db_table_manager
from sqlalchemy import select

from autosubmit_api.database import tables
from autosubmit_api.persistance.experiment import ExperimentPaths


class ExperimentRunDbRepository:
    def __init__(self, expid: str) -> None:
        self.expid = expid
        self.table_manager = create_db_table_manager(
            table=tables.ExperimentRunTable,
            db_filepath=ExperimentPaths(expid).job_data_db,
            schema=expid,
        )
        self.table = self.table_manager.table

    def get_all(self) -> List[Dict[str, Any]]:
        """
        Gets all runs of the experiment
        """
        with self.table_manager.get_connection() as conn:
            rows = conn.execute(select(self.table)).all()

        return [row._asdict() for row in rows]

    def get_last_run(self) -> Optional[Dict[str, Any]]:
        """
        Gets last run of the experiment
        """
        with self.table_manager.get_connection() as conn:
            row = conn.execute(
                select(self.table)
                .order_by(self.table.c.run_id.desc())
                .limit(1)
            ).one_or_none()

        return row._asdict() if row else None
    
    def get_run_by_id(self, run_id: int) -> Optional[Dict[str, Any]]:
        """
        Gets run by id
        """
        with self.table_manager.get_connection() as conn:
            row = conn.execute(
                select(self.table)
                .where(self.table.c.run_id == run_id)
            ).one_or_none()

        return row._asdict() if row else None
    
