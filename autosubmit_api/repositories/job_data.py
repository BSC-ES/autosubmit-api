from abc import ABC, abstractmethod
from typing import Any, List
from pydantic import BaseModel
from sqlalchemy import Engine, Table, or_, Index
from sqlalchemy.schema import CreateTable
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
    def __init__(self, expid: str, engine: Engine, table: Table):
        self.engine = engine
        self.table = table
        self.expid = expid

        with self.engine.connect() as conn:
            conn.execute(CreateTable(self.table, if_not_exists=True))
            Index("ID_JOB_NAME", self.table.c.job_name).create(conn, checkfirst=True)
            conn.commit()

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
    engine = create_sqlite_db_engine(ExperimentPaths(expid).job_data_db)
    return ExperimentJobDataSQLRepository(expid, engine, tables.JobDataTable)
