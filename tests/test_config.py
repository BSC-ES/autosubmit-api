import os
from typing import Dict
from unittest.mock import patch

import pytest

from autosubmit_api.config.config_file import DEFAULT_CONFIG_PATH, read_config_file_path
from autosubmit_api.runners.runner_config import check_runner_permissions
from autosubmit_api.runners.runner_config import parse_runners_config


class TestAPIConfigFile:
    def test_api_config_file_path(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("AS_API_CONFIG_FILE", raising=False)
        assert read_config_file_path() == os.path.expanduser(DEFAULT_CONFIG_PATH)

        monkeypatch.setenv("AS_API_CONFIG_FILE", "test_config.yaml")
        assert read_config_file_path() == "test_config.yaml"

    @pytest.mark.parametrize(
        "config_content, expected_parsed_config",
        [
            pytest.param(
                {},
                {
                    "LOCAL": {
                        "ENABLED": False,
                        "MODULE_LOADERS": {
                            "CONDA": {"ENABLED": False, "MODULES_WHITELIST": []},
                            "VENV": {"ENABLED": False, "MODULES_WHITELIST": []},
                            "LMOD": {"ENABLED": False, "MODULES_WHITELIST": []},
                            "NO_MODULE": {"ENABLED": False},
                        },
                    },
                    "SSH": {
                        "ENABLED": False,
                        "MODULE_LOADERS": {
                            "CONDA": {"ENABLED": False, "MODULES_WHITELIST": []},
                            "VENV": {"ENABLED": False, "MODULES_WHITELIST": []},
                            "LMOD": {"ENABLED": False, "MODULES_WHITELIST": []},
                            "NO_MODULE": {"ENABLED": False},
                        },
                    },
                },
                id="empty_config",
            ),
            pytest.param(
                {
                    "RUNNERS": {
                        "LOCAL": {
                            "ENABLED": True,
                            "MODULE_LOADERS": {
                                "CONDA": {
                                    "ENABLED": True,
                                    "MODULES_WHITELIST": ["python3_8"],
                                },
                                "VENV": {"ENABLED": False},
                            },
                        },
                        "SSH": {"ENABLED": True},
                    }
                },
                {
                    "LOCAL": {
                        "ENABLED": True,
                        "MODULE_LOADERS": {
                            "CONDA": {
                                "ENABLED": True,
                                "MODULES_WHITELIST": ["python3_8"],
                            },
                            "VENV": {"ENABLED": False, "MODULES_WHITELIST": []},
                            "LMOD": {"ENABLED": False, "MODULES_WHITELIST": []},
                            "NO_MODULE": {"ENABLED": False},
                        },
                    },
                    "SSH": {
                        "ENABLED": True,
                        "MODULE_LOADERS": {
                            "CONDA": {"ENABLED": False, "MODULES_WHITELIST": []},
                            "VENV": {"ENABLED": False, "MODULES_WHITELIST": []},
                            "LMOD": {"ENABLED": False, "MODULES_WHITELIST": []},
                            "NO_MODULE": {"ENABLED": False},
                        },
                    },
                },
                id="partial_config",
            ),
            pytest.param(
                {
                    "RUNNERS": {
                        "LOCAL": {
                            "ENABLED": True,
                            "MODULE_LOADERS": {
                                "CONDA": {
                                    "ENABLED": True,
                                    "MODULES_WHITELIST": ["python3_8"],
                                    "FOO": "BAR",
                                },
                                "NO_MODULE": {
                                    "ENABLED": True,
                                    "MODULES_WHITELIST": ["python_3_9"],
                                    "EXTRA": 123,
                                },
                            },
                        }
                    }
                },
                {
                    "LOCAL": {
                        "ENABLED": True,
                        "MODULE_LOADERS": {
                            "CONDA": {
                                "ENABLED": True,
                                "MODULES_WHITELIST": ["python3_8"],
                            },
                            "VENV": {"ENABLED": False, "MODULES_WHITELIST": []},
                            "LMOD": {"ENABLED": False, "MODULES_WHITELIST": []},
                            "NO_MODULE": {"ENABLED": True},
                        },
                    },
                    "SSH": {
                        "ENABLED": False,
                        "MODULE_LOADERS": {
                            "CONDA": {"ENABLED": False, "MODULES_WHITELIST": []},
                            "VENV": {"ENABLED": False, "MODULES_WHITELIST": []},
                            "LMOD": {"ENABLED": False, "MODULES_WHITELIST": []},
                            "NO_MODULE": {"ENABLED": False},
                        },
                    },
                },
                id="with_invalid_options",
            ),
        ],
    )
    def test_parse_runners_config(
        self, config_content: Dict, expected_parsed_config: Dict
    ):
        """
        Test the parse_runners_config function with different configurations.
        """
        with patch(
            "autosubmit_api.runners.runner_config.read_config_file"
        ) as mock_read_config:
            mock_read_config.return_value = config_content

            parsed_config = parse_runners_config()

            assert parsed_config == expected_parsed_config

    @pytest.mark.parametrize(
        "runner, module_loader, config_content, expected",
        [
            pytest.param("foo", "bar", {}, False, id="no_config"),
            pytest.param(
                "runner1",
                "module_loader1",
                {"RUNNERS": {"RUNNER1": {"ENABLED": True}}},
                False,
                id="runner_enabled_no_module_loader",
            ),
            pytest.param(
                "runner1",
                "module_loader1",
                {
                    "RUNNERS": {
                        "RUNNER1": {
                            "ENABLED": True,
                            "MODULE_LOADERS": {"MODULE_LOADER1": {"ENABLED": True}},
                        }
                    }
                },
                True,
                id="runner_and_module_loader_enabled",
            ),
            pytest.param(
                "runner1",
                "module_loader1",
                {
                    "RUNNERS": {
                        "RUNNER1": {
                            "ENABLED": True,
                            "MODULE_LOADERS": {"MODULE_LOADER1": {"ENABLED": False}},
                        }
                    }
                },
                False,
                id="runner_enabled_module_loader_disabled",
            ),
        ],
    )
    def test_runners_permissions(
        self, runner: str, module_loader: str, config_content: Dict, expected: bool
    ):
        """
        Test the check_runner_permissions function with different configurations.
        """
        with patch(
            "autosubmit_api.runners.runner_config.read_config_file"
        ) as mock_read_config:
            mock_read_config.return_value = config_content

            result = check_runner_permissions(runner, module_loader)

            assert result == expected
