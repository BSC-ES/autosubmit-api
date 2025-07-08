from datetime import datetime
import os

import pytest
from bscearth.utils.config_parser import ConfigParserFactory

from autosubmit_api.common.utils import JobSection
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.config.confConfigStrategy import confConfigStrategy
from autosubmit_api.config.config_common import AutosubmitConfigResolver
from autosubmit_api.config.ymlConfigStrategy import ymlConfigStrategy
from tests.utils import custom_return_value


class TestConfigResolver:
    def test_simple_init(self, monkeypatch: pytest.MonkeyPatch):
        # Conf test decision
        monkeypatch.setattr(os.path, "exists", custom_return_value(True))
        monkeypatch.setattr(confConfigStrategy, "__init__", custom_return_value(None))
        resolver = AutosubmitConfigResolver("----", APIBasicConfig, None)
        assert isinstance(resolver._configWrapper, confConfigStrategy)

        # YML test decision
        monkeypatch.setattr(os.path, "exists", custom_return_value(False))
        monkeypatch.setattr(ymlConfigStrategy, "__init__", custom_return_value(None))
        resolver = AutosubmitConfigResolver("----", APIBasicConfig, None)
        assert isinstance(resolver._configWrapper, ymlConfigStrategy)

    def test_files_init_conf(self, fixture_mock_basic_config):
        resolver = AutosubmitConfigResolver("a3tb", fixture_mock_basic_config, None)
        assert isinstance(resolver._configWrapper, confConfigStrategy)


class TestYMLConfigStrategy:
    def test_exclusive(self, fixture_mock_basic_config):
        wrapper = ymlConfigStrategy("a007", fixture_mock_basic_config)
        assert wrapper.get_exclusive(JobSection.SIM) is True

        wrapper = ymlConfigStrategy("a003", fixture_mock_basic_config)
        assert wrapper.get_exclusive(JobSection.SIM) is False


def test_as3_conf(fixture_mock_basic_config):
    as_conf = AutosubmitConfigResolver(
        "a3tb", fixture_mock_basic_config, ConfigParserFactory()
    )
    as_conf.reload()

    assert as_conf.get_retrials() == 0
    assert as_conf.get_version() == "3.13.0"
    assert as_conf.get_safetysleeptime() == 10
    assert as_conf.get_num_chunks() == 3

    assert as_conf.get_chunk_ini() == 1
    assert as_conf.get_chunk_size() == 1
    assert as_conf.get_chunk_size_unit() == "month"

    assert as_conf.check_conf_files() is True
    assert as_conf.check_platforms_conf() is True
    assert as_conf.check_proj() is True

    assert as_conf.get_project_destination() == "auto-ecearth3"

    assert as_conf.get_date_list() == [
        datetime(1993, 1, 1, 0, 0),
        datetime(1993, 5, 1, 0, 0),
    ]
    assert as_conf.get_member_list() == ["fc01"]
    assert as_conf.get_chunk_list() == ""

    assert as_conf.is_valid_communications_library() is True
    assert as_conf.is_valid_storage_type() is True
    assert as_conf.is_valid_jobs_in_wrapper() is True
    assert as_conf.is_valid_git_repository() is True

    assert isinstance(as_conf.load_parameters(), dict)

    assert as_conf.is_valid_mail_address("autosubmit-support@bsc.es") is True
    assert as_conf.is_valid_mail_address("autosubmit@bsc") is False


def test_as4_yml_conf(fixture_mock_basic_config):
    as_conf = AutosubmitConfigResolver(
        "a007", fixture_mock_basic_config, ConfigParserFactory()
    )
    as_conf.reload()

    assert as_conf.get_retrials() == 0
    assert as_conf.get_version() == "4.0.95"
    assert as_conf.get_safetysleeptime() == 10
    assert as_conf.get_num_chunks() == 2

    assert as_conf.get_chunk_ini() == 1
    assert as_conf.get_chunk_size() == 4
    assert as_conf.get_chunk_size_unit() == "month"

    assert as_conf.check_conf_files() is True
    assert as_conf.check_platforms_conf() is True
    # assert as_conf.check_proj() is True # Not implemented

    assert as_conf.get_project_destination() == ""

    assert as_conf.get_date_list() == [datetime(2000, 1, 1, 0, 0)]
    assert as_conf.get_member_list() == ["fc0"]
    # assert as_conf.get_chunk_list() == "" # Not implemented

    assert as_conf.is_valid_communications_library() is True
    assert as_conf.is_valid_storage_type() is True

    assert isinstance(as_conf.load_parameters(), dict)

    assert as_conf.is_valid_mail_address("autosubmit-support@bsc.es") is True
    assert as_conf.is_valid_mail_address("autosubmit@bsc") is False
