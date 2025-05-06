from typing import Annotated, Any, Dict, List, Union
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from autosubmit_api.config.config_file import read_config_file
from autosubmit_api.runners import module_loaders
from autosubmit_api.runners.module_loaders import ModuleLoaderType
from autosubmit_api.runners.runners import RunnerAlreadyRunningError, get_runner, RunnerType
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
    module_loader: ModuleLoaderType
    modules: Union[str, List[str], None] = None


@router.get("/runner-detail", name="Get runner detail")
async def get_runner_detail(query_params: Annotated[GetRunnerBody, Query()]):
    """
    Get the details of the runner for a given experiment ID.
    """
    # Check if the runner and module loader are enabled
    if not check_runner_permissions(
        query_params.runner.value, query_params.module_loader.value
    ):
        raise HTTPException(
            status_code=403,
            detail="Runner or module loader is not enabled in the config file",
        )

    module_loader = module_loaders.get_module_loader(
        query_params.module_loader, query_params.modules
    )
    runner = get_runner(query_params.runner, module_loader)

    try:
        version = await runner.version()
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Failed to get version from runner",
        )

    return {
        "runner": runner.runner_type,
        "module_loader": module_loader.module_loader_type,
        "modules": module_loader.modules,
        "version": version,
    }


@router.post("/experiments/{expid}/run-experiment", name="Run experiment")
async def run_experiment(expid: str, body: GetRunnerBody):
    """
    Run an experiment with the specified ID and module.
    """
    # Check if the runner and module loader are enabled
    if not check_runner_permissions(body.runner.value, body.module_loader.value):
        raise HTTPException(
            status_code=403,
            detail="Runner or module loader is not enabled in the config file",
        )

    module_loader = module_loaders.get_module_loader(
        body.module_loader, body.modules
    )
    runner = get_runner(body.runner, module_loader)

    try:
        runner_data, process = await runner.run(expid)
    except RunnerAlreadyRunningError:
        raise HTTPException(
            status_code=400,
            detail=f"Runner for experiment {expid} is already running.",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to run experiment {expid}: {exc}",
        )

    return {
        "expid": expid,
        "runner": runner.runner_type,
        "module_loader": module_loader.module_loader_type,
        "modules": module_loader.modules,
        "runner_id": runner_data.id,
        "pid": process.pid,
    }
