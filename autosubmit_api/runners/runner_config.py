from typing import Any, Dict, List, Union

from autosubmit_api.config.config_file import read_config_file
from autosubmit_api.logger import logger
from autosubmit_api.runners.base import RunnerType
from autosubmit_api.runners.module_loaders import ModuleLoaderType


def parse_module_loader_config(
    raw_module_loader_config: dict[str, dict],
) -> dict[str, dict]:
    """
    Parses the module loader configuration data.

    :param raw_module_loader_config: A dictionary containing the raw module loader configuration.
    :return: A dictionary containing the parsed module loader configuration.
    """
    parsed_config: dict[str, dict] = {}
    for module_loader in ModuleLoaderType.__members__.values():
        module_loader_name = module_loader.value.upper()
        module_config = raw_module_loader_config.get(module_loader_name, {})
        parsed_config[module_loader_name] = {
            "ENABLED": module_config.get("ENABLED", False),
        }

        # Module specific settings
        if module_loader_name != ModuleLoaderType.NO_MODULE.value.upper():
            parsed_config[module_loader_name]["MODULES_WHITELIST"] = module_config.get(
                "MODULES_WHITELIST", []
            )
    return parsed_config


def parse_runners_config() -> dict[str, dict]:
    """
    Parses the runner configuration data.

    :return: A dictionary containing the parsed runner configuration.
    """
    config_data = read_config_file()
    raw_runners_config: dict[str, dict] = config_data.get("RUNNERS", {})

    # Parse the configuration for each runner
    parsed_config: dict[str, dict] = {}
    for runner in RunnerType.__members__.values():
        runner_name = runner.value.upper()
        raw_runner_config = raw_runners_config.get(runner_name, {})

        # Parse the module loaders configuration for the runner
        raw_module_loader_config = raw_runner_config.get("MODULE_LOADERS", {})
        parsed_mloader_config = parse_module_loader_config(raw_module_loader_config)

        # Store the parsed configuration for the runner
        parsed_config[runner_name] = {
            "ENABLED": raw_runner_config.get("ENABLED", False),
            "MODULE_LOADERS": parsed_mloader_config,
        }

    return parsed_config


def check_runner_permissions(
    runner: str, module_loader: str, modules: Union[str, List[str], None] = None
) -> bool:
    """
    Check if the runner and module loader are enabled in the configuration file.

    :param runner: The runner type to check.
    :param module_loader: The module loader type to check.
    """
    try:
        # Check if the runner is enabled in the config file
        runner_config: Dict[str, Any] = (
            read_config_file().get("RUNNERS", {}).get(runner.upper(), {})
        )
        is_runner_enabled: bool = runner_config.get("ENABLED", False)
        if not is_runner_enabled:
            raise ValueError(f"Runner {runner} is not enabled in the config file.")

        # Check if the module loader is enabled in the config file
        module_loader_config: Dict[str, Any] = runner_config.get(
            "MODULE_LOADERS", {}
        ).get(module_loader.upper(), {})
        is_module_loader_enabled: bool = module_loader_config.get("ENABLED", False)
        if not is_module_loader_enabled:
            raise ValueError(
                f"Module loader {module_loader} is not enabled in the config file."
            )

        # VENV: Check if the venv is in a safe root path
        if module_loader.lower() == ModuleLoaderType.VENV.value:
            venv_config: Dict[str, Any] = runner_config.get("MODULE_LOADERS", {}).get(
                ModuleLoaderType.VENV.value.upper(), {}
            )
            safe_root_path: str = venv_config.get("SAFE_ROOT_PATH", "/")

            if isinstance(modules, str):
                if not modules.startswith(safe_root_path):
                    raise ValueError(
                        f"Module {modules} is not in the safe root path {safe_root_path}"
                    )
            elif isinstance(modules, list):
                for module in modules:
                    if not module.startswith(safe_root_path):
                        raise ValueError(
                            f"Module {module} is not in the safe root path {safe_root_path}"
                        )
            else:
                raise ValueError(
                    f"Modules should be a string or a list of strings, got {type(modules)}"
                )

    except Exception as exc:
        logger.error(f"Runner configuration unauthorized or invalid: {exc}")
        return False

    return True
