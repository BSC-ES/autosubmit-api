from autosubmit_api.runners import module_loaders
from autosubmit_api.runners.local_runner import LocalRunner
from autosubmit_api.runners.base import Runner, RunnerType


def get_runner(runner_type: RunnerType, module_loader: module_loaders.ModuleLoader) -> Runner:
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