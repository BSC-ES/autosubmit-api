import os
import re
from datetime import datetime
from http import HTTPStatus
from typing import List

from sqlalchemy import Connection, Engine, Table, create_engine, insert, select, text
from sqlalchemy.schema import CreateSchema, CreateTable

from autosubmit_api.database import tables


def dummy_response(*args, **kwargs):
    return "Hello World!", HTTPStatus.OK


def custom_return_value(value=None):
    def blank_func(*args, **kwargs):
        return value

    return blank_func


def get_schema_names(conn: Connection) -> List[str]:
    """
    Get all schema names that are not from the system
    """
    results = conn.execute(
        text(
            "SELECT schema_name FROM information_schema.schemata WHERE schema_name NOT LIKE 'pg_%' AND schema_name != 'information_schema'"
        )
    ).all()
    return [res[0] for res in results]


def setup_pg_db(conn: Connection):
    """
    Resets database by dropping all schemas except the system ones and restoring the public schema
    """
    # Get all schema names that are not from the system
    schema_names = get_schema_names(conn)

    # Drop all schemas
    for schema_name in schema_names:
        conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))

    # Restore default public schema
    conn.execute(text("CREATE SCHEMA public"))
    conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
    conn.execute(text("GRANT ALL ON SCHEMA public TO postgres"))


def _copy_table_data(
    source_conn: Connection,
    target_conn: Connection,
    expid: str,
    table: Table,
    schema_required=True,
):
    """
    Helper function to copy table data from SQLite to Postgres.
    """
    # Change schema if needed
    target_table = (
        tables.table_change_schema(expid, table) if expid and schema_required else table
    )
    if schema_required and expid:
        target_conn.execute(CreateSchema(expid, if_not_exists=True))
    target_conn.execute(CreateTable(target_table, if_not_exists=True))
    rows = source_conn.execute(select(table)).all()
    if rows:
        target_conn.execute(insert(target_table), [row._asdict() for row in rows])


def _get_expid_from_filename(pattern: str, filepath: str):
    match = re.search(pattern, filepath)
    return match.group(1) if match else None


def copy_structure_db(filepath: str, engine: Engine):
    expid = _get_expid_from_filename(r"structure_(\w+)\.db", filepath)
    source_as_db = create_engine(f"sqlite:///{filepath}")
    with source_as_db.connect() as source_conn, engine.connect() as conn:
        _copy_table_data(source_conn, conn, expid, tables.ExperimentStructureTable)
        conn.commit()


def copy_job_data_db(filepath: str, engine: Engine):
    expid = _get_expid_from_filename(r"job_data_(\w+)\.db", filepath)
    source_as_db = create_engine(f"sqlite:///{filepath}")
    with source_as_db.connect() as source_conn, engine.connect() as conn:
        job_data_table = tables.check_table_schema(
            source_as_db,
            [tables.JobDataTableV4_2_0, tables.JobDataTableV18, tables.JobDataTable],
        )
        _copy_table_data(source_conn, conn, expid, job_data_table)
        _copy_table_data(source_conn, conn, expid, tables.ExperimentRunTable)
        conn.commit()


def copy_graph_data_db(filepath: str, engine: Engine):
    expid = _get_expid_from_filename(r"graph_data_(\w+)\.db", filepath)
    source_as_db = create_engine(f"sqlite:///{filepath}")
    with source_as_db.connect() as source_conn, engine.connect() as conn:
        _copy_table_data(source_conn, conn, expid, tables.GraphDataTable)
        conn.commit()


def copy_autosubmit_db(filepath: str, engine: Engine):
    source_as_db = create_engine(f"sqlite:///{filepath}")
    with source_as_db.connect() as source_conn, engine.connect() as conn:
        _copy_table_data(
            source_conn, conn, None, tables.ExperimentTable, schema_required=False
        )
        _copy_table_data(
            source_conn, conn, None, tables.DetailsTable, schema_required=False
        )
        conn.commit()


def copy_as_times_db(filepath: str, engine: Engine):
    source_as_db = create_engine(f"sqlite:///{filepath}")
    with source_as_db.connect() as source_conn, engine.connect() as conn:
        _copy_table_data(
            source_conn, conn, None, tables.ExperimentStatusTable, schema_required=False
        )
        conn.commit()


def copy_job_packages_db(filepath: str, engine: Engine):
    expid = _get_expid_from_filename(r"job_packages_(\w+)\.db", filepath)
    source_as_db = create_engine(f"sqlite:///{filepath}")
    with source_as_db.connect() as source_conn, engine.connect() as conn:
        _copy_table_data(source_conn, conn, expid, tables.JobPackageTable)
        _copy_table_data(source_conn, conn, expid, tables.WrapperJobPackageTable)
        conn.commit()


def copy_user_metrics_db(filepath: str, engine: Engine):
    expid = _get_expid_from_filename(r"metrics_(\w+)\.db", filepath)
    source_as_db = create_engine(f"sqlite:///{filepath}")
    with source_as_db.connect() as source_conn, engine.connect() as conn:
        _copy_table_data(source_conn, conn, expid, tables.UserMetricTable)
        conn.commit()


def copy_pkls(filepaths: list[str], engine: Engine):
    """
    Copy all the .pkl files to the test database
    """
    with engine.connect() as conn:
        # Create the table if it doesn't exist
        conn.execute(
            CreateTable(
                tables.JobPklTable,
                if_not_exists=True,
            )
        )

        for filepath in filepaths:
            expid = _get_expid_from_filename(r"job_list_(\w+)\.pkl", filepath)
            with open(filepath, "rb") as f:
                data = f.read()
                modified_timestamp = int(os.stat(filepath).st_mtime)
                modified_datetime = datetime.fromtimestamp(
                    modified_timestamp
                ).isoformat()

            # Insert the data into the database
            conn.execute(
                insert(tables.JobPklTable),
                [
                    {
                        "expid": expid,
                        "pkl": data,
                        "modified": modified_datetime,
                    }
                ],
            )

        conn.commit()


def copy_job_list_db(filepath: str, engine: Engine):
    expid = _get_expid_from_filename(r"(\w+)\/db\/job_list\.db", filepath)
    source_as_db = create_engine(f"sqlite:///{filepath}")
    with source_as_db.connect() as source_conn, engine.connect() as conn:
        # Jobs Table
        _copy_table_data(source_conn, conn, expid, tables.JobsTable)
        # Job Wrappers Tables
        _copy_table_data(source_conn, conn, expid, tables.PreviewWrapperInfoTable)
        _copy_table_data(source_conn, conn, expid, tables.PreviewWrapperJobsTable)
        # Experiment Structure Table
        _copy_table_data(source_conn, conn, expid, tables.ExperimentStructureV4_2_0)
        conn.commit()
