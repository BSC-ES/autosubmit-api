import pytest
from unittest.mock import patch
from autosubmit_api.routers.v4alpha import check_runner_permissions
from autosubmit_api.runners.runner_factory import get_runner
from autosubmit_api.runners.local_runner import LocalRunner
from autosubmit_api.runners.base import RunnerType


def test_get_runner():
    runner = get_runner(RunnerType.LOCAL, None)
    assert isinstance(runner, LocalRunner)


@pytest.mark.parametrize(
    "runner, module_loader, config_content, modules, expected",
    [
        pytest.param(
            "runner1",
            "module_loader1",
            {"RUNNERS": {"RUNNER1": {"ENABLED": True}}},
            None,
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
            None,
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
            None,
            False,
            id="runner_enabled_module_loader_disabled",
        ),
        pytest.param(
            "runner1",
            "venv",
            {
                "RUNNERS": {
                    "RUNNER1": {
                        "ENABLED": True,
                        "MODULE_LOADERS": {
                            "VENV": {
                                "ENABLED": True,
                                "SAFE_ROOT_PATH": "/safe/path",
                            }
                        },
                    }
                }
            },
            "/safe/path/module",
            True,
            id="venv_module_in_safe_path",
        ),
        pytest.param(
            "runner1",
            "venv",
            {
                "RUNNERS": {
                    "RUNNER1": {
                        "ENABLED": True,
                        "MODULE_LOADERS": {
                            "VENV": {
                                "ENABLED": True,
                                "SAFE_ROOT_PATH": "/safe/path",
                            }
                        },
                    }
                }
            },
            "/unsafe/path/module",
            False,
            id="venv_module_not_in_safe_path",
        ),
        pytest.param(
            "runner1",
            "venv",
            {
                "RUNNERS": {
                    "RUNNER1": {
                        "ENABLED": True,
                        "MODULE_LOADERS": {
                            "VENV": {
                                "ENABLED": True,
                                "SAFE_ROOT_PATH": "/safe/path",
                            }
                        },
                    }
                }
            },
            ["/safe/path/module1", "/safe/path/module2"],
            True,
            id="venv_multiple_modules_in_safe_path",
        ),
        pytest.param(
            "runner1",
            "venv",
            {
                "RUNNERS": {
                    "RUNNER1": {
                        "ENABLED": True,
                        "MODULE_LOADERS": {
                            "VENV": {
                                "ENABLED": True,
                                "SAFE_ROOT_PATH": "/safe/path",
                            }
                        },
                    }
                }
            },
            ["/safe/path/module1", "/unsafe/path/module2"],
            False,
            id="venv_multiple_modules_one_not_in_safe_path",
        ),
    ],
)
def test_check_runner_permissions(
    runner, module_loader, config_content, modules, expected
):
    with patch("autosubmit_api.routers.v4alpha.read_config_file") as mock_read_config:
        mock_read_config.return_value = config_content

        result = check_runner_permissions(runner, module_loader, modules)

        assert result == expected
