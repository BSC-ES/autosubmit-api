import pytest

from autosubmit_api.runners.base import RunnerType
from autosubmit_api.runners.module_loaders import CondaModuleLoader, VenvModuleLoader
from autosubmit_api.runners.runner_factory import get_runner


@pytest.mark.asyncio
@pytest.mark.ssh_runner
@pytest.mark.parametrize(
    "module_loader",
    [
        CondaModuleLoader(env_name="autosubmit_env"),
        VenvModuleLoader(venv_path="/home/autosubmit_user/autosubmit_venv"),
    ],
)
async def test_ssh_runner_version(fixture_mock_basic_config, module_loader):
    runner = get_runner(
        runner_type=RunnerType.SSH,
        module_loader=module_loader,
        ssh_host="localhost",
        ssh_user="autosubmit_user",
        ssh_port=2222,
    )

    version = await runner.version()

    assert version == "4.1.14"


@pytest.mark.asyncio
@pytest.mark.ssh_runner
@pytest.mark.parametrize(
    "module_loader",
    [
        CondaModuleLoader(env_name="autosubmit_env"),
        VenvModuleLoader(venv_path="/home/autosubmit_user/autosubmit_venv"),
    ],
)
async def test_ssh_runner_full_run(fixture_mock_basic_config, module_loader):
    runner = get_runner(
        runner_type=RunnerType.SSH,
        module_loader=module_loader,
        ssh_host="localhost",
        ssh_user="autosubmit_user",
        ssh_port=2222,
    )

    # Create a new experiment
    expid = await runner.create_experiment(
        description="Test experiment",
    )

    await runner.create_job_list(expid=expid)
