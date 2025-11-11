import asyncio
import asyncio.subprocess
import re
import subprocess
from typing import Optional

import psutil

from autosubmit_api.logger import logger
from autosubmit_api.repositories.runner_processes import (
    create_runner_processes_repository,
)
from autosubmit_api.runners import module_loaders
from autosubmit_api.runners.base import (
    Runner,
    RunnerAlreadyRunningError,
    RunnerProcessStatus,
    RunnerType,
)

# Garbage collection prevention: https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task
background_task = set()


class LocalRunner(Runner):
    runner_type = RunnerType.LOCAL

    def __init__(self, module_loader: module_loaders.ModuleLoader):
        self.module_loader = module_loader
        self.runners_repo = create_runner_processes_repository()

    async def version(self) -> str:
        """
        Get the version of the Autosubmit module using the local runner in a subprocess asynchronously.

        :return: The version of the Autosubmit module.
        :raise subprocess.CalledProcessError: If the command fails.
        """
        autosubmit_command = "autosubmit -v"

        wrapped_command = self.module_loader.generate_command(autosubmit_command)

        # Launch the command in a subprocess and get the output
        try:
            logger.debug(f"Running command: {wrapped_command}")
            output = subprocess.check_output(
                wrapped_command, shell=True, text=True, executable="/bin/bash"
            ).strip()
        except subprocess.CalledProcessError as exc:
            logger.error(f"Command failed with error: {exc}")
            raise exc

        logger.debug(f"Command output: {output}")
        return output

    def _is_pid_running(self, pid: int) -> bool:
        """
        Check if a process with the given PID is running.

        :param pid: The PID of the process to check.
        :return: True if the process is running, False otherwise.
        """
        try:
            process = psutil.Process(pid)
            return process.is_running()
        except Exception as exc:
            logger.error(f"Error checking process {pid}: {exc}")
            return False

    def get_runner_status(self, expid: str) -> str:
        """
        Get the status of the runner for a given expid.
        It will update the status in the DB if the process is not running anymore.

        :param expid: The experiment ID to get the status of.
        :return: The status of the experiment.
        """
        # Get active processes from the DB
        active_procs = self.runners_repo.get_active_processes_by_expid(expid)
        if not active_procs:
            return "NO_RUNNER"

        # Check if the process is still running
        pid = active_procs[0].pid
        is_pid_running = self._is_pid_running(pid)

        if not is_pid_running:
            # Update the status of the subprocess in the DB
            updated_proc = self.runners_repo.update_process_status(
                id=active_procs[0].id, status=RunnerProcessStatus.TERMINATED.value
            )
            return updated_proc.status
        else:
            return active_procs[0].status

    async def run(self, expid: str):
        """
        Run an Autosubmit experiment using the local runner in a subprocess asynchronously.
        This method will use a module loader to prepare the environment and run the command.
        Once the subprocess is launched, the pid is caught and stored in the DB.
        Then, when the subprocess is finished, the status of the subprocess is updated in the DB.

        :param expid: The experiment ID to run.
        """
        # Check if other runner with the same expid is active
        runner_status = self.get_runner_status(expid)
        if runner_status == RunnerProcessStatus.ACTIVE.value:
            logger.error(f"Experiment {expid} is already running.")
            raise RunnerAlreadyRunningError(expid)

        # Generate the command to run
        autosubmit_command = f"autosubmit run {expid}"
        wrapped_command = self.module_loader.generate_command(autosubmit_command)
        logger.debug(f"Running command: {wrapped_command}")

        # Launch the command in a subprocess and get the pid
        process: asyncio.subprocess.Process = await asyncio.create_subprocess_shell(
            wrapped_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            executable="/bin/bash",
        )

        # Store the pid in the DB
        runner_proc = self.runners_repo.insert_process(
            expid=expid,
            pid=process.pid,
            status=RunnerProcessStatus.ACTIVE.value,
            runner=self.runner_type.value,
            module_loader=self.module_loader.module_loader_type.value,
            modules="\n".join(self.module_loader.modules),
        )

        # Run the wait_run on the background
        task = asyncio.create_task(self.wait_run(runner_proc.id, process))
        # Add the task to the background task set to prevent garbage collection
        background_task.add(task)
        task.add_done_callback(background_task.discard)

        # Return the runner data
        return runner_proc

    async def wait_run(
        self, runner_process_id: int, process: asyncio.subprocess.Process
    ):
        """
        Wait for the Autosubmit experiment to finish and get the output.
        This method will check the status of the process and update the status in the DB.
        :param process: The subprocess to wait for.
        """
        try:
            # Wait for the command to finish and get the output
            stdout, stderr = await process.communicate()

            # Update the status of the subprocess in the DB
            self.runners_repo.update_process_status(
                id=runner_process_id,
                status=RunnerProcessStatus.COMPLETED.value
                if process.returncode == 0
                else RunnerProcessStatus.TERMINATED.value,
            )

            # Check if the command was successful
            if process.returncode != 0:
                logger.error(
                    "Command failed with error. Check the logs for more details."
                )
                raise RuntimeError("Command failed with error")
            logger.debug(
                f"Runner {runner_process_id} with pid {process.pid} completed successfully."
            )
            return stdout, stderr
        except Exception as exc:
            logger.error(
                f"Error while waiting runner {runner_process_id} for process {process.pid}: {exc}"
            )
            raise exc
        finally:
            await process.wait()

    async def stop(self, expid: str, force: bool = False):
        """
        Stop an Autosubmit experiment using the local runner in a subprocess asynchronously.
        This method will get the pid from the DB and kill the process.

        :param expid: The experiment ID to stop.
        """
        # Get the process from the DB
        active_procs = self.runners_repo.get_active_processes_by_expid(expid)
        if not active_procs:
            logger.error(f"Experiment {expid} is not running.")
            raise RuntimeError(f"Experiment {expid} is not running.")

        # Generate the command to stop the experiment
        flags = "--force" if force else ""
        autosubmit_command = f"echo y | autosubmit stop {flags} {expid}"

        wrapped_command = self.module_loader.generate_command(autosubmit_command)

        # Run the command to stop the experiment
        logger.debug(f"Stopping experiment {expid} with command: {wrapped_command}")
        try:
            result = subprocess.run(
                wrapped_command,
                shell=True,
                text=True,
                executable="/bin/bash",
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            logger.debug(f"Stop stdout: {result.stdout}")
            logger.debug(f"Stop stderr: {result.stderr}")
            
            # Command will return non-zero code because it will think process is zombie
            # However it only matters that the process is no longer running.
            pid = active_procs[0].pid
            process = psutil.Process(pid)
            process.wait(timeout=5)
        except Exception as exc:
            logger.error(f"Failed to stop experiment {expid}: {exc}")
            raise exc

        logger.debug(f"Experiment {expid} stopped successfully.")

        # Update the status of the subprocess in the DB
        # NOTE: The final status can be either "STOPPED" or "FAILED"
        # because of a race condition with the wait_run method.
        self.runners_repo.update_process_status(
            id=active_procs[0].id,
            status=RunnerProcessStatus.TERMINATED.value,
        )

    async def create_job_list(
        self,
        expid: str,
        check_wrapper: bool = False,
        update_version: bool = False,
        force: bool = False,
    ) -> str:
        """
        Create a job list for the given expid using `autosubmit create` command.
        This method will use a module loader to prepare the environment and run the command.

        :param expid: The experiment ID to create the job list for.
        :param check_wrapper: If True, the command will check the wrapper script. Default is False.
        :return: The output of the command.
        """
        flags = []
        if check_wrapper:
            flags.append("--check_wrapper")
        if update_version:
            flags.append("--update_version")
        if force:
            flags.append("--force")

        autosubmit_command = f"autosubmit create -np {' '.join(flags)} {expid}"
        wrapped_command = self.module_loader.generate_command(autosubmit_command)

        try:
            logger.debug(f"Running command: {wrapped_command}")
            output = subprocess.check_output(
                wrapped_command, shell=True, text=True, executable="/bin/bash"
            ).strip()
            logger.debug(f"Command output: {output}")
            return output
        except Exception as exc:
            logger.error(f"Command failed with error: {exc}")
            raise exc

    async def create_experiment(
        self,
        description: str,
        git_repo: Optional[str] = None,
        git_branch: Optional[str] = None,
        minimal: bool = False,
        config_path: Optional[str] = None,
        hpc: Optional[str] = None,
        use_local_minimal: bool = False,
        operational: bool = False,
        testcase: bool = False,
    ) -> str:
        flags = [f'--description="{description}"']
        if git_repo:
            flags.append(f'--git_repo="{git_repo}"')
        if git_branch:
            flags.append(f'--git_branch="{git_branch}"')
        if minimal:
            flags.append("--minimal_configuration")
        if config_path:
            flags.append(f'-conf="{config_path}"')
        if hpc:
            flags.append(f'--HPC="{hpc}"')
        if use_local_minimal:
            flags.append("--use_local_minimal")
        if operational:
            flags.append("--operational")
        if testcase:
            flags.append("--testcase")

        autosubmit_command = f"autosubmit expid {' '.join(flags)}"
        wrapped_command = self.module_loader.generate_command(autosubmit_command)

        try:
            logger.debug(f"Running command: {wrapped_command}")
            output = subprocess.check_output(
                wrapped_command, shell=True, text=True, executable="/bin/bash"
            ).strip()
            logger.debug(f"Command output: {output}")

            # Extract the experiment ID from the output
            match = re.search(r"Experiment (\w+) created", output)
            if not match:
                raise RuntimeError("Failed to extract experiment ID from output.")
            expid = match.group(1)
            logger.info(f"Experiment {expid} created successfully.")
            return expid
        except Exception as exc:
            logger.error(f"Command failed with error: {exc}")
            raise exc
