import datetime
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel
from sqlalchemy import Engine, Table, create_engine

from autosubmit_api.common import utils as common_utils
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.database import tables
from autosubmit_api.database.common import create_sqlite_db_engine
from autosubmit_api.persistance.experiment import ExperimentPaths
from autosubmit_api.persistance.pkl_reader import PklReader


class JobData(BaseModel):
    id: int
    name: str
    status: Optional[int] = common_utils.Status.UNKNOWN
    priority: int
    section: str
    date: Optional[datetime.datetime]
    member: Optional[str]
    chunk: Optional[int]
    out_path_local: Optional[str]
    err_path_local: Optional[str]
    out_path_remote: Optional[str]
    err_path_remote: Optional[str]


class JobsRepository(ABC):
    @abstractmethod
    def get_all(self) -> List[JobData]:
        """
        Gets all jobs
        """

    @abstractmethod
    def get_last_modified_timestamp(self) -> int:
        """
        Gets the last modified UNIX timestamp of the jobs
        """


class JobsPklRepository(JobsRepository):
    def __init__(self, expid: str) -> None:
        self.expid = expid
        self.pkl_reader = PklReader(expid)

    def get_all(self) -> List[JobData]:
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
                out_path_local=job.out_path_local,
                err_path_local=job.err_path_local,
                out_path_remote=job.out_path_remote,
                err_path_remote=job.err_path_remote,
            )
            for job in pkl_content
        ]

    def get_last_modified_timestamp(self) -> int:
        return self.pkl_reader.get_modified_time()


class JobsSQLRepository(JobsRepository):
    def __init__(self, expid: str, engine: Engine, table: Table) -> None:
        self.expid = expid
        self.engine = engine
        self.table = table

    def get_all(self) -> List[JobData]:
        """
        Gets all jobs from SQL database
        """
        status_str_to_code = common_utils.Status.STRING_TO_CODE
        with self.engine.connect() as conn:
            result = conn.execute(self.table.select())
            return [
                JobData(
                    id=row.id,
                    name=row.name,
                    status=status_str_to_code.get(
                        row.status, common_utils.Status.UNKNOWN
                    ),
                    priority=row.priority,
                    section=row.section,
                    date=row.date,
                    member=row.member,
                    chunk=row.chunk,
                    out_path_local=row.local_logs_out,
                    err_path_local=row.local_logs_err,
                    out_path_remote=row.remote_logs_out,
                    err_path_remote=row.remote_logs_err,
                )
                for row in result
            ]

    def get_last_modified_timestamp(self) -> int:
        # TODO: Implement this method once is available in Autosubmit
        return 0


def create_jobs_repository(expid: str) -> JobsRepository:
    """
    Factory function to create a JobsRepository instance.
    It decides whether to use the SQL or PKL repository based on the
    existence of the SQLite database.
    """
    if APIBasicConfig.DATABASE_BACKEND == "postgres":
        # Postgres
        engine = create_engine(APIBasicConfig.DATABASE_CONN_URL)
        table = tables.table_change_schema(expid, tables.JobsTable)
        return JobsSQLRepository(expid, engine, table)
    else:
        exp_paths = ExperimentPaths(expid)

        if Path(exp_paths.db_dir).exists() and Path(exp_paths.job_list_db).exists():
            engine = create_sqlite_db_engine(exp_paths.job_list_db, read_only=True)
            table = tables.JobsTable
            return JobsSQLRepository(expid, engine, table)

        return JobsPklRepository(expid)
