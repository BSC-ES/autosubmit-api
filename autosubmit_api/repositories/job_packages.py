from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, List, Union

from pydantic import BaseModel
from sqlalchemy import Engine, Table, create_engine

from autosubmit_api.config.basicConfig import APIBasicConfig
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
    def __init__(
        self, expid: str, engine: Engine, valid_tables: Union[Table, List[Table]]
    ):
        self.expid = expid
        self.engine = engine

        if isinstance(valid_tables, list):
            self.table = tables.check_table_schema(self.engine, valid_tables)
            if self.table is None:
                if len(valid_tables) == 0:
                    raise ValueError("No valid tables provided.")
                self.table = valid_tables[0]
        else:
            self.table = valid_tables

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
    if APIBasicConfig.DATABASE_BACKEND == "postgres":
        # Postgres
        _engine = create_engine(APIBasicConfig.DATABASE_CONN_URL)
        # Handle multiple schema versions by checking which one exists and using it
        _table = (
            [
                tables.table_change_schema(expid, tables.PreviewWrapperJobsTable),
                tables.table_change_schema(expid, tables.WrapperJobPackageTable),
            ]
            if preview
            else [
                tables.table_change_schema(expid, tables.WrapperJobsTable),
                tables.table_change_schema(expid, tables.JobPackageTable),
            ]
        )
    else:
        # SQLite
        exp_paths = ExperimentPaths(expid)

        if Path(exp_paths.db_dir).exists() and Path(exp_paths.job_list_db).exists():
            _engine = create_sqlite_db_engine(exp_paths.job_list_db, read_only=True)
            _table = (
                tables.PreviewWrapperJobsTable if preview else tables.WrapperJobsTable
            )
        else:
            _engine = create_sqlite_db_engine(exp_paths.job_packages_db, read_only=True)
            _table = (
                tables.WrapperJobPackageTable if preview else tables.JobPackageTable
            )
    return JobPackagesSQLRepository(expid, _engine, _table)
