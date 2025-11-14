import asyncio
import json
import re
from typing import Optional

import paramiko

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

STOP_WAIT_TIMEOUT = 10  # seconds


class SSHRunner(Runner):
    runner_type = RunnerType.SSH

    def __init__(
        self,
        module_loader: module_loaders.ModuleLoader,
        ssh_host: str,
        ssh_user: str = None,
        ssh_port: int = 22,
    ):
        if not ssh_host:
            raise ValueError("SSH host must be provided for SSHRunner.")

        self.module_loader = module_loader
        self.ssh_host = ssh_host
        self.ssh_user = ssh_user
        self.ssh_port = ssh_port
        self.runners_repo = create_runner_processes_repository()

        # Initialize Paramiko SSH client
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self._connect()

    def __del__(self):
        """
        Destructor to ensure SSH connection is closed when the object is destroyed.
        """
        self._close_connection()

    def __enter__(self):
        """
        Context manager entry.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit.
        """
        self._close_connection()
        return False

    def _connect(self):
        """
        Establish SSH connection to the remote host.
        """
        try:
            logger.debug(f"Connecting to SSH host {self.ssh_host}:{self.ssh_port}")
            self.ssh_client.connect(
                hostname=self.ssh_host,
                port=self.ssh_port,
                username=self.ssh_user,
                timeout=30,
            )
            logger.debug("SSH connection established successfully")
        except Exception as exc:
            logger.error(f"Failed to connect to SSH host {self.ssh_host}: {exc}")
            raise exc

    def _ensure_connection(self):
        """
        Ensure the SSH connection is active, reconnect if necessary.
        """
        if (
            not self.ssh_client.get_transport()
            or not self.ssh_client.get_transport().is_active()
        ):
            logger.warning("SSH connection is not active, reconnecting...")
            self._connect()

    def _close_connection(self):
        """
        Close the SSH connection.
        """
        if self.ssh_client:
            logger.debug("Closing SSH connection")
            self.ssh_client.close()

    def _prepare_command(self, command: str) -> str:
        """
        Prepare the command to run on the remote host with additional environment setup.
        """
        wrapped_command = self.module_loader.generate_command(command)

        if isinstance(self.module_loader, module_loaders.CondaModuleLoader):
            # Use interactive shell for Conda module loading
            return f'bash -ic "{wrapped_command}"'
        return wrapped_command

    def _execute_command(self, command: str) -> tuple[str, str, int]:
        """
        Execute a command on the remote host via SSH.

        :param command: The command to execute.
        :return: Tuple of (stdout, stderr, exit_code).
        """
        self._ensure_connection()

        logger.debug(f"Executing SSH command: {command}")

        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(command)
            exit_code = stdout.channel.recv_exit_status()

            stdout_text = stdout.read().decode("utf-8")
            stderr_text = stderr.read().decode("utf-8")

            logger.debug(f"Command exit code: {exit_code}")
            if stdout_text:
                logger.debug(f"Command stdout: {stdout_text[:500]}")
            if stderr_text:
                logger.debug(f"Command stderr: {stderr_text[:500]}")

            return stdout_text, stderr_text, exit_code
        except Exception as exc:
            logger.error(f"Failed to execute command: {exc}")
            raise exc

    async def version(self) -> str:
        """
        Get the version of the Autosubmit module using the SSH runner.
        """
        autosubmit_command = "autosubmit -v"
        prepared_command = self._prepare_command(autosubmit_command)

        try:
            stdout, stderr, exit_code = self._execute_command(prepared_command)

            if exit_code != 0:
                logger.error(f"Command failed with exit code {exit_code}: {stderr}")
                raise RuntimeError(f"Command failed: {stderr}")

            return stdout.strip()
        except Exception as exc:
            logger.error(f"Failed to get version: {exc}")
            raise exc

    def _is_pid_running(self, pid: int) -> bool:
        """
        Check if a remote process with the given PID is running.

        :param pid: The PID of the remote process to check.
        :return: True if the process is running, False otherwise.
        """
        try:
            check_command = f"ps -p {pid} -o pid="
            stdout, stderr, exit_code = self._execute_command(check_command)

            # If the command succeeds and returns the PID, the process is running
            return exit_code == 0 and stdout.strip() != ""
        except Exception as exc:
            logger.error(f"Error checking remote process {pid}: {exc}")
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
        runner_status = self.get_runner_status(expid)
        if runner_status == RunnerProcessStatus.ACTIVE.value:
            logger.error(f"Experiment {expid} is already running.")
            raise RunnerAlreadyRunningError(expid)

        autosubmit_command = f"autosubmit run {expid}"
        if (
            self.module_loader.module_loader_type
            == module_loaders.ModuleLoaderType.LMOD
        ):
            prepared_command = self._prepare_command("nohup " + autosubmit_command)
        else:
            prepared_command = "nohup " + self._prepare_command(autosubmit_command)

        # Execute the command asynchronously and get a channel to track PID
        self._ensure_connection()

        # Get the remote PID by running the command in background and capturing its PID
        # We'll use a wrapper script approach to get the PID
        pid_command = (
            f"{prepared_command} > /dev/null 2>&1 & pid=$!; "
            f"(wait $pid; echo $? > /tmp/autosubmit_$pid.exit_code) & echo $pid"
        )

        logger.error(f"Running SSH command: {pid_command}")

        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(pid_command)
            # Read the PID from stdout
            pid_output = stdout.read().decode("utf-8").strip()
            # The last line should be the PID
            lines = pid_output.split("\n")
            remote_pid = int(lines[-1])

            logger.debug(f"Remote process started with PID: {remote_pid}")
        except Exception as exc:
            logger.error(f"Failed to start remote process: {exc}")
            raise exc

        # Store the pid in the DB
        runner_extra_params = {
            "ssh_host": self.ssh_host,
            "ssh_user": self.ssh_user if self.ssh_user else None,
        }
        runner_proc = self.runners_repo.insert_process(
            expid=expid,
            pid=remote_pid,
            status=RunnerProcessStatus.ACTIVE.value,
            runner=self.runner_type.value,
            module_loader=self.module_loader.module_loader_type.value,
            modules="\n".join(self.module_loader.modules),
            runner_extra_params=json.dumps(runner_extra_params),
        )

        # Run the wait_run on the background
        task = asyncio.create_task(self.wait_run(runner_proc.id, remote_pid, expid))
        # Add the task to the background task set to prevent garbage collection
        background_task.add(task)
        task.add_done_callback(background_task.discard)

        # Return the runner data
        return runner_proc

    async def wait_run(self, runner_process_id: int, remote_pid: int, expid: str):
        """
        Wait for the Autosubmit experiment to finish by polling the remote process status.
        This method will check the status of the process and update the status in the DB.
        :param runner_process_id: The ID of the runner process in the DB.
        :param remote_pid: The PID of the remote process.
        :param expid: The experiment ID.
        """
        try:
            # Poll the remote process status
            while True:
                await asyncio.sleep(5)  # Poll every 5 seconds

                try:
                    is_running = self._is_pid_running(remote_pid)
                    if not is_running:
                        break
                except Exception as exc:
                    logger.error(f"Error checking remote process {remote_pid}: {exc}")
                    break

            # Get the exit status of the completed process
            success = False
            try:
                exit_code_file = f"/tmp/autosubmit_{remote_pid}.exit_code"
                cat_command = f"cat {exit_code_file}"
                stdout, stderr, exit_code = self._execute_command(cat_command)
                if exit_code == 0:
                    exit_status_str = stdout.strip()
                    exit_status = int(exit_status_str)
                    success = exit_status == 0
                    logger.debug(
                        f"Remote process {remote_pid} exited with code {exit_status}"
                    )
                else:
                    logger.error(
                        f"Failed to get exit code for remote process {remote_pid}: {stderr}"
                    )
            except Exception as exc:
                logger.error(
                    f"Error retrieving exit code for remote process {remote_pid}: {exc}"
                )

            # Update the status of the subprocess in the DB
            self.runners_repo.update_process_status(
                id=runner_process_id,
                status=RunnerProcessStatus.COMPLETED.value
                if success
                else RunnerProcessStatus.TERMINATED.value,
            )

            if not success:
                logger.error(
                    "Command failed with error. Check the logs for more details."
                )
            else:
                logger.debug(
                    f"Runner {runner_process_id} with remote pid {remote_pid} completed successfully."
                )
        except Exception as exc:
            logger.error(
                f"Error while waiting runner {runner_process_id} for remote process {remote_pid}: {exc}"
            )
            # Update status to terminated on error
            self.runners_repo.update_process_status(
                id=runner_process_id,
                status=RunnerProcessStatus.TERMINATED.value,
            )
            raise exc

    async def stop(self, expid: str, force: bool = False):
        """
        Stop the remote Autosubmit experiment by killing the process.
        """
        # Get the process from the DB
        active_procs = self.runners_repo.get_active_processes_by_expid(expid)
        if not active_procs:
            logger.error(f"Experiment {expid} is not running.")
            raise RuntimeError(f"Experiment {expid} is not running.")

        # Generate the command to stop the experiment
        flags = "--force" if force else ""
        autosubmit_command = f"autosubmit stop {flags} {expid}"

        # Prepare command with echo y piped for confirmation
        prepared_command = self._prepare_command(autosubmit_command)
        full_command = f"echo y | {prepared_command}"

        # Run the command to stop the experiment
        logger.debug(f"Stopping experiment {expid} with command: {full_command}")
        try:
            stdout, stderr, exit_code = self._execute_command(full_command)
            logger.debug(f"Stop stdout: {stdout}")
            logger.debug(f"Stop stderr: {stderr}")

            # Wait for the process to stop by polling
            pid = active_procs[0].pid
            max_wait_time = STOP_WAIT_TIMEOUT
            waited = 0
            poll_interval = 2  # seconds

            while waited < max_wait_time:
                try:
                    is_running = self._is_pid_running(pid)
                    if not is_running:
                        # Process stopped
                        break
                except Exception:
                    # Error checking means process likely stopped
                    break

                await asyncio.sleep(poll_interval)
                waited += poll_interval

            if waited >= max_wait_time:
                logger.warning(f"Timeout waiting for experiment {expid} to stop")

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
        prepared_command = self._prepare_command(autosubmit_command)

        try:
            logger.debug(f"Running create job list command: {prepared_command}")
            stdout, stderr, exit_code = self._execute_command(prepared_command)

            if exit_code != 0:
                logger.error(f"Command failed with exit code {exit_code}: {stderr}")
                raise RuntimeError(f"Failed to create job list: {stderr}")

            logger.debug(f"Create job list output: {stdout}")
            return stdout
        except Exception as exc:
            logger.error(f"Command failed with error: {exc}")
            raise RuntimeError(f"Failed to create job list: {exc}")

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
        prepared_command = self._prepare_command(autosubmit_command)

        try:
            logger.debug(f"Running create experiment command: {prepared_command}")
            stdout, stderr, exit_code = self._execute_command(prepared_command)

            if exit_code != 0:
                logger.error(f"Command failed with exit code {exit_code}: {stderr}")
                raise RuntimeError(f"Failed to create experiment: {stderr}")

            logger.debug(f"Create experiment output: {stdout}")

            # Extract the experiment ID from the output
            match = re.search(r"Experiment (\w+) created", stdout)
            if not match:
                raise RuntimeError("Failed to extract experiment ID from output.")
            expid = match.group(1)
            logger.info(f"Experiment {expid} created successfully.")
            return expid
        except Exception as exc:
            logger.error(f"Command failed with error: {exc}")
            raise exc

    async def set_job_status(
        self,
        expid: str,
        job_names_list: list[str] = None,
        final_status: str = None,
        filter_chunks: str = None,
        filter_status: str = None,
        filter_type: str = None,
        filter_type_chunk: str = None,
        filter_type_chunk_split: str = None,
        check_wrapper: bool = False,
        update_version: bool = False,
    ):
        flags = ["-np", "-nt", "-s"]
        if job_names_list:
            job_names = " ".join(job_names_list)
            flags.append(f'--list="{job_names}"')
        if final_status:
            flags.append(f'--status_final="{final_status}"')
        if filter_chunks:
            flags.append(f'--filter_chunks="{filter_chunks}"')
        if filter_status:
            flags.append(f'--filter_status="{filter_status}"')
        if filter_type:
            flags.append(f'--filter_type="{filter_type}"')
        if filter_type_chunk:
            flags.append(f'--filter_type_chunk="{filter_type_chunk}"')
        if filter_type_chunk_split:
            flags.append(f'--filter_type_chunk_split="{filter_type_chunk_split}"')
        if check_wrapper:
            flags.append("--check_wrapper")
        if update_version:
            flags.append("--update_version")

        autosubmit_command = f"autosubmit setstatus {expid} {' '.join(flags)}"
        prepared_command = self._prepare_command(autosubmit_command)

        try:
            logger.debug(f"Running set job status command: {prepared_command}")
            stdout, stderr, exit_code = self._execute_command(prepared_command)

            if exit_code != 0:
                logger.error(f"Command failed with exit code {exit_code}: {stderr}")
                raise RuntimeError(f"Failed to set job status: {stderr}")

            logger.debug(f"Set job status output: {stdout}")
            return stdout
        except Exception as exc:
            logger.error(f"Command failed with error: {exc}")
            raise exc
