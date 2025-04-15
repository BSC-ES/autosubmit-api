from autosubmit_api.repositories.runner_processes import (
    create_runner_processes_repository,
)
from autosubmit_api.runners import module_loaders
from autosubmit_api.runners.local_runner import LocalRunner
from autosubmit_api.runners.base import Runner, RunnerType


def get_runner(
    runner_type: RunnerType, module_loader: module_loaders.ModuleLoader
) -> Runner:
    """
    Get the runner for the specified runner type and module loader.

    :param runner_type: The type of the runner to get.
    :param module_loader: The module loader to use.
    :return: The runner for the specified type and module loader.
    """
    if runner_type == RunnerType.LOCAL:
        return LocalRunner(module_loader)
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
    return get_runner(runner_type, module_loader)
