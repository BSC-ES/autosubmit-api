from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, List

from pydantic import BaseModel
from sqlalchemy import Engine, Table

from autosubmit_api.database import tables
from autosubmit_api.database.common import (
    create_sqlite_db_engine,
)
from autosubmit_api.persistance.experiment import ExperimentPaths


class JobPackageModel(BaseModel):
    exp_id: Any
    package_name: Any
    job_name: Any


class JobPackagesRepository(ABC):
    @abstractmethod
    def get_all(self) -> List[JobPackageModel]:
        """
        Get all job packages.
        """


class JobPackagesSQLRepository(JobPackagesRepository):
    def __init__(self, expid: str, engine: Engine, table: Table):
        self.expid = expid
        self.engine = engine
        self.table = table

    def get_all(self):
        with self.engine.connect() as conn:
            statement = self.table.select()
            result = conn.execute(statement).all()
        return [
            JobPackageModel(
                exp_id=row.exp_id if hasattr(row, "exp_id") else self.expid,
                package_name=row.package_name,
                job_name=row.job_name,
            )
            for row in result
        ]


def create_job_packages_repository(expid: str, preview=False) -> JobPackagesRepository:
    """
    Create a job packages repository.

    :param preview: Whether to use the alternative preview table.
    """
    exp_paths = ExperimentPaths(expid)

    if Path(exp_paths.db_dir).exists():
        engine = create_sqlite_db_engine(exp_paths.job_list_db, read_only=True)
        table = tables.PreviewWrapperJobsTable if preview else tables.WrapperJobsTable
    else:
        engine = create_sqlite_db_engine(exp_paths.job_packages_db, read_only=True)
        table = (
            tables.wrapper_job_package_table if preview else tables.job_package_table
        )
    return JobPackagesSQLRepository(expid, engine, table)
