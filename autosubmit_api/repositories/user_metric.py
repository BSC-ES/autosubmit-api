from abc import ABC, abstractmethod
from typing import List

from pydantic import BaseModel
from sqlalchemy import Engine, Table, create_engine, select

from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.database import tables
from autosubmit_api.database.common import (
    create_sqlite_db_engine,
)
from autosubmit_api.persistance.experiment import ExperimentPaths


class UserMetricModel(BaseModel):
    user_metric_id: int
    run_id: int
    job_name: str
    metric_name: str
    metric_value: str
    modified: str


class UserMetricRepository(ABC):
    @abstractmethod
    def get_by_run_id(self, run_id: int) -> List[UserMetricModel]:
        """
        Get the user metrics by run id

        :param run_id: The run id
        :return user_metrics: The list of user metrics
        """

    @abstractmethod
    def get_runs_with_user_metrics(self) -> List[int]:
        """
        Get the list of run ids with user metrics

        :return run_ids: The list of run ids
        """


class UserMetricSQLRepository(UserMetricRepository):
    def __init__(self, engine: Engine, table: Table):
        self.engine = engine
        self.table = table

    def get_by_run_id(self, run_id: int) -> List[UserMetricModel]:
        """
        Get the user metrics by run id

        :param run_id: The run id
        :return user_metrics: The list of user metrics
        """
        with self.engine.connect() as conn:
            query = self.table.select().where(self.table.c.run_id == run_id)
            result = conn.execute(query).fetchall()
            return [
                UserMetricModel(
                    user_metric_id=row.user_metric_id,
                    run_id=row.run_id,
                    job_name=row.job_name,
                    metric_name=row.metric_name,
                    metric_value=row.metric_value,
                    modified=row.modified,
                )
                for row in result
            ]

    def get_runs_with_user_metrics(self) -> List[int]:
        """
        Get the list of run ids with user metrics

        :return run_ids: The list of run ids
        """
        with self.engine.connect() as conn:
            query = select(self.table.c.run_id).distinct()
            result = conn.execute(query).all()
            return sorted([row.run_id for row in result], reverse=True)


def create_user_metric_repository(expid: str) -> UserMetricRepository:
    """
    Create a user metric repository.

    :param expid: The experiment id
    :return: The user metric repository
    """
    if APIBasicConfig.DATABASE_BACKEND == "postgres":
        # Postgres
        _engine = create_engine(APIBasicConfig.DATABASE_CONN_URL)
        _table = tables.table_change_schema(expid, tables.UserMetricTable)
    else:
        _engine = create_sqlite_db_engine(
            ExperimentPaths(expid).user_metric_db, read_only=True
        )
        _table = tables.UserMetricTable
    return UserMetricSQLRepository(_engine, _table)
