from typing import Dict
from unittest.mock import patch

import pytest

from autosubmit_api.runners.runner_config import (
    check_runner_permissions,
    extend_profile,
    validate_profile,
)


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
    runner: str, module_loader: str, config_content: Dict, expected: bool
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


@pytest.mark.parametrize(
    "base, extension, expected",
    [
        pytest.param(
            {"a": 1, "b": 2}, {"c": 3}, {"a": 1, "b": 2, "c": 3}, id="add_new_key"
        ),
        pytest.param(
            {"a": 1, "b": 2},
            {"b": 3, "c": 4},
            {"a": 1, "b": 2, "c": 4},
            id="do_not_overwrite_existing_key",
        ),
        pytest.param(
            {"a": {"x": 1}, "b": 2},
            {"a": {"y": 2}},
            {"a": {"x": 1, "y": 2}, "b": 2},
            id="recursive_extend",
        ),
        pytest.param(
            {"a": {"x": 1}}, {"a": 2}, {"a": {"x": 1}}, id="extension_not_dict"
        ),
        pytest.param({}, {"a": 1}, {"a": 1}, id="empty_base"),
        pytest.param({"a": 1}, {}, {"a": 1}, id="empty_extension"),
        pytest.param({}, {}, {}, id="both_empty"),
    ],
)
def test_extend_profile(base, extension, expected):
    result = extend_profile(base, extension)
    assert result == expected


@pytest.mark.parametrize(
    "profile, expected",
    [
        pytest.param(
            {"RUNNER_TYPE": "LOCAL", "MODULE_LOADER_TYPE": "NO_MODULE"},
            True,
            id="valid_no_module_loader",
        ),
        pytest.param(
            {
                "RUNNER_TYPE": "SSH",
                "MODULE_LOADER_TYPE": "NO_MODULE",
                "SSH": {"HOST": "host", "USERNAME": "user"},
            },
            True,
            id="valid_ssh_runner",
        ),
        pytest.param(
            {
                "RUNNER_TYPE": "LOCAL",
                "MODULE_LOADER_TYPE": "CONDA",
                "MODULES": "foo",
            },
            True,
            id="valid_local_runner_with_module",
        ),
        pytest.param(
            {
                "RUNNER_TYPE": "SSH",
                "MODULE_LOADER_TYPE": "VENV",
                "MODULES": ["/venv/path"],
                "SSH": {"HOST": "host", "USERNAME": "user"},
            },
            True,
            id="valid_ssh_runner_with_module_list",
        ),
        pytest.param(
            {"MODULE_LOADER_TYPE": "NO_MODULE"}, False, id="missing_runner_type"
        ),
        pytest.param({"RUNNER_TYPE": "LOCAL"}, False, id="missing_module_loader_type"),
        pytest.param(
            {"RUNNER_TYPE": "LOCAL", "MODULE_LOADER_TYPE": "VENV"},
            False,
            id="missing_modules_for_module_loader",
        ),
        pytest.param(
            {"RUNNER_TYPE": "SSH", "MODULE_LOADER_TYPE": "NO_MODULE"},
            False,
            id="missing_ssh_config",
        ),
        pytest.param(
            {
                "RUNNER_TYPE": "SSH",
                "MODULE_LOADER_TYPE": "NO_MODULE",
                "SSH": {"USERNAME": "user"},
            },
            False,
            id="missing_host_in_ssh_config",
        ),
        pytest.param(
            {
                "RUNNER_TYPE": "SSH",
                "MODULE_LOADER_TYPE": "NO_MODULE",
                "SSH": {"HOST": "host"},
            },
            False,
            id="missing_username_in_ssh_config",
        ),
        pytest.param(
            {
                "RUNNER_TYPE": "SSH",
                "MODULE_LOADER_TYPE": "NO_MODULE",
                "SSH": {},
            },
            False,
            id="empty_ssh_config",
        ),
    ],
)
def test_validate_profile(profile, expected):
    assert validate_profile(profile) == expected
