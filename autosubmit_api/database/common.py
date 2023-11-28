import os
from typing import Any
from sqlalchemy import Connection, Select, create_engine, select, text, func
from autosubmit_api.logger import logger
from autosubmit_api.config.basicConfig import APIBasicConfig


def create_main_db_conn():
    APIBasicConfig.read()
    autosubmit_db_path = os.path.abspath(APIBasicConfig.DB_PATH)
    as_times_db_path = os.path.join(APIBasicConfig.DB_DIR, APIBasicConfig.AS_TIMES_DB)
    engine = create_engine("sqlite://")
    conn = engine.connect()
    conn.execute(text(f"attach database '{autosubmit_db_path}' as autosubmit;"))
    conn.execute(text(f"attach database '{as_times_db_path}' as as_times;"))
    return conn


def create_autosubmit_db_engine():
    APIBasicConfig.read()
    return create_engine(f"sqlite:///{ os.path.abspath(APIBasicConfig.DB_PATH)}")


def create_as_times_db_engine():
    APIBasicConfig.read()
    db_path = os.path.join(APIBasicConfig.DB_DIR, APIBasicConfig.AS_TIMES_DB)
    return create_engine(f"sqlite:///{ os.path.abspath(db_path)}")


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
