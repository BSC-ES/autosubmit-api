# Conftest file for sharing fixtures
# Reference: https://docs.pytest.org/en/latest/reference/fixtures.html#conftest-py-sharing-fixtures-across-multiple-files

import os
import tempfile
from typing import Tuple

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from testcontainers.postgres import PostgresContainer

from autosubmit_api import config
from autosubmit_api.config.basicConfig import APIBasicConfig
from tests import utils

FAKE_EXP_DIR = "./tests/experiments/"
DEFAULT_DATABASE_CONN_URL = (
    "postgresql://postgres:mysecretpassword@localhost:5432/autosubmit_test"
)


@pytest.fixture(autouse=True)
def fixture_disable_protection(monkeypatch: pytest.MonkeyPatch):
    """
    This fixture disables the protection level for all the tests.

    Autouse is set, so, no need to put this fixture in the test function.
    """
    monkeypatch.setattr(config, "PROTECTION_LEVEL", "NONE")
    monkeypatch.setenv("PROTECTION_LEVEL", "NONE")


@pytest.fixture(
    params=[
        pytest.param("fixture_sqlite", marks=pytest.mark.sqlite),
        pytest.param("fixture_postgres", marks=pytest.mark.postgres),
    ]
)
def fixture_mock_basic_config(request: pytest.FixtureRequest):
    """
    Sets a mock basic config for the tests.
    """
    request.getfixturevalue(request.param)
    APIBasicConfig.read()
    yield APIBasicConfig


@pytest.fixture
def fixture_fastapi_client(fixture_mock_basic_config):
    from autosubmit_api import app

    with TestClient(app.app) as client:
        yield client


# Fixtures sqlite


@pytest.fixture(scope="session")
def fixture_temp_dir_copy():
    """
    Fixture that copies the contents of the FAKE_EXP_DIR to a temporary directory with rsync
    """
    with tempfile.TemporaryDirectory() as tempdir:
        # Copy all files recursively
        os.system(f"rsync -r {FAKE_EXP_DIR} {tempdir}")
        yield tempdir


@pytest.fixture(scope="session")
def fixture_gen_rc_sqlite(fixture_temp_dir_copy: str):
    """
    Fixture that generates a .autosubmitrc file in the temporary directory
    """
    rc_file = os.path.join(fixture_temp_dir_copy, ".autosubmitrc")
    with open(rc_file, "w") as f:
        f.write(
            "\n".join(
                [
                    "[database]",
                    f"path = {fixture_temp_dir_copy}",
                    "filename = autosubmit.db",
                    "backend = sqlite",
                    "[local]",
                    f"path = {fixture_temp_dir_copy}",
                    "[globallogs]",
                    f"path = {fixture_temp_dir_copy}/logs",
                    "[historicdb]",
                    f"path = {fixture_temp_dir_copy}/metadata/data",
                    "[structures]",
                    f"path = {fixture_temp_dir_copy}/metadata/structures",
                    "[historiclog]",
                    f"path = {fixture_temp_dir_copy}/metadata/logs",
                    "[graph]",
                    f"path = {fixture_temp_dir_copy}/metadata/graph",
                ]
            )
        )
    yield fixture_temp_dir_copy


@pytest.fixture
def fixture_sqlite(fixture_gen_rc_sqlite: str, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv(
        "AUTOSUBMIT_CONFIGURATION", os.path.join(fixture_gen_rc_sqlite, ".autosubmitrc")
    )
    yield fixture_gen_rc_sqlite


# Fixtures Postgres


@pytest.fixture(scope="session")
def fixture_temp_dir_copy_exclude_db():
    """
    Fixture that copies the contents of the FAKE_EXP_DIR to a temporary directory with rsync
    and exclues .db files
    """
    with tempfile.TemporaryDirectory() as tempdir:
        # Copy all files recursively excluding .db files
        os.system(f"rsync -r --exclude '*.db' {FAKE_EXP_DIR} {tempdir}")
        yield tempdir


@pytest.fixture(scope="session")
def fixture_setup_pg_db():
    """
    Fixture that sets up a PostgreSQL database container for testing purposes.
    """
    IMAGE = "postgres:17"
    _PG_PORT = 25432
    _PG_USER = "postgres"
    _PG_PASSWORD = "mysecretpassword"
    _PG_DB = "autosubmit_test"
    with PostgresContainer(
        image=IMAGE,
        port=5432,
        username=_PG_USER,
        password=_PG_PASSWORD,
        dbname=_PG_DB,
    ).with_bind_ports(5432, _PG_PORT) as postgres:
        conn_url = f"postgresql://{_PG_USER}:{_PG_PASSWORD}@{postgres.get_container_host_ip()}:{_PG_PORT}/{_PG_DB}"

        engine = create_engine(conn_url)

        with engine.connect() as conn:
            utils.setup_pg_db(conn)
            conn.commit()

        yield conn_url


@pytest.fixture(scope="session")
def fixture_gen_rc_pg(fixture_temp_dir_copy_exclude_db: str, fixture_setup_pg_db: str):
    """
    Fixture that generates a .autosubmitrc file in the temporary directory
    """
    rc_file = os.path.join(fixture_temp_dir_copy_exclude_db, ".autosubmitrc")
    conn_url = fixture_setup_pg_db
    with open(rc_file, "w") as f:
        f.write(
            "\n".join(
                [
                    "[database]",
                    f"path = {fixture_temp_dir_copy_exclude_db}",
                    "backend = postgres",
                    f"connection_url = {conn_url}",
                    "[local]",
                    f"path = {fixture_temp_dir_copy_exclude_db}",
                    "[globallogs]",
                    f"path = {fixture_temp_dir_copy_exclude_db}/logs",
                    "[historicdb]",
                    f"path = {fixture_temp_dir_copy_exclude_db}/metadata/data",
                    "[structures]",
                    f"path = {fixture_temp_dir_copy_exclude_db}/metadata/structures",
                    "[historiclog]",
                    f"path = {fixture_temp_dir_copy_exclude_db}/metadata/logs",
                    "[graph]",
                    f"path = {fixture_temp_dir_copy_exclude_db}/metadata/graph",
                ]
            )
        )
    yield (fixture_temp_dir_copy_exclude_db, conn_url)


@pytest.fixture(scope="session")
def fixture_pg_db_copy_all(fixture_gen_rc_pg: Tuple[str, str]):
    """
    This fixture recursively search all the .db files in the FAKE_EXP_DIR and copies them to the test database
    """
    engine = create_engine(fixture_gen_rc_pg[1])
    # Get .db files absolute paths from the FAKE_EXP_DIR recursively
    all_files = []
    all_pkl_files = []
    for root, dirs, files in os.walk(FAKE_EXP_DIR):
        for filepath in files:
            if filepath.endswith(".db"):
                all_files.append(os.path.join(root, filepath))
            if filepath.endswith(".pkl"):
                all_pkl_files.append(os.path.join(root, filepath))

    # Copy all the .db files to the test database
    for filepath in all_files:
        # Infer which type of DB is this
        if "metadata/structures" in filepath:
            utils.copy_structure_db(filepath, engine)
        elif "metadata/data" in filepath:
            utils.copy_job_data_db(filepath, engine)
        elif "metadata/graph" in filepath:
            utils.copy_graph_data_db(filepath, engine)
        elif "autosubmit.db" in filepath:
            utils.copy_autosubmit_db(filepath, engine)
        elif "as_times.db" in filepath:
            utils.copy_as_times_db(filepath, engine)
        elif "pkl/job_packages" in filepath:
            utils.copy_job_packages_db(filepath, engine)
        elif "tmp/metrics_" in filepath:
            utils.copy_user_metrics_db(filepath, engine)

    # Copy all the .pkl files to the test database
    utils.copy_pkls(all_pkl_files, engine)

    yield fixture_gen_rc_pg


@pytest.fixture
def fixture_postgres(
    fixture_pg_db_copy_all: Tuple[str, Engine], monkeypatch: pytest.MonkeyPatch
):
    """
    This fixture cleans and setup a PostgreSQL database for testing purposes.
    """
    monkeypatch.setenv(
        "AUTOSUBMIT_CONFIGURATION",
        os.path.join(fixture_pg_db_copy_all[0], ".autosubmitrc"),
    )
    yield fixture_pg_db_copy_all[0]
