from __future__ import annotations

import datetime
import re
from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel
from sqlalchemy import Engine, Table, create_engine

from autosubmit_api.logger import logger
from autosubmit_api.common import utils as common_utils
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.database import tables
from autosubmit_api.database.common import (
    POSTGRESQL_MAX_PARAMS,
    SQLITE_MAX_PARAMS,
    create_sqlite_db_engine,
)
from autosubmit_api.persistance.experiment import ExperimentPaths
from autosubmit_api.persistance.pkl_reader import PklReader
from autosubmit_api.repositories.experiment import create_experiment_repository

STRING_TO_CODE = common_utils.Status.STRING_TO_CODE


class JobData(BaseModel):
    id: Any
    name: str
    status: int | None = common_utils.Status.UNKNOWN
    priority: int
    section: str
    date: datetime.datetime | None
    member: str | None
    chunk: int | None
    split: int | None
    splits: int | None
    out_path_local: str | None
    err_path_local: str | None
    out_path_remote: str | None
    err_path_remote: str | None


class JobsRepository(ABC):
    @abstractmethod
    def get_all(self) -> list[JobData]:
        """
        Gets all jobs
        """

    @abstractmethod
    def get_last_modified_timestamp(self) -> int:
        """
        Gets the last modified UNIX timestamp of the jobs
        """

    @abstractmethod
    def get_by_name(self, name: str) -> JobData | None:
        """
        Gets a job by its name
        """

    @abstractmethod
    def get_by_names(self, names: list[str]) -> list[JobData]:
        """
        Gets jobs matching any of the given names
        """

    def search(
        self, job_name: str | None = None, status: str | None = None
    ) -> list[JobData]:
        """
        Searches jobs by a query string
        """


class JobsPklRepository(JobsRepository):
    def __init__(self, expid: str) -> None:
        self.expid = expid
        self.pkl_reader = PklReader(expid)

    def get_all(self) -> list[JobData]:
        """
        Gets all jobs from pkl file
        """
        pkl_content = self.pkl_reader.parse_job_list()
        return [
            JobData(
                id=job.id,
                name=job.name,
                status=job.status,
                priority=job.priority,
                section=job.section,
                date=job.date,
                member=job.member,
                chunk=job.chunk,
                split=job.split,
                splits=job.splits,
                out_path_local=job.out_path_local,
                err_path_local=job.err_path_local,
                out_path_remote=job.out_path_remote,
                err_path_remote=job.err_path_remote,
            )
            for job in pkl_content
        ]

    def get_last_modified_timestamp(self) -> int:
        return self.pkl_reader.get_modified_time()

    def get_by_name(self, name: str) -> JobData | None:
        """
        Gets a job by its name from pkl file
        """
        pkl_content = self.pkl_reader.parse_job_list()
        for job in pkl_content:
            if job.name == name:
                return JobData(
                    id=job.id,
                    name=job.name,
                    status=job.status,
                    priority=job.priority,
                    section=job.section,
                    date=job.date,
                    member=job.member,
                    chunk=job.chunk,
                    split=job.split,
                    splits=job.splits,
                    out_path_local=job.out_path_local,
                    err_path_local=job.err_path_local,
                    out_path_remote=job.out_path_remote,
                    err_path_remote=job.err_path_remote,
                )
        return None

    def get_by_names(self, names: list[str]) -> list[JobData]:
        """
        Gets all jobs whose names are in the given list, reading the pkl once.
        """
        name_set = set(names)
        pkl_content = self.pkl_reader.parse_job_list()
        return [
            JobData(
                id=job.id,
                name=job.name,
                status=job.status,
                priority=job.priority,
                section=job.section,
                date=job.date,
                member=job.member,
                chunk=job.chunk,
                split=job.split,
                splits=job.splits,
                out_path_local=job.out_path_local,
                err_path_local=job.err_path_local,
                out_path_remote=job.out_path_remote,
                err_path_remote=job.err_path_remote,
            )
            for job in pkl_content
            if job.name in name_set
        ]

    @staticmethod
    def _wildcard_compare(expression: str | None, value: str) -> bool:
        """
        Compares a value with a wildcard expression.
        The expression can contain '*' as wildcard, and '!' as negation.
        If the expression is empty, it matches everything.
        Examples:
        - 'test*' matches 'test123', 'test_abc', etc. Not matching '123test'.
        - '!test*' does not match 'test123', 'test_abc', etc
        """
        if not expression:
            return True
        if expression.startswith("!"):
            return not JobsPklRepository._wildcard_compare(expression[1:], value)

        # Transform to regex style: escape metacharacters, then convert '*' wildcard to '.*'
        escaped_expression = re.escape(expression)
        pattern = escaped_expression.replace(r"\*", ".*")
        return bool(re.search(pattern, value))

    def search(
        self, job_name: str | None = None, status: str | None = None
    ) -> list[JobData]:
        """
        Searches jobs by a query string
        """
        pkl_content = self.pkl_reader.parse_job_list()

        return [
            JobData(
                id=job.id,
                name=job.name,
                status=job.status,
                priority=job.priority,
                section=job.section,
                date=job.date,
                member=job.member,
                chunk=job.chunk,
                split=job.split,
                splits=job.splits,
                out_path_local=job.out_path_local,
                err_path_local=job.err_path_local,
                out_path_remote=job.out_path_remote,
                err_path_remote=job.err_path_remote,
            )
            for job in pkl_content
            if JobsPklRepository._wildcard_compare(job_name, job.name)
            and (status is None or job.status == status)
        ]


class JobsSQLRepository(JobsRepository):
    def __init__(self, expid: str, engine: Engine, table: Table) -> None:
        self.expid = expid
        self.engine = engine
        self.table = table

        # Check table schema
        if tables.check_table_schema(self.engine, [self.table]) is None:
            raise ValueError(
                f"Table schema for {self.table.name} does not match expected schema."
            )

    def get_all(self) -> list[JobData]:
        """
        Gets all jobs from SQL database
        """
        with self.engine.connect() as conn:
            result = conn.execute(self.table.select())
            return [
                JobData(
                    id=row.id,
                    name=row.name,
                    status=STRING_TO_CODE.get(row.status, common_utils.Status.UNKNOWN),
                    priority=row.priority,
                    section=row.section,
                    date=row.date,
                    member=row.member,
                    chunk=row.chunk,
                    split=row.split,
                    splits=row.splits,
                    out_path_local=row.local_logs_out,
                    err_path_local=row.local_logs_err,
                    out_path_remote=row.remote_logs_out,
                    err_path_remote=row.remote_logs_err,
                )
                for row in result
            ]

    def get_last_modified_timestamp(self) -> int:
        with self.engine.connect() as conn:
            statement = (
                self.table.select().order_by(self.table.c.modified.desc()).limit(1)
            )
            result = conn.execute(statement).first()
            if result is not None:
                # Try to convert the modified timestamp iso string to int
                try:
                    _date = datetime.datetime.fromisoformat(result.modified)
                    return int(_date.timestamp())
                except Exception:
                    logger.warning(
                        f"Failed to convert modified timestamp '{result.modified}' to int for experiment {self.expid}."
                    )
                    return 0
            else:
                logger.warning(
                    f"No jobs found in the database for experiment {self.expid} to get last modified timestamp."
                )
                return 0

    def get_by_name(self, name: str) -> JobData | None:
        with self.engine.connect() as conn:
            statement = self.table.select().where(self.table.c.name == name)
            result = conn.execute(statement).first()
            if result is not None:
                return JobData(
                    id=result.id,
                    name=result.name,
                    status=STRING_TO_CODE.get(
                        result.status, common_utils.Status.UNKNOWN
                    ),
                    priority=result.priority,
                    section=result.section,
                    date=result.date,
                    member=result.member,
                    chunk=result.chunk,
                    split=result.split,
                    splits=result.splits,
                    out_path_local=result.local_logs_out,
                    err_path_local=result.local_logs_err,
                    out_path_remote=result.remote_logs_out,
                    err_path_remote=result.remote_logs_err,
                )
            else:
                return None

    def get_by_names(self, names: list[str]) -> list[JobData]:
        chunk_size = (
            SQLITE_MAX_PARAMS
            if APIBasicConfig.DATABASE_BACKEND == "sqlite"
            else POSTGRESQL_MAX_PARAMS
        )
        rows = []
        with self.engine.connect() as conn:
            for i in range(0, len(names), chunk_size):
                chunk = names[i : i + chunk_size]
                statement = self.table.select().where(self.table.c.name.in_(chunk))
                result = conn.execute(statement).all()

                for row in result:
                    rows.append(
                        JobData(
                            id=row.id,
                            name=row.name,
                            status=STRING_TO_CODE.get(
                                row.status, common_utils.Status.UNKNOWN
                            ),
                            priority=row.priority,
                            section=row.section,
                            date=row.date,
                            member=row.member,
                            chunk=row.chunk,
                            split=row.split,
                            splits=row.splits,
                            out_path_local=row.local_logs_out,
                            err_path_local=row.local_logs_err,
                            out_path_remote=row.remote_logs_out,
                            err_path_remote=row.remote_logs_err,
                        )
                    )
        return rows


def create_jobs_repository(expid: str) -> JobsRepository:
    """
    Factory function to create a JobsRepository instance.
    It decides whether to use the SQL or PKL repository based on the
    existence of the SQLite database.
    """
    # Experiment should exist
    experiment = create_experiment_repository().get_by_expid(expid)
    is_gt_4_2_0 = common_utils.is_db_version_4_2_0_or_higher(
        experiment.autosubmit_version
    )

    if APIBasicConfig.DATABASE_BACKEND == "postgres":
        # Postgres
        if is_gt_4_2_0:
            engine = create_engine(APIBasicConfig.DATABASE_CONN_URL)
            table = tables.table_change_schema(expid, tables.JobsTable)
            return JobsSQLRepository(expid, engine, table)
    else:
        exp_paths = ExperimentPaths(expid)

        if is_gt_4_2_0:
            engine = create_sqlite_db_engine(exp_paths.job_list_db, read_only=True)
            table = tables.JobsTable
            return JobsSQLRepository(expid, engine, table)

    return JobsPklRepository(expid)
