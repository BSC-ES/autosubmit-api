from abc import ABC, abstractmethod
from typing import List, Any
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
    def __init__(self, engine: Engine, table: Table):
        self.engine = engine
        self.table = table

    def get_all(self):
        with self.engine.connect() as conn:
            statement = self.table.select()
            result = conn.execute(statement).all()
        return [
            JobPackageModel(
                exp_id=row.exp_id,
                package_name=row.package_name,
                job_name=row.job_name,
            )
            for row in result
        ]


def create_job_packages_repository(expid: str, wrapper=False) -> JobPackagesRepository:
    """
    Create a job packages repository.

    :param wrapper: Whether to use the alternative wrapper job packages table.
    """
    engine = create_sqlite_db_engine(ExperimentPaths(expid).job_packages_db)
    table = tables.wrapper_job_package_table if wrapper else tables.job_package_table
    return JobPackagesSQLRepository(engine, table)
