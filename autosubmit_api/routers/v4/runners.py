from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from autosubmit_api.auth import auth_token_dependency
from autosubmit_api.config.config_file import read_config_file
from autosubmit_api.logger import logger
from autosubmit_api.runners.module_loaders import get_module_loader
from autosubmit_api.runners.runner_config import (
    get_runner_extra_params,
    process_profile,
)
from autosubmit_api.runners.runner_factory import get_runner

router = APIRouter()


@router.get("/configuration/ssh-public-keys", name="Get SSH public keys of the API")
def get_ssh_public_keys(
    user_id: Optional[str] = Depends(auth_token_dependency()),
) -> List[str]:
    """
    Get the SSH public keys from the configuration file.
    """
    config = read_config_file()
    ssh_keys = config.get("RUNNER_CONFIGURATION", {}).get("SSH_PUBLIC_KEYS", [])

    if not isinstance(ssh_keys, list):
        ssh_keys = []

    return ssh_keys


@router.get("/configuration/profiles", name="Get runner configuration profiles")
def get_runner_configuration_profiles(
    user_id: Optional[str] = Depends(auth_token_dependency()),
) -> Dict[str, Any]:
    """
    Get the runner configuration profiles from the configuration file.
    """
    config = read_config_file()
    profiles = config.get("RUNNER_CONFIGURATION", {}).get("PROFILES", {})

    return profiles


class RunnerEndpointBody(BaseModel):
    profile_name: str
    profile_params: Optional[Dict[str, Any]] = None
    command_params: Optional[Dict[str, Any]] = None


class SetJobStatusCmdParams(BaseModel):
    job_names_list: Optional[list[str]] = None
    final_status: Optional[str] = None
    filter_chunks: Optional[str] = None
    filter_status: Optional[str] = None
    filter_type: Optional[str] = None
    filter_type_chunk: Optional[str] = None
    filter_type_chunk_split: Optional[str] = None
    check_wrapper: bool = False
    update_version: bool = False


class SetJobStatusBody(RunnerEndpointBody):
    expid: str
    command_params: SetJobStatusCmdParams


@router.post("/command/set-job-status", name="Set job status for an experiment")
async def set_job_status(
    body: SetJobStatusBody,
    user_id: Optional[str] = Depends(auth_token_dependency()),
) -> Dict[str, Any]:
    """
    Set the job status for an experiment using the specified runner profile.
    """
    expid = body.expid
    command_params = body.command_params

    try:
        profile = process_profile(body.profile_name, body.profile_params)
        logger.debug(f"Processing profile: {body.profile_name}. Profile data: {profile}")

        runner_type, module_loader_type, modules = (
            profile.get("RUNNER_TYPE"),
            profile.get("MODULE_LOADER_TYPE"),
            profile.get("MODULES"),
        )

        runner_extra_params = get_runner_extra_params(profile)

        module_loader = get_module_loader(module_loader_type, modules)
        runner = get_runner(runner_type, module_loader, **runner_extra_params)
        await runner.set_job_status(
            expid,
            **command_params.__dict__,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to set job status for experiment {expid}: {exc}",
        )

    return {
        "message": f"Job status for experiment {expid} set successfully.",
    }
