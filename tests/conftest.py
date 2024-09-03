# Conftest file for sharing fixtures
# Reference: https://docs.pytest.org/en/latest/reference/fixtures.html#conftest-py-sharing-fixtures-across-multiple-files

import os
from flask import Flask
import pytest
from autosubmit_api.app import create_app
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api import config

FAKE_EXP_DIR = "./tests/experiments/"


#### FIXTURES ####
@pytest.fixture(autouse=True)
def fixture_disable_protection(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(config, "PROTECTION_LEVEL", "NONE")
    monkeypatch.setenv("PROTECTION_LEVEL", "NONE")


@pytest.fixture
def fixture_mock_basic_config(monkeypatch: pytest.MonkeyPatch):
    # Get APIBasicConfig from file
    monkeypatch.setenv("AUTOSUBMIT_CONFIGURATION", os.path.join(FAKE_EXP_DIR, ".autosubmitrc"))
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
