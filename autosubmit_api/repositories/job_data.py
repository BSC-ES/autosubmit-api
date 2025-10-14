from abc import ABC, abstractmethod
from typing import Any, List

from pydantic import BaseModel
from sqlalchemy import Engine, Table, create_engine, or_

from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.database import tables
from autosubmit_api.database.common import create_sqlite_db_engine
from autosubmit_api.persistance.experiment import ExperimentPaths


class ExperimentJobDataModel(BaseModel):
    id: Any
    counter: Any
    job_name: Any
    created: Any
    modified: Any
    submit: Any
    start: Any
    finish: Any
    status: Any
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


class ExperimentJobDataRepository(ABC):
    @abstractmethod
    def get_last_job_data_by_run_id(self, run_id: int) -> List[ExperimentJobDataModel]:
        """
        Gets last job data of an specific run id
        """

    @abstractmethod
    def get_last_job_data(self) -> List[ExperimentJobDataModel]:
        """
        Gets last job data
        """

    @abstractmethod
    def get_jobs_by_name(self, job_name: str) -> List[ExperimentJobDataModel]:
        """
        Gets historical job data by job_name
        """

    @abstractmethod
    def get_all(self) -> List[ExperimentJobDataModel]:
        """
        Gets all job data
        """

    @abstractmethod
    def get_job_data_COMPLETED_by_rowtype_run_id(
        self, rowtype: int, run_id: int
    ) -> List[ExperimentJobDataModel]:
        """
        Gets job data by rowtype and run id
        """

    @abstractmethod
    def get_job_data_COMPLETD_by_section(
        self, section: str
    ) -> List[ExperimentJobDataModel]:
        """
        Gets job data by section
        """


class ExperimentJobDataSQLRepository(ExperimentJobDataRepository):
    def __init__(self, expid: str, engine: Engine, valid_tables: List[Table]):
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
            tables.table_change_schema(expid, tables.JobDataTableV18),
            tables.table_change_schema(expid, tables.JobDataTable),
        ]
    else:
        _engine = create_sqlite_db_engine(
            ExperimentPaths(expid).job_data_db, read_only=True
        )
        _tables = [
            tables.JobDataTableV18,
            tables.JobDataTable,
        ]
    return ExperimentJobDataSQLRepository(expid, _engine, _tables)
