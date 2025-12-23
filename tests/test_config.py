import os

import pytest

from autosubmit_api.config.config_file import DEFAULT_CONFIG_PATH, read_config_file_path


class TestAPIConfigFile:
    def test_api_config_file_path(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("AS_API_CONFIG_FILE", raising=False)
        assert read_config_file_path() == os.path.expanduser(DEFAULT_CONFIG_PATH)

        monkeypatch.setenv("AS_API_CONFIG_FILE", "test_config.yaml")
        assert read_config_file_path() == "test_config.yaml"
