import os
import pytest
from autosubmit_api.common.utils import JobSection
from autosubmit_api.config.confConfigStrategy import confConfigStrategy
from autosubmit_api.config.basicConfig import APIBasicConfig

from autosubmit_api.config.config_common import AutosubmitConfigResolver
from autosubmit_api.config.config_file import DEFAULT_CONFIG_PATH, read_config_file_path
from autosubmit_api.config.ymlConfigStrategy import ymlConfigStrategy

from tests.utils import custom_return_value


class TestAPIConfigFile:
    def test_api_config_file_path(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("AS_API_CONFIG_FILE", raising=False)
        assert read_config_file_path() == os.path.expanduser(DEFAULT_CONFIG_PATH)

        monkeypatch.setenv("AS_API_CONFIG_FILE", "test_config.yaml")
        assert read_config_file_path() == "test_config.yaml"


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
