from http import HTTPStatus
import re
from typing import List
from sqlalchemy import Connection, Engine, create_engine, insert, select, text

from autosubmit_api.database import tables
from sqlalchemy.schema import CreateSchema, CreateTable


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


def copy_structure_db(filepath: str, engine: Engine):
    """
    This function copies the content of the FAKE_EXP_DIR/metadata/structures to the Postgres database
    """
    # Get the xxxx from structure_xxxx.db with regex
    match = re.search(r"structure_(\w+)\.db", filepath)
    expid = match.group(1)

    # Get SQLite source data
    source_as_db = create_engine(f"sqlite:///{filepath}")
    with source_as_db.connect() as source_conn:
        structures_rows = source_conn.execute(
            select(tables.ExperimentStructureTable)
        ).all()

    # Copy data to the Postgres database
    with engine.connect() as conn:
        conn.execute(CreateSchema(expid, if_not_exists=True))
        target_table = tables.table_change_schema(
            expid, tables.ExperimentStructureTable
        )
        conn.execute(CreateTable(target_table, if_not_exists=True))
        if len(structures_rows) > 0:
            conn.execute(
                insert(target_table), [row._asdict() for row in structures_rows]
            )
        conn.commit()


def copy_job_data_db(filepath: str, engine: Engine):
    """
    This function copies the content of the FAKE_EXP_DIR/metadata/data to the Postgres database
    """
    # Get the xxxx from job_data_xxxx.db with regex
    match = re.search(r"job_data_(\w+)\.db", filepath)
    expid = match.group(1)
    # Get SQLite source data
    source_as_db = create_engine(f"sqlite:///{filepath}")
    with source_as_db.connect() as source_conn:
        job_data_rows = source_conn.execute(select(tables.JobDataTable)).all()
        exprun_rows = source_conn.execute(select(tables.ExperimentRunTable)).all()

    # Copy data to the Postgres database
    with engine.connect() as conn:
        conn.execute(CreateSchema(expid, if_not_exists=True))
        # Job data
        target_table = tables.table_change_schema(expid, tables.JobDataTable)
        conn.execute(CreateTable(target_table, if_not_exists=True))
        if len(job_data_rows) > 0:
            conn.execute(insert(target_table),[row._asdict() for row in job_data_rows])
        # Experiment run
        target_table = tables.table_change_schema(expid, tables.ExperimentRunTable)
        conn.execute(CreateTable(target_table, if_not_exists=True))
        if len(exprun_rows) > 0:
            conn.execute(insert(target_table),[row._asdict() for row in exprun_rows])
        conn.commit()


def copy_graph_data_db(filepath: str, engine: Engine):
    """
    This function copies the content of the FAKE_EXP_DIR/metadata/graph to the Postgres database
    """
    # Get the xxxx from graph_xxxx.db with regex
    match = re.search(r"graph_data_(\w+)\.db", filepath)
    expid = match.group(1)

    # Get SQLite source data
    source_as_db = create_engine(f"sqlite:///{filepath}")
    with source_as_db.connect() as source_conn:
        graph_rows = source_conn.execute(select(tables.GraphDataTable)).all()

    # Copy data to the Postgres database
    with engine.connect() as conn:
        conn.execute(CreateSchema(expid, if_not_exists=True))
        target_table = tables.table_change_schema(expid, tables.GraphDataTable)
        conn.execute(CreateTable(target_table, if_not_exists=True))
        if len(graph_rows) > 0:
            conn.execute(insert(target_table),[row._asdict() for row in graph_rows])
        conn.commit()


def copy_autosubmit_db(filepath: str, engine: Engine):
    """
    This function copies the content of the FAKE_EXP_DIR/autosubmit.db to the Postgres database
    """
    # Get SQLite source data
    source_as_db = create_engine(f"sqlite:///{filepath}")
    with source_as_db.connect() as source_conn:
        exp_rows = source_conn.execute(select(tables.ExperimentTable)).all()
        details_rows = source_conn.execute(select(tables.DetailsTable)).all()

    # Copy data to the Postgres database
    with engine.connect() as conn:
        conn.execute(CreateTable(tables.ExperimentTable, if_not_exists=True))
        conn.execute(insert(tables.ExperimentTable),[row._asdict() for row in exp_rows])
        conn.execute(CreateTable(tables.DetailsTable, if_not_exists=True))
        conn.execute(insert(tables.DetailsTable),[row._asdict() for row in details_rows])
        conn.commit()


def copy_as_times_db(filepath: str, engine: Engine):
    """
    This function copies the content of the FAKE_EXP_DIR/as_times.db to the Postgres database
    """
    # Get SQLite source data
    source_as_db = create_engine(f"sqlite:///{filepath}")
    with source_as_db.connect() as source_conn:
        as_times_rows = source_conn.execute(select(tables.ExperimentStatusTable)).all()

    # Copy data to the Postgres database
    with engine.connect() as conn:
        conn.execute(CreateTable(tables.ExperimentStatusTable, if_not_exists=True))
        conn.execute(insert(tables.ExperimentStatusTable),[row._asdict() for row in as_times_rows])
        conn.commit()


def copy_job_packages_db(filepath: str, engine: Engine):
    """
    This function copies the content of the FAKE_EXP_DIR/pkl/job_packages to the Postgres database
    """
    # Get the xxxx from job_packages_xxxx.db with regex
    match = re.search(r"job_packages_(\w+)\.db", filepath)
    expid = match.group(1)

    # Get SQLite source data
    source_as_db = create_engine(f"sqlite:///{filepath}")
    with source_as_db.connect() as source_conn:
        job_packages_rows = source_conn.execute(select(tables.JobPackageTable)).all()
        wrapper_job_packages_rows = source_conn.execute(select(tables.WrapperJobPackageTable)).all()

    # Copy data to the Postgres database
    with engine.connect() as conn:
        conn.execute(CreateSchema(expid, if_not_exists=True))
        # Job packages
        target_table = tables.table_change_schema(expid, tables.JobPackageTable)
        conn.execute(CreateTable(target_table, if_not_exists=True))
        if len(job_packages_rows) > 0:
            conn.execute(insert(target_table),[row._asdict() for row in job_packages_rows])
        # Wrapper job packages
        target_table = tables.table_change_schema(expid, tables.WrapperJobPackageTable)
        conn.execute(CreateTable(target_table, if_not_exists=True))
        if len(wrapper_job_packages_rows) > 0:
            conn.execute(insert(target_table),[row._asdict() for row in wrapper_job_packages_rows])
        conn.commit()
