from sqlalchemy import Connection, Table
from autosubmit_api.database.common import (
    create_as_times_db_engine,
    create_autosubmit_db_engine,
)
from autosubmit_api.database import tables


def _create_autosubmit_db_tables(conn: Connection):
    experiment_table: Table = tables.ExperimentTable.__table__
    experiment_table.create(conn, checkfirst=True)
    details_table: Table = tables.DetailsTable.__table__
    details_table.create(conn, checkfirst=True)


def _create_as_times_db_tables(conn: Connection):
    experiment_status_table: Table = tables.ExperimentStatusTable.__table__
    experiment_status_table.create(conn, checkfirst=True)


def prepare_db():
    with create_as_times_db_engine().connect() as conn:
        _create_as_times_db_tables(conn)
        conn.commit()

    with create_autosubmit_db_engine().connect() as conn:
        _create_autosubmit_db_tables(conn)
        conn.commit()
