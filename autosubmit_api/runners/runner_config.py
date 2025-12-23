from typing import Any, Dict, List, Optional, Union

from autosubmit_api.config.config_file import read_config_file
from autosubmit_api.logger import logger
from autosubmit_api.runners.module_loaders import ModuleLoaderType


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


def extend_profile(base: Dict[str, Any], extension: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extend a base profile dictionary with another dictionary, without overwriting existing keys.
    This operation is recursive for nested dictionaries.
    """
    result = base.copy()
    if extension:
        for key, value in extension.items():
            if key not in result:
                result[key] = value
            elif isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = extend_profile(result[key], value)
                # Recursion is ok here since the depth of the profile dictionaries should be small
    return result


def validate_profile(profile: Dict[str, Any]) -> bool:
    """
    Validate that the profile has all required fields set.
    """
    required_fields = ["RUNNER_TYPE", "MODULE_LOADER_TYPE"]
    for field in required_fields:
        if field not in profile:
            return False

    # If the module loader is not NO_MODULE, check for MODULES
    if profile["MODULE_LOADER_TYPE"] != "NO_MODULE":
        if "MODULES" not in profile:
            return False

    # SSH runner requires SSH configuration
    if profile["RUNNER_TYPE"] == "SSH":
        ssh_config = profile.get("SSH")
        if not ssh_config:
            return False
        ssh_required_fields = ["HOST", "USERNAME"]
        for field in ssh_required_fields:
            if field not in ssh_config:
                return False
    return True


def process_profile(
    profile_name: str,
    profile_params: Optional[Dict[str, Any]] = None,
    validate: bool = True,
) -> Dict[str, Any]:
    """
    Process a runner configuration profile by name, extending it with provided parameters.
    """
    # Get the profile from the configuration file
    config = read_config_file()
    profiles = config.get("RUNNER_CONFIGURATION", {}).get("PROFILES", {})
    base_profile = profiles.get(profile_name)
    if base_profile is None:
        raise ValueError("Invalid profile name")

    # Extend the base profile with the provided parameters
    profile = extend_profile(base_profile, profile_params or {})

    # Validate that the profile has all required fields set
    if validate and not validate_profile(profile):
        raise ValueError("Profile is missing required fields")

    return profile


def get_runner_extra_params(profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract runner extra parameters from the profile.
    """
    runner_extra_params = {}
    if profile["RUNNER_TYPE"] == "SSH":
        ssh_config = profile.get("SSH", {})
        runner_extra_params["ssh_host"] = ssh_config.get("HOST")
        runner_extra_params["ssh_user"] = ssh_config.get("USERNAME")
        runner_extra_params["ssh_port"] = ssh_config.get("PORT", 22)

    return runner_extra_params
