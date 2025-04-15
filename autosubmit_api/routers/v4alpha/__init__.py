from typing import List, Union
from fastapi import APIRouter
from pydantic import BaseModel

from autosubmit_api.runners import module_loaders
from autosubmit_api.runners.module_loaders import ModuleLoaderType
from autosubmit_api.runners.runners import LocalRunner


router = APIRouter()


class RunExperimentBody(BaseModel):
    runner: ModuleLoaderType = None
    module_names: Union[str, List[str], None] = None


@router.post("/experiments/{expid}/run-experiment", name="Run experiment")
async def run_experiment(expid: str, body: RunExperimentBody):
    """
    Run an experiment with the specified ID and module.
    """
    module_loader = module_loaders.get_module_loader("venv", "~/venvs/autosubmit4.1.10")

    LocalRunner(module_loader)

    raise NotImplementedError("This is a stub for the run_experiment function.")