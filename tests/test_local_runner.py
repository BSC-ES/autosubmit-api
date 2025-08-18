import subprocess
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from autosubmit_api.runners.local_runner import LocalRunner
from autosubmit_api.runners.module_loaders import NoModuleLoader


@pytest.mark.asyncio
async def test_get_version(fixture_mock_basic_config):
    module_loader = NoModuleLoader()
    runner = LocalRunner(module_loader)

    version = await runner.version()
    assert version is not None
    assert isinstance(version, str)

    autosubmit_version = subprocess.check_output(
        "autosubmit -v", shell=True, text=True
    ).strip()
    assert autosubmit_version == version


@pytest.mark.asyncio
async def test_run(fixture_mock_basic_config):
    module_loader = NoModuleLoader()
    runner = LocalRunner(module_loader)

    # Mock get_status
    runner.get_runner_status = lambda expid: "NO_FOUND"
    runner.wait_run = lambda runner_process_id, process: None

    # Mock the subprocess call
    with patch("autosubmit_api.runners.local_runner.asyncio") as mock_asyncio:
        mock_asyncio.create_subprocess_shell = AsyncMock()
        mock_process = MagicMock()
        mock_process.pid = 1234
        mock_asyncio.create_subprocess_shell.return_value = mock_process

        # Run the command
        TEST_EXPID = "test_expid"
        await runner.run(TEST_EXPID)

        # Check that the subprocess was called with the correct arguments
        mock_asyncio.create_subprocess_shell.assert_called_once()
        args = mock_asyncio.create_subprocess_shell.call_args[0]
        assert TEST_EXPID in args[0]


@pytest.mark.asyncio
async def test_wait_run(fixture_mock_basic_config):
    module_loader = NoModuleLoader()
    runner = LocalRunner(module_loader)

    # Mock the repository
    runner.runners_repo.update_process_status = lambda id, status: None

    # Mock the process
    mock_process = MagicMock()
    mock_process.pid = 1234
    mock_process.returncode = 0
    mock_process.communicate = AsyncMock(return_value=(b"output", b"error"))
    mock_process.wait = AsyncMock(return_value=0)

    # Call the method
    runner_process_id = 1
    await runner.wait_run(runner_process_id, mock_process)


@pytest.mark.asyncio
async def test_stop_experiment_not_running(fixture_mock_basic_config):
    module_loader = NoModuleLoader()
    runner = LocalRunner(module_loader)

    # Mock the repository to return no active processes
    runner.runners_repo.get_active_processes_by_expid = MagicMock(return_value=[])

    TEST_EXPID = "test_expid"

    with pytest.raises(RuntimeError, match=f"Experiment {TEST_EXPID} is not running."):
        await runner.stop(TEST_EXPID)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "force_stop",
    [
        pytest.param(True, id="force_stop_true"),
        pytest.param(False, id="force_stop_false"),
    ],
)
async def test_stop_experiment_success(fixture_mock_basic_config, force_stop: bool):
    module_loader = NoModuleLoader()
    runner = LocalRunner(module_loader)

    TEST_EXPID = "test_expid"
    TEST_PID = 1234

    # Mock the repository to return an active process
    mock_active_process = MagicMock()
    mock_active_process.pid = TEST_PID
    mock_active_process.id = 1
    runner.runners_repo.get_active_processes_by_expid = MagicMock(
        return_value=[mock_active_process]
    )

    # Mock the repository to update the process status
    mock_update_process_status = MagicMock()
    runner.runners_repo.update_process_status = mock_update_process_status

    # Mock psutil.Process and its methods
    mock_process = MagicMock()
    mock_process.children.return_value = []
    mock_process.name.return_value = "autosubmit"
    mock_process.kill = MagicMock()
    mock_process.terminate = MagicMock()
    mock_process.send_signal = MagicMock()
    mock_process.wait = MagicMock()

    with patch("subprocess.run") as mock_check_output, patch("psutil.Process") as mock_psutil:
        mock_psutil.return_value = mock_process
        await runner.stop(TEST_EXPID, force=force_stop)

        mock_check_output.assert_called_once()

        called_args = mock_check_output.call_args[0]
        assert "autosubmit stop" in called_args[0]
        assert TEST_EXPID in called_args[0]
        if force_stop:
            assert "--force" in called_args[0]

        # Verify the repository status update
        mock_update_process_status.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "params, expected_flags",
    [
        (
            {"check_wrapper": True, "update_version": True},
            ["--check-wrapper", "--update_version"],
        ),
        (
            {"check_wrapper": False, "force": True},
            ["--force"],
        ),
    ],
)
async def test_create_job_list(
    fixture_mock_basic_config, params: dict, expected_flags: list
):
    module_loader = NoModuleLoader()
    runner = LocalRunner(module_loader)

    TEST_EXPID = "test_expid"

    # Mock the command generation
    with patch(
        "autosubmit_api.runners.local_runner.subprocess.check_output"
    ) as mock_check_output:
        # Call the method
        await runner.create_job_list(TEST_EXPID, **params)

        # Verify the command was called once
        mock_check_output.assert_called_once()

        # Verify that the command contains the experiment ID
        command = mock_check_output.call_args[0][0]
        assert "autosubmit create" in command
        assert TEST_EXPID in command

        for flag in expected_flags:
            assert flag in command


@pytest.mark.asyncio
async def test_create_job_list_cmd_fail(fixture_mock_basic_config):
    module_loader = NoModuleLoader()
    runner = LocalRunner(module_loader)

    TEST_EXPID = "test_expid"

    # Mock the command generation
    with patch(
        "autosubmit_api.runners.local_runner.subprocess.check_output"
    ) as mock_check_output:
        mock_check_output.side_effect = subprocess.CalledProcessError(
            returncode=1, cmd="autosubmit create"
        )

        # Call the method and expect an exception
        with pytest.raises(subprocess.CalledProcessError):
            await runner.create_job_list(TEST_EXPID, check_wrapper=False)

        # Verify the command was called once
        mock_check_output.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "params, expected_flags",
    [
        (
            {"description": "Test Experiment"},
            ['--description="Test Experiment"'],
        ),
        (
            {
                "description": "Minimal experiment",
                "minimal": True,
                "git_repo": "https://example.com/repo.git",
                "git_branch": "foobar",
                "testcase": True,
                "config_path": "git_config",
            },
            [
                '--description="Minimal experiment"',
                "--minimal_configuration",
                '--git_repo="https://example.com/repo.git"',
                '--git_branch="foobar"',
                "--testcase",
                '-conf="git_config"',
            ],
        ),
        (
            {
                "description": "Operational experiment with HPC",
                "operational": True,
                "hpc": "LUMI",
                "use_local_minimal": True,
            },
            [
                '--description="Operational experiment with HPC"',
                "--operational",
                '--HPC="LUMI"',
                "--use_local_minimal",
            ],
        ),
    ],
)
async def test_create_experiment(
    fixture_mock_basic_config, params: dict, expected_flags: list[str]
):
    module_loader = NoModuleLoader()
    runner = LocalRunner(module_loader)

    TEST_EXPID = "test_expid"

    # Mock the command generation
    with patch(
        "autosubmit_api.runners.local_runner.subprocess.check_output"
    ) as mock_check_output:
        mock_check_output.return_value = f"Experiment {TEST_EXPID} created successfully"

        # Call the method
        expid = await runner.create_experiment(**params)

        assert expid == TEST_EXPID

        command = mock_check_output.call_args[0][0]

        assert "autosubmit expid" in command
        for flag in expected_flags:
            assert flag in command


@pytest.mark.asyncio
async def test_create_experiment_cmd_fail(fixture_mock_basic_config):
    module_loader = NoModuleLoader()
    runner = LocalRunner(module_loader)

    # Mock the command to raise an error
    with patch(
        "autosubmit_api.runners.local_runner.subprocess.check_output",
        side_effect=subprocess.CalledProcessError(1, "command", "error message"),
    ):
        with pytest.raises(subprocess.CalledProcessError):
            await runner.create_experiment(description="Test Experiment")


@pytest.mark.asyncio
async def test_create_experiment_autosubmit_fail(fixture_mock_basic_config):
    """
    Test when autosubmit doesn't return a valid experiment ID in the output.
    """

    module_loader = NoModuleLoader()
    runner = LocalRunner(module_loader)

    # Mock the command generation
    with patch(
        "autosubmit_api.runners.local_runner.subprocess.check_output"
    ) as mock_check_output:
        mock_check_output.return_value = (
            "[CRITICAL] Autosubmit failed to create experiment"
        )
        with pytest.raises(
            RuntimeError, match="Failed to extract experiment ID from output"
        ):
            await runner.create_experiment(description="Test Experiment")
