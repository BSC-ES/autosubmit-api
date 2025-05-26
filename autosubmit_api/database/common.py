import os
from typing import Any
from sqlalchemy import (
    Connection,
    Engine,
    NullPool,
    Select,
    create_engine,
    select,
    text,
    func,
)
from autosubmit_api.builders import BaseBuilder
from autosubmit_api.logger import logger
from autosubmit_api.config.basicConfig import APIBasicConfig


class AttachedDatabaseConnBuilder(BaseBuilder):
    """
    SQLite utility to build attached databases.
    """

    def __init__(self) -> None:
        super().__init__(False)
        APIBasicConfig.read()
        self.engine = create_engine("sqlite:///:memory:?uri=true", poolclass=NullPool)
        self._product = self.engine.connect()

    def attach_db(self, path: str, name: str, read_only: bool = False):
        path = os.path.abspath(path)
        if read_only:
            path = f"file:{path}?mode=ro&uri=true"
        self._product.execute(text(f"attach database '{path}' as {name};"))

    def attach_autosubmit_db(self, read_only: bool = False):
        autosubmit_db_path = os.path.abspath(APIBasicConfig.DB_PATH)
        self.attach_db(autosubmit_db_path, "autosubmit", read_only=read_only)

    def attach_as_times_db(self, read_only: bool = False):
        as_times_db_path = os.path.join(
            APIBasicConfig.DB_DIR, APIBasicConfig.AS_TIMES_DB
        )
        self.attach_db(as_times_db_path, "as_times", read_only=read_only)

    @property
    def product(self) -> Connection:
        return super().product


def create_main_db_conn(read_only: bool = False) -> Connection:
    """
    Connection with the autosubmit and as_times DDBB.
    """
    builder = AttachedDatabaseConnBuilder()
    builder.attach_autosubmit_db(read_only=read_only)
    builder.attach_as_times_db(read_only=read_only)

    return builder.product


def create_sqlite_db_engine(db_path: str, read_only: bool = False) -> Engine:
    """
    Create an engine for a SQLite DDBB.
    """
    _db_path = os.path.abspath(db_path)
    if read_only:
        _db_path = f"file:{_db_path}?mode=ro&uri=true"
    return create_engine(f"sqlite:///{_db_path}", poolclass=NullPool)


def create_autosubmit_db_engine() -> Engine:
    """
    Create an engine for the autosubmit DDBB. Usually named autosubmit.db
    """
    APIBasicConfig.read()
    return create_sqlite_db_engine(APIBasicConfig.DB_PATH)


def create_as_times_db_engine() -> Engine:
    """
    Create an engine for the AS_TIMES DDBB. Usually named as_times.db
    """
    APIBasicConfig.read()
    db_path = os.path.join(APIBasicConfig.DB_DIR, APIBasicConfig.AS_TIMES_DB)
    return create_sqlite_db_engine(db_path)


def execute_with_limit_offset(
    statement: Select[Any], conn: Connection, limit: int = None, offset: int = None
):
    """
    Execute query statement adding limit and offset.
    Also, it returns the total items without applying limit and offset.
    """
    count_stmnt = select(func.count()).select_from(statement.subquery())

    # Add limit and offset
    if offset and offset >= 0:
        statement = statement.offset(offset)
    if limit and limit > 0:
        statement = statement.limit(limit)

    # Execute query
    logger.debug(statement.compile(conn))
    query_result = conn.execute(statement).all()
    logger.debug(count_stmnt.compile(conn))
    total = conn.scalar(count_stmnt)

    return query_result, total
