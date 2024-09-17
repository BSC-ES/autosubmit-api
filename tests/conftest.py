# Conftest file for sharing fixtures
# Reference: https://docs.pytest.org/en/latest/reference/fixtures.html#conftest-py-sharing-fixtures-across-multiple-files

import os
import tempfile
from flask import Flask
import pytest
from autosubmit_api.app import create_app
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api import config

FAKE_EXP_DIR = "./tests/experiments/"


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
