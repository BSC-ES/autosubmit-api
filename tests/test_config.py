import os
import pytest
from autosubmit_api.config.confConfigStrategy import confConfigStrategy
from autosubmit_api.config.basicConfig import APIBasicConfig

from autosubmit_api.config.config_common import AutosubmitConfigResolver
from autosubmit_api.config.ymlConfigStrategy import ymlConfigStrategy

from tests.common_fixtures import fixture_mock_basic_config
from tests.custom_utils import custom_return_value


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

    def test_files_init_conf(
        self, fixture_mock_basic_config: fixture_mock_basic_config
    ):
        resolver = AutosubmitConfigResolver("a3tb", APIBasicConfig, None)
        assert isinstance(resolver._configWrapper, confConfigStrategy)
