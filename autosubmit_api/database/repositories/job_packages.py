from typing import Dict, List
from autosubmit_api.database.table_manager import create_db_table_manager
from sqlalchemy import select

from autosubmit_api.database import tables
from autosubmit_api.persistance.experiment import ExperimentPaths


class JobPackagesDbRepository:
    def __init__(self, expid: str) -> None:
        self.expid = expid
        self.table_manager = create_db_table_manager(
            table=tables.JobPackageTable,
            db_filepath=ExperimentPaths(expid).job_packages_db,
            schema=expid,
        )

    def get_all(self) -> List[Dict[str, str]]:
        """
        Get all job packages.
        """
        with self.table_manager.get_connection() as conn:
            rows = conn.execute(select(self.table_manager.table)).all()
        return [row._asdict() for row in rows]


class WrapperJobPackagesDbRepository:
    def __init__(self, expid: str) -> None:
        self.expid = expid
        self.table_manager = create_db_table_manager(
            table=tables.WrapperJobPackageTable,
            db_filepath=ExperimentPaths(expid).job_packages_db,
            schema=expid,
        )

    def get_all(self) -> List[Dict[str, str]]:
        """
        Get all job packages.
        """
        with self.table_manager.get_connection() as conn:
            rows = conn.execute(select(self.table_manager.table)).all()
        return [row._asdict() for row in rows]
