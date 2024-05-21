# Conftest file for sharing fixtures
# Reference: https://docs.pytest.org/en/latest/reference/fixtures.html#conftest-py-sharing-fixtures-across-multiple-files

import os
import tempfile
from flask import Flask
import pytest
from autosubmit_api.app import create_app
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api import config
from tests.custom_utils import custom_return_value
from autosubmit.database import session
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy import create_engine

FAKE_EXP_DIR = "./tests/experiments/"
DEFAULT_DATABASE_CONN_URL = (
    "postgresql://postgres:mysecretpassword@localhost:5432/autosubmit_test"
)


# FIXTURES ####

# Config fixtures


@pytest.fixture(autouse=True)
def fixture_disable_protection(monkeypatch: pytest.MonkeyPatch):
    """
    This fixture disables the protection level for all the tests.

    Autouse is set, so, no need to put this fixture in the test function.
    """
    monkeypatch.setattr(config, "PROTECTION_LEVEL", "NONE")
    monkeypatch.setenv("PROTECTION_LEVEL", "NONE")


@pytest.fixture
def fixture_mock_basic_config(
    monkeypatch: pytest.MonkeyPatch, fixture_gen_rc_sqlite: str
):
    """
    Sets a mock basic config for the tests.
    """
    # Set the environment variable
    monkeypatch.setenv(
        "AUTOSUBMIT_CONFIGURATION", os.path.join(fixture_gen_rc_sqlite, ".autosubmitrc")
    )
    yield APIBasicConfig


# Flask app fixtures


@pytest.fixture
def fixture_app(fixture_mock_basic_config):
    app = create_app()
    app.config.update(
        {
            "TESTING": True,
        }
    )
    yield app


@pytest.fixture
def fixture_client(fixture_app: Flask):
    return fixture_app.test_client()


@pytest.fixture
def fixture_runner(fixture_app: Flask):
    return fixture_app.test_cli_runner()


# Database fixtures


@pytest.fixture
def fixture_pg_db(monkeypatch: pytest.MonkeyPatch, fixture_mock_basic_config):
    """
    This fixture sets up a PostgreSQL database for testing purposes.
    """
    # Apply patch BasicConfig
    monkeypatch.setattr(APIBasicConfig, "read", custom_return_value())
    monkeypatch.setattr(APIBasicConfig, "DATABASE_BACKEND", "postgres")
    monkeypatch.setattr(
        APIBasicConfig,
        "DATABASE_CONN_URL",
        os.environ.get("PYTEST_DATABASE_CONN_URL", DEFAULT_DATABASE_CONN_URL),
    )

    # Mock the session
    MockSession = scoped_session(
        sessionmaker(
            bind=create_engine(
                os.environ.get("PYTEST_DATABASE_CONN_URL", DEFAULT_DATABASE_CONN_URL)
            )
        )
    )
    monkeypatch.setattr(session, "Session", custom_return_value(MockSession))

    # Copy files from FAKEDIR to the temporary directory except .db files
    with tempfile.TemporaryDirectory() as tempdir:
        # Copy all files recursively excluding .db files

        # Patch the LOCAL_ROOT_DIR
        monkeypatch.setattr(APIBasicConfig, "LOCAL_ROOT_DIR", tempdir)


# Fixtures


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
