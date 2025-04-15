from abc import ABC, abstractmethod
import signal
import subprocess
import os
import psutil
import asyncio
from autosubmit_api.runners import module_loaders
from autosubmit_api.logger import logger


class Runner(ABC):
    @abstractmethod
    async def run(self, expid: str):
        """
        Run an Autosubmit experiment.

        :param expid: The experiment ID to run.
        """

    @abstractmethod
    async def stop(self, expid: str, force: bool = False):
        """
        Stop an Autosubmit experiment.

        :param expid: The experiment ID to stop.
        :param force: Whether to force stop the experiment.
        """

    @abstractmethod
    async def version(self):
        """
        Get the version of the Autosubmit module.

        :return: The version of the Autosubmit module.
        """


class LocalRunner(Runner):
    def __init__(self, module_loader: module_loaders.ModuleLoader):
        self.module_loader = module_loader

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

    async def run(self, expid: str):
        """
        Run an Autosubmit experiment using the local runner in a subprocess asynchronously.
        This method will use a module loader to prepare the environment and run the command.
        Once the subprocess is launched, the pid is catched and stored in the DB.
        Then, when the subprocess is finished, the status of the subprocess is updated in the DB
        and the output is logged.

        :param expid: The experiment ID to run.
        """
        autosubmit_command = f"autosubmit run -np {expid}"

        # Generate the command to run
        wrapped_command = self.module_loader.generate_command(autosubmit_command)
        logger.debug(f"Running command: {wrapped_command}")

        # Launch the command in a subprocess and get the pid
        process = subprocess.Popen(
            wrapped_command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            executable="/bin/bash",
        )

        # TODO: Store the pid in the DB

        # Return the pid of the process to the caller
        return process

    async def wait_run(self, process: subprocess.Popen):
        """
        Wait for the Autosubmit experiment to finish and get the output.
        This method will check the status of the process and update the status in the DB.
        :param process: The subprocess to wait for.
        """
        # Wait for the command to finish and get the output
        stdout, stderr = process.communicate()

        # TODO: Update the status of the subprocess in the DB

        if process.returncode != 0:
            logger.error(f"Command failed with error: {stderr}")
            raise subprocess.CalledProcessError(
                returncode=process.returncode,
                cmd=process.args,
                output=stdout,
                stderr=stderr,
            )
        logger.debug(f"Command output: {stdout}")
        return stdout

    async def get_run_status(self, expid: str):
        """
        Get the status of an Autosubmit experiment using the local runner in a subprocess asynchronously.
        This method will get the pid from the DB and check if the process is still running.
        It can return the status of the process (running, completed, failed, stopped).
        This method will also check if the process is still running and update the status in the DB.

        :param expid: The experiment ID to get the status of.
        :return: The status of the experiment.
        """
        # TODO: Get the pid & status from the DB
        pid = 12345  # Placeholder for the actual pid
        status = "PLACEHOLDER"  # Placeholder for the actual status

        # TODO
        pid
        status

    async def stop(self, expid: str, force: bool = False):
        """
        Stop an Autosubmit experiment using the local runner in a subprocess asynchronously.
        This method will get the pid from the DB and kill the process.

        :param expid: The experiment ID to stop.
        """
        # TODO: Get the pid from the DB
        pid = 12345  # Placeholder for the actual pid

        try:
            if force:
                # Force kill the process
                logger.debug(f"Force stopping process {pid} of experiment {expid}...")
                os.kill(pid, signal.SIGTERM)
            else:
                # Kill the process by using the ctrl+c signal
                logger.debug(
                    f"Stopping process {pid} of the experiment {expid} gracefully..."
                )
                os.kill(pid, signal.SIGINT)
            logger.debug(f"Process {pid} of experiment {expid} killed successfully.")

            # TODO: Update the status of the subprocess in the DB

        except OSError as e:
            logger.error(f"Failed to kill process {pid} of experiment {expid}: {e}")

    async def version(self):
        """
        Get the version of the Autosubmit module using the local runner in a subprocess asynchronously.

        :return: The version of the Autosubmit module.
        :raise subprocess.CalledProcessError: If the command fails.
        """
        autosubmit_command = "autosubmit -v"

        wrapped_command = self.module_loader.generate_command(autosubmit_command)
        logger.debug(f"Running command: {wrapped_command}")

        # Launch the command in a subprocess and get the output
        try:
            output = subprocess.check_output(
                wrapped_command, shell=True, text=True, executable="/bin/bash"
            )
        except subprocess.CalledProcessError as exc:
            logger.error(f"Command failed with error: {exc}")
            raise exc

        logger.debug(f"Command output: {output}")
        return output


if __name__ == "__main__":
    # redirect logger to stdout
    import logging

    logger.setLevel(logging.DEBUG)
    logger.addHandler(logging.StreamHandler())

    python_version = subprocess.check_output(
        ["python3", "--version"], text=True
    ).strip()
    logger.debug(f"Running Python version: {python_version}")

    expid = "a007"
    # module_loader = module_loaders.get_module_loader("conda", "autosubmit")
    module_loader = module_loaders.get_module_loader("venv", "~/venvs/autosubmit4.1.10")
    local_runner = LocalRunner(module_loader)
    # Run the local runner
    # using asyncio to run the asynchronous method
    asyncio.run(local_runner.version())

    python_version = subprocess.check_output(
        ["python3", "--version"], text=True
    ).strip()
    logger.debug(f"Running Python version: {python_version}")
