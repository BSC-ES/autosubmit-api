from typing import Any, Dict, List, Union
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from autosubmit_api.config.config_file import read_config_file
from autosubmit_api.runners import module_loaders
from autosubmit_api.runners.module_loaders import ModuleLoaderType
from autosubmit_api.runners.runners import get_runner, RunnerType
from autosubmit_api.logger import logger

router = APIRouter()


def check_runner_permissions(runner: str, module_loader: str) -> bool:
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
            return False

        # Check if the module loader is enabled in the config file
        module_loader_config: Dict[str, Any] = runner_config.get(
            "MODULE_LOADERS", {}
        ).get(module_loader.upper(), {})
        is_module_loader_enabled: bool = module_loader_config.get("ENABLED", False)
        if not is_module_loader_enabled:
            return False
    except Exception:
        logger.error(
            f"Error checking permissions for runner {runner} and module loader {module_loader}"
        )
        return False

    return True


class GetRunnerBody(BaseModel):
    runner: RunnerType
    module_type: ModuleLoaderType
    module_names: Union[str, List[str], None] = None


@router.get("/experiments/{expid}/runner-detail", name="Get runner detail")
async def get_runner_detail(expid: str, body: GetRunnerBody):
    """
    Get the details of the runner for a given experiment ID.
    """
    # Check if the runner and module loader are enabled
    if not check_runner_permissions(body.runner.value, body.module_type.value):
        raise HTTPException(
            status_code=403,
            detail="Runner or module loader is not enabled in the config file",
        )

    module_loader = module_loaders.get_module_loader(
        body.module_type, body.module_names
    )
    runner = get_runner(body.runner, module_loader)

    try:
        version = await runner.version()
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to get version from runner",
        )

    return {
        "expid": expid,
        "runner": runner.runner_type,
        "module_type": module_loader.module_loader_type,
        "module_names": module_loader.module_names,
        "version": version,
    }


@router.post("/experiments/{expid}/run-experiment", name="Run experiment")
async def run_experiment(expid: str, body: GetRunnerBody):
    """
    Run an experiment with the specified ID and module.
    """
    # Check if the runner and module loader are enabled
    if not check_runner_permissions(body.runner.value, body.module_type.value):
        raise HTTPException(
            status_code=403,
            detail="Runner or module loader is not enabled in the config file",
        )

    module_loader = module_loaders.get_module_loader(
        body.module_type, body.module_names
    )
    runner = get_runner(body.runner, module_loader)

    return {
        "expid": expid,
        "runner": runner.runner_type,
        "module_type": module_loader.module_loader_type,
        "module_names": module_loader.module_names,
    }
