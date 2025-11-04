from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends

from autosubmit_api.auth import auth_token_dependency
from autosubmit_api.config.config_file import read_config_file
from autosubmit_api.runners.runner_config import parse_runners_config

router = APIRouter()


@router.get("/config", name="Get runners configuration")
def get_runners_config(
    user_id: Optional[str] = Depends(auth_token_dependency()),
) -> Dict[str, Any]:
    """
    Get the runners configuration.
    """
    config = parse_runners_config()
    return config


@router.get("/ssh-public-keys", name="Get SSH public keys")
def get_ssh_public_keys(
    user_id: Optional[str] = Depends(auth_token_dependency()),
) -> Dict[str, list[str]]:
    """
    Get the SSH public keys from the configuration file.
    """
    config = read_config_file()
    ssh_keys = config.get("SSH_PUBLIC_KEYS", [])

    return {
        "ssh_public_keys": ssh_keys,
    }
