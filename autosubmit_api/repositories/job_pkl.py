from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from pydantic import BaseModel
from sqlalchemy import Engine, Table, create_engine

from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.database import tables


class JobPklModel(BaseModel):
    expid: str
    pkl: Any
    modified: Any


class JobPklRepository(ABC):
    @abstractmethod
    def get_pkl(self) -> bytes:
        """
        Get pkl binary object
        """

    @abstractmethod
    def get_modified_timestamp(self) -> int:
        """
        Get modified date in epoch format
        """


class JobPklSQLRepository(JobPklRepository):
    def __init__(self, expid: str, engine: Engine, table: Table):
        self.expid = expid
        self.engine = engine
        self.table = table

    def get_pkl(self) -> bytes:
        with self.engine.connect() as conn:
            statement = self.table.select().where(self.table.c.expid == self.expid)
            result = conn.execute(statement).first()
            if result is None:
                raise ValueError(f"Experiment {self.expid} not found")
            return result.pkl

    def get_modified_timestamp(self) -> int:
        with self.engine.connect() as conn:
            statement = self.table.select().where(self.table.c.expid == self.expid)
            result = conn.execute(statement).first()
            if result is None:
                raise ValueError(f"Experiment {self.expid} not found")
            return int(datetime.fromisoformat(result.modified).timestamp())


def create_job_pkl_repository(expid: str) -> JobPklRepository:
    if APIBasicConfig.DATABASE_BACKEND == "postgres":
        # PostgreSQL
        _engine = create_engine(APIBasicConfig.DATABASE_CONN_URL)
        _table = tables.JobPklTable
    else:
        raise ValueError("Only PostgreSQL is supported for job pkl repository")
    return JobPklSQLRepository(expid, _engine, _table)
