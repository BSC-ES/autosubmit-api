from typing import List, Union
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from autosubmit_api.runners import module_loaders
from autosubmit_api.runners.module_loaders import ModuleLoaderType
from autosubmit_api.runners.runners import get_runner, RunnerType


router = APIRouter()


class GetRunnerBody(BaseModel):
    runner: RunnerType
    module_type: ModuleLoaderType
    module_names: Union[str, List[str], None] = None


@router.get("/experiments/{expid}/runner-detail", name="Get runner detail")
async def get_runner_detail(expid: str, body: GetRunnerBody):
    """
    Get the details of the runner for a given experiment ID.
    """
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
