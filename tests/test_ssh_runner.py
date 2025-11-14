from unittest.mock import patch
import pytest

from autosubmit_api.runners.base import RunnerProcessStatus, RunnerType
from autosubmit_api.runners.module_loaders import (
    CondaModuleLoader,
    NoModuleLoader,
    VenvModuleLoader,
)
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
        mock_wait_run.return_value = True  # Don't wait for the run to finish

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


@pytest.mark.asyncio
@pytest.mark.ssh_runner
@pytest.mark.parametrize(
    "params, expected_flags",
    [
        (
            {
                "check_wrapper": True,
                "update_version": True,
                "final_status": "FAILED",
                "filter_type": "SIM",
            },
            [
                "--check_wrapper",
                "--update_version",
                '--status_final="FAILED"',
                '--filter_type="SIM"',
            ],
        ),
        (
            {
                "check_wrapper": False,
                "final_status": "WAITING",
                "job_names_list": [
                    "job1",
                    "job2",
                ],
            },
            ['--status_final="WAITING"', '--list="job1 job2"'],
        ),
    ],
)
async def test_set_job_status(
    fixture_mock_basic_config, params: dict, expected_flags: list
):
    module_loader = NoModuleLoader()
    runner = SSHRunner(
        module_loader, ssh_host="localhost", ssh_user="autosubmit_user", ssh_port=2222
    )

    TEST_EXPID = "test_expid"

    # Mock the command generation
    with patch(
        "autosubmit_api.runners.ssh_runner.SSHRunner._execute_command"
    ) as mock_exec_cmd:
        mock_exec_cmd.return_value = ("", "", 0)

        # Call the method
        await runner.set_job_status(TEST_EXPID, **params)

        # Verify the command was called once
        mock_exec_cmd.assert_called_once()

        # Verify that the command contains the experiment ID
        command = mock_exec_cmd.call_args[0][0]
        assert "autosubmit setstatus" in command
        assert TEST_EXPID in command

        for flag in expected_flags:
            assert flag in command
