from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, field_validator
from sqlalchemy import Engine, Table, create_engine, or_

from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.database import tables
from autosubmit_api.database.common import create_sqlite_db_engine, iter_param_chunks
from autosubmit_api.models.jobs import UNKNOWN_STATUS, status_name
from autosubmit_api.persistance.experiment import ExperimentPaths


class ExperimentJobDataModel(BaseModel):
    """A row of the job data database.

    The table is owned by Autosubmit, so only the fields the API reads are typed;
    the rest are kept as ``Any`` to avoid rejecting rows written by other
    versions of Autosubmit.
    """

    id: Any
    counter: Any
    job_name: Any
    created: Any
    modified: Any
    # Times are reported as 0 when the row has no value
    submit: int = 0
    start: int = 0
    finish: int = 0
    # Stored as the status name, normalized on read
    status: str = UNKNOWN_STATUS
    rowtype: Any
    ncpus: Any
    wallclock: Any
    qos: Any
    energy: Any
    date: Any
    section: Any
    member: Any
    chunk: Any
    last: Any
    platform: Any
    job_id: Any
    extra_data: Any
    nnodes: Any
    run_id: Any
    MaxRSS: Any
    AveRSS: Any
    out: Any
    err: Any
    rowstatus: Any
    children: Any
    platform_output: Any
    workflow_commit: Any = None
    split: int | None = None
    splits: int | None = None
    fail_count: Any = None

    @field_validator("split", "splits", mode="before")
    @classmethod
    def parse_int_or_none(cls, v):
        if v is None:
            return None
        try:
            return int(v)
        except (TypeError, ValueError):
            return None

    @field_validator("status", mode="before")
    @classmethod
    def parse_status(cls, value):
        return status_name(value)

    @field_validator("submit", "start", "finish", mode="before")
    @classmethod
    def parse_timestamp(cls, value):
        if value is None:
            return 0
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0


class ExperimentJobDataRepository(ABC):
    @abstractmethod
    def get_last_job_data_by_run_id(self, run_id: int) -> list[ExperimentJobDataModel]:
        """
        Gets last job data of an specific run id
        """

    @abstractmethod
    def get_last_job_data(self) -> list[ExperimentJobDataModel]:
        """
        Gets last job data
        """

    @abstractmethod
    def get_jobs_by_name(self, job_name: str) -> list[ExperimentJobDataModel]:
        """
        Gets historical job data by job_name
        """

    @abstractmethod
    def get_last_job_data_by_name(self, job_name: str) -> ExperimentJobDataModel:
        """
        Gets last job data of a specific job name
        """

    @abstractmethod
    def get_last_job_data_by_name_list(
        self, job_names: list[str]
    ) -> list[ExperimentJobDataModel]:
        """
        Gets last job data of a specific list of job names
        """

    @abstractmethod
    def get_all(self) -> list[ExperimentJobDataModel]:
        """
        Gets all job data
        """

    @abstractmethod
    def get_job_data_COMPLETED_by_rowtype_run_id(
        self, rowtype: int, run_id: int
    ) -> list[ExperimentJobDataModel]:
        """
        Gets job data by rowtype and run id
        """

    @abstractmethod
    def get_job_data_COMPLETD_by_section(
        self, section: str
    ) -> list[ExperimentJobDataModel]:
        """
        Gets job data by section
        """


class ExperimentJobDataSQLRepository(ExperimentJobDataRepository):
    def __init__(self, expid: str, engine: Engine, valid_tables: list[Table]):
        self.expid = expid
        self.engine = engine
        self.table = tables.check_table_schema(self.engine, valid_tables)
        if self.table is None:
            if len(valid_tables) == 0:
                raise ValueError("No valid tables provided.")
            self.table = valid_tables[0]

    def get_last_job_data_by_run_id(self, run_id: int):
        with self.engine.connect() as conn:
            statement = (
                self.table.select()
                .where(
                    (self.table.c.run_id == run_id),
                    (self.table.c.rowtype >= 2),
                )
                .order_by(self.table.c.id.desc())
            )
            result = conn.execute(statement).all()

        return [
            ExperimentJobDataModel.model_validate(row, from_attributes=True)
            for row in result
        ]

    def get_last_job_data(self):
        with self.engine.connect() as conn:
            statement = self.table.select().where(
                (self.table.c.last == 1),
                (self.table.c.rowtype >= 2),
            )
            result = conn.execute(statement).all()

        return [
            ExperimentJobDataModel.model_validate(row, from_attributes=True)
            for row in result
        ]

    def get_jobs_by_name(self, job_name: str):
        with self.engine.connect() as conn:
            statement = (
                self.table.select()
                .where(self.table.c.job_name == job_name)
                .order_by(self.table.c.counter.desc())
            )
            result = conn.execute(statement).all()

        return [
            ExperimentJobDataModel.model_validate(row, from_attributes=True)
            for row in result
        ]

    def get_last_job_data_by_name(self, job_name: str):
        with self.engine.connect() as conn:
            statement = (
                self.table.select()
                .where(
                    (self.table.c.job_name == job_name),
                    (self.table.c.rowtype >= 2),
                    (self.table.c.last == 1),
                )
                .order_by(self.table.c.counter.desc())
            )
            result = conn.execute(statement).first()

        if result:
            return ExperimentJobDataModel.model_validate(result, from_attributes=True)
        else:
            raise ValueError(f"No job data found for job name: {job_name}")

    def get_last_job_data_by_name_list(self, job_names: list[str]):
        rows = []
        with self.engine.connect() as conn:
            for chunk in iter_param_chunks(job_names):
                statement = (
                    self.table.select()
                    .where(
                        (self.table.c.job_name.in_(chunk)),
                        (self.table.c.rowtype >= 2),
                        (self.table.c.last == 1),
                    )
                    .order_by(self.table.c.counter.desc())
                )
                rows.extend(conn.execute(statement).all())

        return [
            ExperimentJobDataModel.model_validate(row, from_attributes=True)
            for row in rows
        ]

    def get_all(self):
        with self.engine.connect() as conn:
            statement = (
                self.table.select().where(self.table.c.id > 0).order_by(self.table.c.id)
            )
            result = conn.execute(statement).all()

        return [
            ExperimentJobDataModel.model_validate(row, from_attributes=True)
            for row in result
        ]

    def get_job_data_COMPLETED_by_rowtype_run_id(self, rowtype: int, run_id: int):
        with self.engine.connect() as conn:
            statement = (
                self.table.select()
                .where(
                    (self.table.c.rowtype == rowtype),
                    (self.table.c.run_id == run_id),
                    (self.table.c.status == "COMPLETED"),
                )
                .order_by(self.table.c.id)
            )
            result = conn.execute(statement).all()

        return [
            ExperimentJobDataModel.model_validate(row, from_attributes=True)
            for row in result
        ]

    def get_job_data_COMPLETD_by_section(self, section: str):
        with self.engine.connect() as conn:
            statement = (
                self.table.select()
                .where(
                    (self.table.c.status == "COMPLETED"),
                    or_(
                        (self.table.c.section == section),
                        (self.table.c.member == section),
                    ),
                )
                .order_by(self.table.c.id)
            )
            result = conn.execute(statement).all()

        return [
            ExperimentJobDataModel.model_validate(row, from_attributes=True)
            for row in result
        ]


def create_experiment_job_data_repository(expid: str):
    if APIBasicConfig.DATABASE_BACKEND == "postgres":
        _engine = create_engine(APIBasicConfig.DATABASE_CONN_URL)
        _tables = [
            tables.table_change_schema(expid, tables.JobDataTableV19),
            tables.table_change_schema(expid, tables.JobDataTableV18),
            tables.table_change_schema(expid, tables.JobDataTable),
        ]
    else:
        _engine = create_sqlite_db_engine(
            ExperimentPaths(expid).job_data_db, read_only=True
        )
        _tables = [
            tables.JobDataTableV19,
            tables.JobDataTableV18,
            tables.JobDataTable,
        ]
    return ExperimentJobDataSQLRepository(expid, _engine, _tables)
