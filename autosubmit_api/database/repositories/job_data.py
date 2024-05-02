from typing import Any, Dict, List
from autosubmit_api.database.table_manager import create_db_table_manager
from sqlalchemy import or_, select

from autosubmit_api.database import tables
from autosubmit_api.persistance.experiment import ExperimentPaths


class JobDataDbRepository:
    def __init__(self, expid: str) -> None:
        self.expid = expid
        self.table_manager = create_db_table_manager(
            table=tables.JobDataTable,
            db_filepath=ExperimentPaths(expid).job_data_db,
            schema=expid,
        )
        self.table = self.table_manager.table
        with self.table_manager.get_connection() as conn:
            self.table_manager.create_table(conn)

    def get_last_job_data_by_run_id(self, run_id: int) -> List[Dict[str, Any]]:
        """
        Gets last job data of an specific run id
        """
        with self.table_manager.get_connection() as conn:
            row = conn.execute(
                select(self.table)
                .where(
                    (self.table.c.run_id == run_id),
                    (self.table.c.rowtype == 2),
                )
                .order_by(self.table.c.id.desc())
            ).all()

        return [row._asdict() for row in row]

    def get_last_job_data(self) -> List[Dict[str, Any]]:
        """
        Gets last job data
        """
        with self.table_manager.get_connection() as conn:
            row = conn.execute(
                select(self.table).where(
                    (self.table.c.last == 1),
                    (self.table.c.rowtype >= 2),
                )
            ).all()
        return [row._asdict() for row in row]

    def get_jobs_by_name(self, job_name: str) -> List[Dict[str, Any]]:
        """
        Gets job data by name
        """
        with self.table_manager.get_connection() as conn:
            rows = conn.execute(
                select(self.table)
                .where(self.table.c.job_name == job_name)
                .order_by(self.table.c.counter.desc())
            ).all()

        return [row._asdict() for row in rows]

    def get_all(self) -> List[Dict[str, Any]]:
        """
        Gets all job data
        """
        with self.table_manager.get_connection() as conn:
            statement = (
                select(self.table)
                .where(self.table.c.id > 0)
                .order_by(self.table.c.id)
            )
            rows = conn.execute(statement).all()

        return [row._asdict() for row in rows]

    def get_job_data_COMPLETED_by_rowtype_run_id(self, rowtype: int, run_id: int) -> List[Dict[str, Any]]:
        """
        Gets job data by rowtype and run id
        """
        with self.table_manager.get_connection() as conn:
            rows = conn.execute(
                select(self.table)
                .where(
                    (self.table.c.run_id == run_id),
                    (self.table.c.rowtype == rowtype),
                    (self.table.c.status == "COMPLETED"),
                )
                .order_by(self.table.c.id)
            ).all()

        return [row._asdict() for row in rows]
    
    def get_job_data_COMPLETD_by_section(self, section: str)-> List[Dict[str, Any]]:
        """
        Gets job data by section
        """
        with self.table_manager.get_connection() as conn:
            rows = conn.execute(
                select(self.table)
                .where(
                    (self.table.c.status == "COMPLETED"),
                    or_(
                        (self.table.c.section == section),
                        (self.table.c.member == section)
                    )
                )
                .order_by(self.table.c.id)
            ).all()

        return [row._asdict() for row in rows]