from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import List

from pydantic import BaseModel
from sqlalchemy import Engine, Table, create_engine
from sqlalchemy.schema import CreateTable

from autosubmit_api.common.utils import LOCAL_TZ
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.database import tables
from autosubmit_api.database.common import create_sqlite_db_engine


class RunnerProcessesDataModel(BaseModel):
    id: int
    expid: str
    pid: int
    status: str
    runner: str
    module_loader: str
    modules: str
    created: str
    modified: str


class RunnerProcessesRepository(ABC):
    @abstractmethod
    def get_active_processes_by_expid(
        self, expid: str
    ) -> List[RunnerProcessesDataModel]:
        """
        Gets all the ACTIVE processes of a specific experiment id
        """

    @abstractmethod
    def get_last_process_by_expid(self, expid: str) -> RunnerProcessesDataModel:
        """
        Gets the last process of a specific experiment id
        """

    @abstractmethod
    def insert_process(
        self,
        expid: str,
        pid: int,
        status: str,
        runner: str,
        module_loader: str,
        modules: str,
    ) -> RunnerProcessesDataModel:
        """
        Inserts a new process status
        """

    @abstractmethod
    def update_process_status(self, id: int, status: str) -> RunnerProcessesDataModel:
        """
        Updates the status of a process
        """


class RunnerProcessesSQLRepository(RunnerProcessesRepository):
    """
    SQLAlchemy implementation of the RunnerProcessesRepository
    """

    def __init__(self, engine: Engine, table: Table):
        self.engine = engine
        self.table = table

        # Create the table if it doesn't exist
        with self.engine.connect() as conn:
            conn.execute(CreateTable(self.table, if_not_exists=True))
            conn.commit()

    def get_active_processes_by_expid(
        self, expid: str
    ) -> List[RunnerProcessesDataModel]:
        with self.engine.connect() as conn:
            statement = self.table.select().where(
                self.table.c.expid == expid, self.table.c.status == "ACTIVE"
            )
            result = conn.execute(statement).all()
        return [
            RunnerProcessesDataModel(
                id=row.id,
                expid=row.expid,
                pid=row.pid,
                status=row.status,
                runner=row.runner,
                module_loader=row.module_loader,
                modules=row.modules,
                created=row.created,
                modified=row.modified,
            )
            for row in result
        ]

    def get_last_process_by_expid(self, expid: str) -> RunnerProcessesDataModel:
        with self.engine.connect() as conn:
            statement = (
                self.table.select()
                .where(self.table.c.expid == expid)
                .order_by(self.table.c.created.desc())
                .limit(1)
            )
            result = conn.execute(statement).first()
            if result is None:
                raise ValueError(f"No process found for expid {expid}")
        return RunnerProcessesDataModel(
            id=result.id,
            expid=result.expid,
            pid=result.pid,
            status=result.status,
            runner=result.runner,
            module_loader=result.module_loader,
            modules=result.modules,
            created=result.created,
            modified=result.modified,
        )

    def insert_process(
        self,
        expid: str,
        pid: int,
        status: str,
        runner: str,
        module_loader: str,
        modules: str,
    ) -> RunnerProcessesDataModel:
        with self.engine.connect() as conn:
            _now = datetime.now(tz=LOCAL_TZ).isoformat(timespec="seconds")
            statement = self.table.insert().values(
                expid=expid,
                pid=pid,
                status=status,
                runner=runner,
                module_loader=module_loader,
                modules=modules,
                created=_now,
                modified=_now,
            )
            result = conn.execute(statement)
            conn.commit()
        return RunnerProcessesDataModel(
            id=result.inserted_primary_key[0],
            expid=expid,
            pid=pid,
            status=status,
            runner=runner,
            module_loader=module_loader,
            modules=modules,
            created=_now,
            modified=_now,
        )

    def update_process_status(self, id: int, status: str) -> RunnerProcessesDataModel:
        with self.engine.connect() as conn:
            _now = datetime.now(tz=LOCAL_TZ).isoformat(timespec="seconds")
            statement = (
                self.table.update()
                .where(self.table.c.id == id)
                .values(status=status, modified=_now)
            )
            conn.execute(statement)
            conn.commit()

            # Get the updated row
            statement = self.table.select().where(self.table.c.id == id)
            result = conn.execute(statement).first()
            if result is None:
                raise ValueError(f"Process with id {id} not found")

        return RunnerProcessesDataModel(
            id=result.id,
            expid=result.expid,
            pid=result.pid,
            status=result.status,
            runner=result.runner,
            module_loader=result.module_loader,
            modules=result.modules,
            created=result.created,
            modified=_now,
        )


def create_runner_processes_repository() -> RunnerProcessesRepository:
    """
    Create a new RunnerProcessesRepository instance
    """
    if APIBasicConfig.DATABASE_BACKEND == "postgres":
        _engine = create_engine(APIBasicConfig.DATABASE_CONN_URL)
    else:
        _engine = create_sqlite_db_engine(
            str(Path(APIBasicConfig.LOCAL_ROOT_DIR).joinpath("api_runners.db"))
        )
    _table = tables.RunnerProcessesTable
    return RunnerProcessesSQLRepository(_engine, _table)
