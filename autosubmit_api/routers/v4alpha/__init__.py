from typing import Annotated, Any, Dict, List, Optional, Union

from fastapi import APIRouter, Body, HTTPException, Query
from pydantic import BaseModel

from autosubmit_api.config.config_file import read_config_file
from autosubmit_api.logger import logger
from autosubmit_api.repositories.runner_processes import (
    create_runner_processes_repository,
)
from autosubmit_api.runners import module_loaders
from autosubmit_api.runners.base import RunnerAlreadyRunningError, RunnerType
from autosubmit_api.runners.module_loaders import ModuleLoaderType
from autosubmit_api.runners.runner_factory import get_runner, get_runner_from_expid

router = APIRouter()


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


class GetRunnerExtraParamsBody(BaseModel):
    ssh_host: Optional[str] = None
    ssh_user: Optional[str] = None
    ssh_port: Optional[int] = 22


class GetRunnerBody(BaseModel):
    runner: RunnerType
    module_loader: ModuleLoaderType
    modules: Union[str, List[str], None] = None
    runner_extra_params: Optional[GetRunnerExtraParamsBody] = None


@router.get("/runner-detail", name="Get runner detail")
async def get_runner_detail(
    query_params: Annotated[GetRunnerBody, Query()],
    body: Annotated[GetRunnerExtraParamsBody, Body()] = None,
):
    """
    Get the details of the runner for a given experiment ID.
    """
    # Check if the runner and module loader are enabled
    if not check_runner_permissions(
        query_params.runner.value,
        query_params.module_loader.value,
        query_params.modules,
    ):
        raise HTTPException(
            status_code=403,
            detail="Runner or module loader is not enabled in the config file",
        )

    module_loader = module_loaders.get_module_loader(
        query_params.module_loader, query_params.modules
    )
    runner_extra_params = body.model_dump() if body else {}
    logger.debug(f"Extra runner params: {runner_extra_params}")
    runner = get_runner(query_params.runner, module_loader, **runner_extra_params)

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
    if not check_runner_permissions(
        body.runner.value,
        body.module_loader.value,
        body.modules,
    ):
        raise HTTPException(
            status_code=403,
            detail="Runner or module loader is not enabled in the config file",
        )

    module_loader = module_loaders.get_module_loader(body.module_loader, body.modules)
    runner_extra_params = (
        body.runner_extra_params.model_dump() if body.runner_extra_params else {}
    )
    runner = get_runner(body.runner, module_loader, **runner_extra_params)

    try:
        runner_data = await runner.run(expid)
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
        "pid": runner_data.pid,
    }


@router.post("/experiments/{expid}/stop-experiment", name="Stop experiment")
async def stop_experiment(expid: str):
    """
    Stop an experiment with the specified ID and module.
    """
    try:
        runner = get_runner_from_expid(expid)
        await runner.stop(expid)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop experiment {expid}: {exc}",
        )

    return {"message": f"Experiment {expid} stopped successfully."}


@router.get(
    "/experiments/{expid}/get-runner-status", name="Get experiment's runner status"
)
async def get_experiment_runner_status(expid: str):
    """
    Get the status of the runner for a given experiment ID.
    """
    try:
        runner_repo = create_runner_processes_repository()

        last_process = runner_repo.get_last_process_by_expid(expid)
        if not last_process:
            raise ValueError(f"No runner process found for expid: {expid}")
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get status for experiment {expid}: {exc}",
        )

    return {
        "expid": expid,
        "runner_id": last_process.id,
        "runner": last_process.runner,
        "module_loader": last_process.module_loader,
        "modules": last_process.modules,
        "status": last_process.status,
        "pid": last_process.pid,
        "created": last_process.created,
        "modified": last_process.modified,
    }


class CreateJobListBody(GetRunnerBody):
    check_wrapper: Optional[bool] = None
    update_version: Optional[bool] = None
    force: Optional[bool] = None


@router.post("/experiments/{expid}/create-job-list", name="Create job list")
async def create_job_list(expid: str, body: CreateJobListBody):
    """
    Create a job list for the given experiment ID using the specified runner and module loader.
    """
    # Check if the runner and module loader are enabled
    if not check_runner_permissions(
        body.runner.value,
        body.module_loader.value,
        body.modules,
    ):
        raise HTTPException(
            status_code=403,
            detail="Runner or module loader is not enabled in the config file",
        )

    try:
        module_loader = module_loaders.get_module_loader(
            body.module_loader, body.modules
        )
        runner_extra_params = (
            body.runner_extra_params.model_dump() if body.runner_extra_params else {}
        )
        runner = get_runner(body.runner, module_loader, **runner_extra_params)
        await runner.create_job_list(
            expid,
            check_wrapper=body.check_wrapper,
            update_version=body.update_version,
            force=body.force,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create job list for experiment {expid}: {exc}",
        )

    return {
        "message": f"Job list for experiment {expid} created successfully.",
    }


class CreateExperimentBody(GetRunnerBody):
    description: str
    git_repo: Optional[str] = None
    git_branch: Optional[str] = None
    minimal: bool = False
    config_path: Optional[str] = None
    hpc: Optional[str] = None
    use_local_minimal: bool = False
    operational: bool = False
    testcase: bool = False


@router.post("/runner-create-experiment", name="Create experiment")
async def create_experiment(body: CreateExperimentBody):
    """
    Create an Autosubmit experiment with the specified parameters.
    """
    # Check if the runner and module loader are enabled
    if not check_runner_permissions(
        body.runner.value,
        body.module_loader.value,
        body.modules,
    ):
        raise HTTPException(
            status_code=403,
            detail="Runner or module loader is not enabled in the config file",
        )

    try:
        module_loader = module_loaders.get_module_loader(
            body.module_loader, body.modules
        )
        runner_extra_params = (
            body.runner_extra_params.model_dump() if body.runner_extra_params else {}
        )
        runner = get_runner(body.runner, module_loader, **runner_extra_params)
        expid = await runner.create_experiment(
            description=body.description,
            git_repo=body.git_repo,
            git_branch=body.git_branch,
            minimal=body.minimal,
            config_path=body.config_path,
            hpc=body.hpc,
            use_local_minimal=body.use_local_minimal,
            operational=body.operational,
            testcase=body.testcase,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create experiment: {exc}",
        )

    return {
        "message": "Experiment created successfully.",
        "expid": expid,
        "runner": runner.runner_type,
        "module_loader": module_loader.module_loader_type,
        "modules": module_loader.modules,
    }


class SetJobStatusBody(GetRunnerBody):
    job_names_list: Optional[list[str]] = None
    final_status: Optional[str] = None
    filter_chunks: Optional[str] = None
    filter_status: Optional[str] = None
    filter_type: Optional[str] = None
    filter_type_chunk: Optional[str] = None
    filter_type_chunk_split: Optional[str] = None
    check_wrapper: bool = False
    update_version: bool = False


@router.post("/experiments/{expid}/set-job-status", name="Set job status")
async def set_job_status(expid: str, body: SetJobStatusBody):
    """
    Set the status of a job for the given experiment ID using the specified runner and module loader.
    """
    # Check if the runner and module loader are enabled
    if not check_runner_permissions(
        body.runner.value,
        body.module_loader.value,
        body.modules,
    ):
        raise HTTPException(
            status_code=403,
            detail="Runner or module loader is not enabled in the config file",
        )

    try:
        module_loader = module_loaders.get_module_loader(
            body.module_loader, body.modules
        )
        runner_extra_params = (
            body.runner_extra_params.model_dump() if body.runner_extra_params else {}
        )
        runner = get_runner(body.runner, module_loader, **runner_extra_params)
        await runner.set_job_status(
            expid,
            job_names_list=body.job_names_list,
            final_status=body.final_status,
            filter_chunks=body.filter_chunks,
            filter_status=body.filter_status,
            filter_type=body.filter_type,
            filter_type_chunk=body.filter_type_chunk,
            filter_type_chunk_split=body.filter_type_chunk_split,
            check_wrapper=body.check_wrapper,
            update_version=body.update_version,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to set job status for experiment {expid}: {exc}",
        )

    return {
        "message": f"Job status for experiment {expid} set successfully.",
    }
