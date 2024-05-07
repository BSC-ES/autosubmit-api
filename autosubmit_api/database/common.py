import os
from typing import Any, Union
from sqlalchemy import (
    Connection,
    Engine,
    MetaData,
    NullPool,
    Select,
    create_engine,
    select,
    text,
    func,
    Table,
)
from sqlalchemy.orm import DeclarativeBase
from autosubmit_api.builders import BaseBuilder
from autosubmit_api.logger import logger
from autosubmit_api.config.basicConfig import APIBasicConfig

APIBasicConfig.read()
try:
    _postgres_engine = create_engine(APIBasicConfig.DATABASE_CONN_URL)
except Exception:
    pass

def get_postgres_engine():
    db = _postgres_engine
    if not isinstance(db, Engine):
        APIBasicConfig.read()
        db = create_engine(APIBasicConfig.DATABASE_CONN_URL)
    return db


def copy_rename_table(source_table: DeclarativeBase, new_name: str):
    dest_table = Table(new_name)

    core_source_table: Table = source_table.__table__
    for col in core_source_table.columns:
        dest_table.append_column(col)

    return dest_table


class AttachedDatabaseConnBuilder(BaseBuilder):
    """
    SQLite utility to build attached databases.
    """

    def __init__(self) -> None:
        super().__init__(False)
        APIBasicConfig.read()
        self.engine = create_engine("sqlite://", poolclass=NullPool)
        self._product = self.engine.connect()

    def attach_db(self, path: str, name: str):
        self._product.execute(text(f"attach database '{path}' as {name};"))

    def attach_autosubmit_db(self):
        autosubmit_db_path = os.path.abspath(APIBasicConfig.DB_PATH)
        self.attach_db(autosubmit_db_path, "autosubmit")

    def attach_as_times_db(self):
        as_times_db_path = os.path.join(
            APIBasicConfig.DB_DIR, APIBasicConfig.AS_TIMES_DB
        )
        self.attach_db(as_times_db_path, "as_times")

    @property
    def product(self) -> Connection:
        return super().product


def create_main_db_conn() -> Connection:
    """
    Connection with the autosubmit and as_times DDBB.
    """
    APIBasicConfig.read()
    if APIBasicConfig.DATABASE_BACKEND == "postgres":
        return get_postgres_engine().connect()
    builder = AttachedDatabaseConnBuilder()
    builder.attach_autosubmit_db()
    builder.attach_as_times_db()

    return builder.product


def create_autosubmit_db_engine() -> Engine:
    """
    Create an engine for the autosubmit DDBB. Usually named autosubmit.db
    """
    APIBasicConfig.read()
    if APIBasicConfig.DATABASE_BACKEND == "postgres":
        return get_postgres_engine()
    return create_engine(f"sqlite:///{ os.path.abspath(APIBasicConfig.DB_PATH)}", poolclass=NullPool)


def create_as_times_db_engine() -> Engine:
    """
    Create an engine for the AS_TIMES DDBB. Usually named as_times.db
    """

    APIBasicConfig.read()
    if APIBasicConfig.DATABASE_BACKEND == "postgres":
        return get_postgres_engine()
    db_path = os.path.join(APIBasicConfig.DB_DIR, APIBasicConfig.AS_TIMES_DB)
    return create_engine(f"sqlite:///{ os.path.abspath(db_path)}", poolclass=NullPool)


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


def table_change_schema(schema: str, source: Union[DeclarativeBase, Table]) -> Table:
    """
    Copy the source table and change the schema of that SQLAlchemy table into a new table instance
    """
    if issubclass(source, DeclarativeBase):
        _source_table: Table = source.__table__
    elif isinstance(source, Table):
        _source_table = source
    else:
        raise RuntimeError("Invalid source type on table schema change")

    metadata = MetaData(schema=schema)
    dest_table = Table(_source_table.name, metadata)

    for col in _source_table.columns:
        dest_table.append_column(col.copy())

    logger.debug(_source_table.columns)
    logger.debug(dest_table.columns)

    return dest_table
