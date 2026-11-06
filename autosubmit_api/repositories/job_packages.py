from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel
from sqlalchemy import Engine, Table, create_engine

from autosubmit_api.common.utils import is_db_version_4_2_0_or_higher
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.database import tables
from autosubmit_api.database.common import (
    create_sqlite_db_engine,
)
from autosubmit_api.persistance.experiment import ExperimentPaths
from autosubmit_api.repositories.experiment import create_experiment_repository


IN_CLAUSE_CHUNK_SIZE = 900
"""Maximum number of job names in an SQL IN clause.
Older SQLite versions have a limit of 999 parameters in a query, and the job
list can ask up to 1000 jobs in one page. Long lookups are split.
"""


class JobPackageModel(BaseModel):
    exp_id: Any
    package_name: Any
    job_name: Any


class JobPackagesRepository(ABC):
    @abstractmethod
    def get_all(self) -> list[JobPackageModel]:
        """Get all job packages."""

    @abstractmethod
    def get_by_job_name(self, job_name: str) -> list[JobPackageModel]:
        """Get the job packages for a given job name."""

    @abstractmethod
    def get_by_job_name_list(self, job_name_list: list[str]) -> list[JobPackageModel]:
        """Get the job packages for a given list of job names.

        Let the job list resolve the wrapper of a whole page with one query,
        instead of one query per job name.
        """


class JobPackagesSQLRepository(JobPackagesRepository):
    def __init__(self, expid: str, engine: Engine, valid_tables: Table | list[Table]):
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

    def get_all(self) -> list[JobPackageModel]:
        with self.engine.connect() as conn:
            statement = self.table.select()
            result = conn.execute(statement).all()   
        return self._to_models(result)

    def get_by_job_name(self, job_name: str) -> list[JobPackageModel]:
        with self.engine.connect() as conn:
            statement = self.table.select().where(self.table.c.job_name == job_name)
            result = conn.execute(statement).all()
        return self._to_models(result)

    def get_by_job_name_list(self, job_names: list[str]) -> list[JobPackageModel]:
        if not job_names:
            return []
        rows = []
        with self.engine.connect() as conn:
            for start in range(0, len(job_names), IN_CLAUSE_CHUNK_SIZE):
                chunk = job_names[start : start + IN_CLAUSE_CHUNK_SIZE]
                statement = self.table.select().where(self.table.c.job_name.in_(chunk))
                rows.extend(conn.execute(self._latest_first(statement)).all())
        return self._to_models(rows)

    def _latest_first(self, statement):
        """Orders the packaging of the latest run first.

        The packaging tables keep the packages of every run of the experiment, so
        the same job can have a row per run. The columns depend on the schema
        revision, so the ordering is built from the ones that are present.
        """
        columns = self.table.c
        order_by = [
            columns[name].desc() for name in ("run_id", "package_id") if name in columns
        ]
        return statement.order_by(*order_by) if order_by else statement

    def _to_models(self, rows) -> list[JobPackageModel]:
        """Maps table rows to job packages.

        The preview tables do not store the experiment id, so it falls back to the
        experiment of the repository.
        """
        return [
            JobPackageModel(
                exp_id=row.exp_id if hasattr(row, "exp_id") else self.expid,
                package_name=row.package_name,
                job_name=row.job_name,
            )
            for row in rows
        ]


def create_job_packages_repository(
    expid: str, preview: bool = False
) -> JobPackagesRepository:
    """Create a job packages repository.

    :param preview: Whether to use the alternative preview job packages table.
    :raises ExperimentNotFoundError: If the experiment does not exist
    """
    # Experiment should exist, whatever the backend is
    experiment = create_experiment_repository().get_by_expid(expid)

    if APIBasicConfig.DATABASE_BACKEND == "postgres":
        # Postgres
        _engine = create_engine(APIBasicConfig.DATABASE_CONN_URL)
        if preview:
            _table = [
                tables.table_change_schema(expid, tables.PreviewWrapperJobsTableV2),
                tables.table_change_schema(expid, tables.PreviewWrapperJobsTable),
                tables.table_change_schema(expid, tables.WrapperJobPackageTable),
            ]
        else:
            _table = [
                tables.table_change_schema(expid, tables.WrapperJobsTableV2),
                tables.table_change_schema(expid, tables.WrapperJobsTable),
                tables.table_change_schema(expid, tables.JobPackageTable),
            ]
    else:
        # SQLite
        if is_db_version_4_2_0_or_higher(experiment.autosubmit_version):
            db_path = ExperimentPaths(expid).job_list_db
        else:
            db_path = ExperimentPaths(expid).job_packages_db

        _engine = create_sqlite_db_engine(db_path, read_only=True)
        if preview:
            _table = [
                tables.PreviewWrapperJobsTableV2,
                tables.PreviewWrapperJobsTable,
                tables.WrapperJobPackageTable,
            ]
        else:
            _table = [
                tables.WrapperJobsTableV2,
                tables.WrapperJobsTable,
                tables.JobPackageTable,
            ]

    return JobPackagesSQLRepository(expid, _engine, _table)
