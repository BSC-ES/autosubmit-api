import os
from typing import Any, Dict, List, Union

from sqlalchemy import (
    Column,
    Connection,
    Engine,
    NullPool,
    Select,
    Table,
    create_engine,
    func,
    insert,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from autosubmit_api.builders import BaseBuilder
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.logger import logger


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


def create_as_api_db_engine() -> Engine:
    """
    Create an engine for the AS_API DDBB. Usually named as_api.db
    """
    APIBasicConfig.read()
    db_path = os.path.join(APIBasicConfig.DB_DIR, "autosubmit_api.db")
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


def execute_upsert(
    conn: Connection,
    table: Table,
    values: Dict[str, Any],
    index_elements: List[Union[str, Column]],
    set_: Dict[str, Any] = None,
) -> int:
    """
    Execute an atomic upsert (INSERT ... ON CONFLICT DO UPDATE) for SQLite and PostgreSQL.
    This is extendable to other dialects like MySQL (ON DUPLICATE KEY UPDATE),
    mssql (MERGE), or oracle (UPSERT), if needed in the future.

    Notice that statements are executed without an explicit commit, so the caller can manage transactions as needed.

    :param conn: An open SQLAlchemy Connection (caller manages the transaction).
    :param table: The target SQLAlchemy Table.
    :param values: Full row values dict (column name -> value) to insert or update.
    :param index_elements: Conflict target. List of column names or Column objects.
    :param set_: Columns to update on conflict. If None, all columns except index_elements will be updated.
    :return: rowcount of the executed statement.
    """
    str_index_elements = [
        el if isinstance(el, str) else el.name for el in index_elements
    ]

    if set_ is None:
        set_ = {}
        for col in values.keys():
            if col not in str_index_elements:
                set_[col] = values[col]

    dialect = conn.dialect.name
    if dialect == "postgresql":
        _insert = pg_insert
    elif dialect == "sqlite":
        _insert = sqlite_insert
    else:
        # Fallback for unsupported dialects - this will not perform an atomic upsert, so use with caution.
        logger.debug(
            f"Dialect '{dialect}' native upsert not supported or not implemented. Performing non-atomic upsert as fallback."
        )
        existing = conn.execute(
            select(table).where(
                *[table.c[el] == values[el] for el in str_index_elements]
            )
        ).first()
        if existing:
            update_stmt = (
                table.update()
                .where(*[table.c[el] == values[el] for el in str_index_elements])
                .values(**set_)
            )
            result = conn.execute(update_stmt)
            return result.rowcount
        else:
            insert_stmt = insert(table).values(**values)
            result = conn.execute(insert_stmt)
            return result.rowcount

    stmt = (
        _insert(table)
        .values(**values)
        .on_conflict_do_update(index_elements=index_elements, set_=set_)
    )
    return conn.execute(stmt).rowcount


def execute_replace(
    conn: Connection,
    table: Table,
    values: Dict[str, Any],
    index_elements: List[Union[str, Column]],
) -> int:
    """
    Replace a row with a transactional DELETE + INSERT identified by ``index_elements``.
    
    This strategy is schema-agnostic: unlike ``INSERT ... ON CONFLICT`` it does not
    require any PRIMARY KEY/UNIQUE constraint on the key columns, so it is safe for
    the legacy tables found in the hubs, whose schemas cannot be altered and which
    may lack a constraint on ``exp_id``.
    
    Under SQLite's single-writer model, the DELETE takes the write lock before the
    INSERT, so concurrent writers are serialized and only one row per key is kept.
    
    Statements are not committed here: the caller manages the transactions.
    
    :param conn: An open SQLAlchemy Connection (caller manages the transaction).
    :param table: The target SQLAlchemy Table.
    :param values: Full row values dict (column name -> value) to insert.
    :param index_elements: Conflict target. List of column names or Column objects.
    :return: rowcount of the executed insert statement.
    """
    str_index_elements = [
        el if isinstance(el, str) else el.name for el in index_elements
    ]

    # Delete any existing row with the same key
    delete_stmt = table.delete().where(
        *[table.c[el] == values[el] for el in str_index_elements]
    )
    insert_stmt = insert(table).values(**values)

    conn.execute(delete_stmt)
    result = conn.execute(insert_stmt)
    return result.rowcount


def upsert_or_replace(
    conn: Connection,
    table: Table,
    values: Dict[str, Any],
    index_elements: List[Union[str, Column]],
    set_: Dict[str, Any] = None,
) -> int:
    """
    Make the row identified by ``index_elements`` exist with the given ``values``.
    Choose the safest primitive for the actual database backend:

    * PostgreSQL: tables always created though SQLAlchemy, which declares a
    PRIMARY KEY on the key columns. The atomic upsert is used.

    * SQLite: tables may be legacy and lack a PRIMARY KEY on the key columns.
    A transactional DELETE + INSERT is used, which is safe under SQLite's
    single-writer model.

    Statements are not committed here: the caller manages the transactions.

    :param conn: An open SQLAlchemy Connection (caller manages the transaction).
    :param table: The target SQLAlchemy Table.
    :param values: Full row values dict (column name -> value) to insert.
    :param index_elements: Conflict target. List of column names or Column objects.
    :param set_: Columns to update on conflict (upsert only). If None, all
        columns except index_elements will be updated.
    :return: rowcount of the executed insert statement.
    """

    if conn.dialect.name == "postgresql":
        return execute_upsert(conn, table, values, index_elements, set_)
    return execute_replace(conn, table, values, index_elements)
