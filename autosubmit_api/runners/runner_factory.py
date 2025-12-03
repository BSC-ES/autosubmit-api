import json

from autosubmit_api.repositories.runner_processes import (
    create_runner_processes_repository,
)
from autosubmit_api.runners import module_loaders
from autosubmit_api.runners.base import Runner, RunnerType
from autosubmit_api.runners.local_runner import LocalRunner
from autosubmit_api.runners.ssh_runner import SSHRunner


def get_runner(
    runner_type: RunnerType, module_loader: module_loaders, *args, **kwargs
) -> Runner:
    """
    Get the runner for the specified runner type and module loader.

    :param runner_type: The type of the runner to get.
    :param module_loader: The module loader to use.
    :return: The runner for the specified type and module loader.
    """
    if runner_type.upper() == RunnerType.LOCAL:
        return LocalRunner(module_loader)
    elif runner_type.upper() == RunnerType.SSH:
        ssh_host = kwargs.get("ssh_host")
        ssh_user = kwargs.get("ssh_user")
        ssh_port = kwargs.get("ssh_port", 22)
        if not isinstance(ssh_port, int):
            ssh_port = 22

        return SSHRunner(module_loader, ssh_host=ssh_host, ssh_user=ssh_user, ssh_port=ssh_port)
    else:
        raise ValueError(f"Unknown runner type: {runner_type}")


def get_runner_from_expid(expid: str) -> Runner:
    """
    Get the runner from an expid based on the last runner process entry.
    This function retrieves the runner type and module loader from the database
    and returns the corresponding runner instance.

    :param expid: The experiment ID to get the runner for.
    :return: The runner for the specified expid.
    """
    runner_repo = create_runner_processes_repository()

    last_process = runner_repo.get_last_process_by_expid(expid)
    if not last_process:
        raise ValueError(f"No runner process found for expid: {expid}")

    runner_type = RunnerType(last_process.runner)
    module_loader = module_loaders.get_module_loader(
        last_process.module_loader, list(last_process.modules.split("\n"))
    )

    runner_extra_params = (
        json.loads(last_process.runner_extra_params)
        if last_process.runner_extra_params
        else {}
    )

    return get_runner(runner_type, module_loader, **runner_extra_params)
