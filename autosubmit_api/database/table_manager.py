from abc import ABC, abstractmethod
import os
from typing import Any, Dict, List, Optional, Type, Union
from sqlalchemy import Connection, Engine, Table, delete, insert, select
from sqlalchemy.schema import CreateTable, CreateSchema, DropTable
from sqlalchemy.orm import DeclarativeBase
from autosubmit_api.database import tables, session

from autosubmit_api.config.basicConfig import APIBasicConfig


class DbTableManager(ABC):
    engine: Engine
    table: Table

    @abstractmethod
    def __init__(
        self,
        table: Union[Type[DeclarativeBase], Table],
        db_filepath: str = None,
        schema: Optional[str] = None,
    ) -> None:
        """
        Class to manage a database table with common methods
        :param table: SQLAlchemy Table
        :param db_filepath: File path location in case of SQLite is used as database backend
        :param schema: Almost always same as expid. Postgres database schema in case this is a distributed table.
        """
        self.schema = schema
        self.db_filepath = db_filepath
        if isinstance(table, type) and issubclass(table, DeclarativeBase):
            self.table = table.__table__
        else:
            self.table = table

    def get_connection(self) -> Connection:
        return self.engine.connect()

    def create_table(self, conn: Connection):
        """
        Create table
        """
        conn.execute(CreateTable(self.table, if_not_exists=True))
        conn.commit()

    def drop_table(self, conn: Connection):
        """
        Drops the table
        """
        conn.execute(DropTable(self.table, if_exists=True))
        conn.commit()

    def insert_many(self, conn: Connection, values: List[Dict[str, Any]]) -> int:
        """
        Insert many values
        """
        result = conn.execute(insert(self.table), values)
        conn.commit()
        return result.rowcount

    def select_all(self, conn: Connection):
        rows = conn.execute(select(self.table)).all()
        return rows

    def delete_all(self, conn: Connection) -> int:
        """
        Deletes all the rows of the table
        """
        result = conn.execute(delete(self.table))
        conn.commit()
        return result.rowcount


class SQLiteDbTableManager(DbTableManager):
    def __init__(
        self,
        table: Union[Type[DeclarativeBase], Table],
        db_filepath: str = None,
        schema: Optional[str] = None,
    ) -> None:
        super().__init__(table, db_filepath, schema)
        self.engine = session.create_sqlite_engine(self.db_filepath)


class PostgresDbTableManager(DbTableManager):
    def __init__(
        self,
        table: Union[Type[DeclarativeBase], Table],
        db_filepath: str = None,
        schema: Optional[str] = None,
    ) -> None:
        super().__init__(table, db_filepath, schema)
        self.engine = session.Session().bind
        if schema:
            self.table = tables.table_change_schema(schema, table)

    def create_table(self, conn: Connection):
        """
        Create table and the schema (if applicable)
        """
        if self.schema:
            conn.execute(CreateSchema(self.schema, if_not_exists=True))
        super().create_table(conn)


def create_db_table_manager(
    table: Union[Type[DeclarativeBase], Table],
    db_filepath: str = None,
    schema: Optional[str] = None,
) -> DbTableManager:
    """
    Creates a Postgres or SQLite DbTableManager depending on the Autosubmit configuration
    :param table: SQLAlchemy Table
    :param db_filepath: File path location in case of SQLite is used as database backend
    :param schema: Almost always same as expid. Postgres database schema in case this is a distributed table.
    """
    APIBasicConfig.read()
    if APIBasicConfig.DATABASE_BACKEND == "postgres":
        return PostgresDbTableManager(table, db_filepath, schema)
    elif APIBasicConfig.DATABASE_BACKEND == "sqlite":
        return SQLiteDbTableManager(table, db_filepath, schema)
    else:
        raise Exception("Invalid DATABASE_BACKEND")
