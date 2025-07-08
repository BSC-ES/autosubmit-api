import asyncio
import asyncio.subprocess
import subprocess


from autosubmit_api.logger import logger
from autosubmit_api.repositories.runner_processes import (
    create_runner_processes_repository,
)
from autosubmit_api.runners import module_loaders
from autosubmit_api.runners.base import Runner, RunnerAlreadyRunningError, RunnerType

# Garbage collection prevention: https://docs.python.org/3/library/asyncio-task.html#asyncio.create_task
background_task = set()


class SSHRunner(Runner):
    runner_type = RunnerType.SSH

    def __init__(self, module_loader: module_loaders.ModuleLoader, ssh_host: str, ssh_user: str = None):
        self.module_loader = module_loader
        self.ssh_host = ssh_host
        self.ssh_user = ssh_user
        self.runners_repo = create_runner_processes_repository()

    def _ssh_prefix(self):
        user_host = f"{self.ssh_user}@{self.ssh_host}" if self.ssh_user else self.ssh_host
        return f"ssh {user_host}"

    async def version(self) -> str:
        """
        Get the version of the Autosubmit module using the SSH runner in a subprocess asynchronously.
        """
        autosubmit_command = "autosubmit -v"
        wrapped_command = self.module_loader.generate_command(autosubmit_command)
        ssh_command = f"{self._ssh_prefix()} '{wrapped_command}'"

        try:
            logger.debug(f"Running SSH command: {ssh_command}")
            output = subprocess.check_output(
                ssh_command, shell=True, text=True, executable="/bin/bash"
            ).strip()
        except subprocess.CalledProcessError as exc:
            logger.error(f"SSH command failed with error: {exc}")
            raise exc

        logger.debug(f"SSH command output: {output}")
        return output

    def _is_pid_running(self, pid: int) -> bool:
        """
        Check if a process with the given PID is running on the remote host.
        """
        check_cmd = f"{self._ssh_prefix()} 'ps -p {pid} -o pid='"
        try:
            output = subprocess.check_output(
                check_cmd, shell=True, text=True, executable="/bin/bash"
            ).strip()
            return bool(output)
        except subprocess.CalledProcessError:
            return False

    def get_runner_status(self, expid: str) -> str:
        active_procs = self.runners_repo.get_active_processes_by_expid(expid)
        if not active_procs:
            return "NO_RUNNER"

        pid = active_procs[0].pid
        is_pid_running = self._is_pid_running(pid)

        if not is_pid_running:
            updated_proc = self.runners_repo.update_process_status(
                id=active_procs[0].id, status="FAILED"
            )
            return updated_proc.status
        else:
            return active_procs[0].status

    async def run(self, expid: str):
        runner_status = self.get_runner_status(expid)
        if runner_status == "ACTIVE":
            logger.error(f"Experiment {expid} is already running.")
            raise RunnerAlreadyRunningError(expid)

        autosubmit_command = f"autosubmit run {expid}"
        wrapped_command = self.module_loader.generate_command(autosubmit_command)
        # Run in background and print the PID
        remote_cmd = f"nohup {wrapped_command} > /dev/null 2>&1 & echo $!"
        ssh_command = f"{self._ssh_prefix()} '{remote_cmd}'"
        logger.debug(f"Running SSH command: {ssh_command}")

        # Get the remote PID
        proc = await asyncio.create_subprocess_shell(
            ssh_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            executable="/bin/bash",
        )
        stdout, stderr = await proc.communicate()
        if proc.returncode != 0:
            logger.error(f"Failed to start remote process: {stderr.decode().strip()}")
            raise RuntimeError(f"Failed to start remote process: {stderr.decode().strip()}")

        try:
            pid = int(stdout.decode().strip())
        except Exception as exc:
            logger.error(f"Could not parse remote PID: {stdout.decode().strip()}")
            raise exc

        runner_proc = self.runners_repo.insert_process(
            expid=expid,
            pid=pid,
            status="ACTIVE",
            runner=self.runner_type.value,
            module_loader=self.module_loader.module_loader_type.value,
            modules="\n".join(self.module_loader.modules),
        )

        task = asyncio.create_task(self.wait_run(runner_proc.id, pid))
        background_task.add(task)
        task.add_done_callback(background_task.discard)
        return runner_proc

    async def wait_run(self, runner_process_id: int, pid: int):
        """
        Wait for the remote Autosubmit experiment to finish and update the status in the DB.
        """
        try:
            while True:
                await asyncio.sleep(5)
                if not self._is_pid_running(pid):
                    break

            # Optionally, fetch exit code or logs here if needed

            self.runners_repo.update_process_status(
                id=runner_process_id,
                status="COMPLETED",
            )
            logger.debug(
                f"Runner {runner_process_id} with remote pid {pid} completed successfully."
            )
        except Exception as exc:
            logger.error(
                f"Error while waiting runner {runner_process_id} for remote pid {pid}: {exc}"
            )
            self.runners_repo.update_process_status(
                id=runner_process_id,
                status="FAILED",
            )
            raise exc

    async def stop(self, expid: str, force: bool = False):
        active_procs = self.runners_repo.get_active_processes_by_expid(expid)
        if not active_procs:
            logger.error(f"Experiment {expid} is not running.")
            raise RuntimeError(f"Experiment {expid} is not running.")

        pid = active_procs[0].pid
        signal_cmd = "KILL" if force else "TERM"
        ssh_command = f"{self._ssh_prefix()} 'kill -s {signal_cmd} {pid}'"
        logger.debug(f"Stopping remote process with SSH command: {ssh_command}")

        proc = await asyncio.create_subprocess_shell(
            ssh_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            executable="/bin/bash",
        )
        await proc.communicate()

        self.runners_repo.update_process_status(
            id=active_procs[0].id,
            status="STOPPED",
        )
        logger.debug(f"Process {pid} of experiment {expid} killed successfully on remote host.")
