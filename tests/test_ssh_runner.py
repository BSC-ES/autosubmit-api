from unittest.mock import patch
import pytest

from autosubmit_api.runners.base import RunnerProcessStatus, RunnerType
from autosubmit_api.runners.module_loaders import CondaModuleLoader, VenvModuleLoader
from autosubmit_api.runners.runner_factory import get_runner
from autosubmit_api.runners.ssh_runner import SSHRunner


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
    runner: SSHRunner = get_runner(
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

    # Create a job list for the experiment
    await runner.create_job_list(expid=expid)

    # Run the experiment
    with patch("autosubmit_api.runners.ssh_runner.SSHRunner.wait_run") as mock_wait_run:
        mock_wait_run.return_value = True # Don't wait for the run to finish

        runner_proc = await runner.run(expid=expid)
        assert runner_proc is not None
        assert runner_proc.expid == expid
        assert runner_proc.status == RunnerProcessStatus.ACTIVE.value

    # Check runner status
    status = runner.get_runner_status(expid=expid)
    assert status == RunnerProcessStatus.ACTIVE.value

    # Stop the experiment
    await runner.stop(expid=expid)

    # Check if the process is stopped
    status = runner.get_runner_status(expid=expid)
    assert status != RunnerProcessStatus.ACTIVE.value
