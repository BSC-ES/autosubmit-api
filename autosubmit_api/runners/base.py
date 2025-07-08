from abc import ABC, abstractmethod
from enum import Enum

from autosubmit_api.repositories.runner_processes import RunnerProcessesDataModel


class RunnerType(str, Enum):
    LOCAL = "local"

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
    async def create_experiment(self):
        """
        Create an Autosubmit experiment.
        """
