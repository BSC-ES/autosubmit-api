from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.database import tables
from autosubmit_api.database.common import get_postgres_engine, table_change_schema
from autosubmit_api.persistance.experiment import ExperimentPaths


from sqlalchemy import NullPool, create_engine
from sqlalchemy.schema import CreateSchema


from typing import Any, Dict, List


class ExpGraphDrawDBAdapter:

    def __init__(self, expid: str) -> None:
        self.expid = expid

        if APIBasicConfig.DATABASE_BACKEND == "postgres":
            self.table = table_change_schema(expid, tables.GraphDataTable)
            self.engine = get_postgres_engine()
            with self.engine.connect() as conn:
                conn.execute(CreateSchema(self.expid, if_not_exists=True))
                self.table.create(conn, checkfirst=True)
                conn.commit()

        else:
            self.table = tables.GraphDataTable.__table__
            sqlite_graph_db_path = ExperimentPaths(expid).graph_data_db
            self.engine = create_engine(
                f"sqlite:///{ sqlite_graph_db_path}", poolclass=NullPool
            )
            with self.engine.connect() as conn:
                self.table.create(conn, checkfirst=True)
                conn.commit()

    def get_all(self) -> List[Dict[str, Any]]:
        with self.engine.connect() as conn:
            result = conn.execute(self.table.select()).all()

        return [x._mapping for x in result]

    def delete_all(self) -> int:
        with self.engine.connect() as conn:
            result = conn.execute(self.table.delete())
            conn.commit()
        return result.rowcount

    def insert_many(self, values) -> int:
        with self.engine.connect() as conn:
            result = conn.execute(self.table.insert(), values)
            conn.commit()
        return result.rowcount



