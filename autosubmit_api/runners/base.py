from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional

from autosubmit_api.repositories.runner_processes import RunnerProcessesDataModel

STOP_WAIT_TIMEOUT = 10  # seconds


class RunnerType(str, Enum):
    LOCAL = "LOCAL"
    SSH = "SSH"


class RunnerProcessStatus(str, Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    TERMINATED = "TERMINATED"


# Runner Exceptions
class RunnerAlreadyRunningError(Exception):
    """
    Exception raised when a runner is already running.
    """

    def __init__(self, expid: str):
        super().__init__(f"Runner for experiment {expid} is already running.")
        self.expid = expid


class Runner(ABC):
    """
    Base class for runners
    """

    @property
    @abstractmethod
    def runner_type(self) -> RunnerType:
        """
        The type of the runner.
        """

    @abstractmethod
    async def version(self) -> str:
        """
        Get the version of the Autosubmit module.

        :return: The version of the Autosubmit module.
        """

    @abstractmethod
    async def run(self, expid: str) -> RunnerProcessesDataModel:
        """
        Run an Autosubmit experiment.

        :param expid: The experiment ID to run.
        :raise RunnerAlreadyRunningError: If the runner is already running.
        """

    @abstractmethod
    async def stop(self, expid: str, force: bool = False):
        """
        Stop an Autosubmit experiment.

        :param expid: The experiment ID to stop.
        :param force: Whether to force stop the experiment.
        """

    @abstractmethod
    async def create_job_list(self, expid: str):
        """
        Create a job list for the given expid using `autosubmit create` command.

        :param expid: The expid of the experiment to create a job list for.
        """

    @abstractmethod
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
        copy: Optional[str] = None,
    ):
        """
        Create an Autosubmit experiment.
        """

    @abstractmethod
    async def set_job_status(
        self,
        expid: str,
        job_names_list: Optional[list[str]] = None,
        final_status: Optional[str] = None,
        filter_chunks: Optional[str] = None,
        filter_status: Optional[str] = None,
        filter_type: Optional[str] = None,
        filter_type_chunk: Optional[str] = None,
        filter_type_chunk_split: Optional[str] = None,
        check_wrapper: bool = False,
        update_version: bool = False,
    ):
        """
        Set the status of a job for a given experiment.

        :param expid: The experiment ID.
        :param job_names_list: List of job names to update.
        :param final_status: The target status to set for the jobs.
        :param filter_chunks: Filter jobs by chunk.
        :param filter_status: Filter jobs by their status.
        :param filter_type: Filter jobs by section.
        :param filter_type_chunk: Filter by section and chunk.
        :param filter_type_chunk_split: Filter by section, chunk, and split.
        :param check_wrapper: Whether to check the wrapper script.
        :param update_version: Whether to update the version.
        """
