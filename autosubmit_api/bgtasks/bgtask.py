from abc import ABC, abstractmethod
import traceback
from autosubmit_api.logger import logger
from autosubmit_api.experiment import common_requests
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.workers.business import populate_times, process_graph_drawings
from autosubmit_api.workers.populate_details.populate import DetailsProcessor


class BackgroundTaskTemplate(ABC):
    """
    Interface to define Background Tasks.
    Do not override the run method.
    """
    logger = logger

    @classmethod
    def run(cls):
        """
        Not blocking exceptions
        """
        try:
            cls.procedure()
        except Exception as exc:
            cls.logger.error(f"Exception on Background Task {cls.id}: {exc}")
            cls.logger.error(traceback.print_exc())

    @classmethod
    @abstractmethod
    def procedure(cls):
        raise NotImplementedError

    @property
    @abstractmethod
    def id(self) -> dict:
        raise NotImplementedError

    @property
    @abstractmethod
    def trigger_options(self) -> dict:
        raise NotImplementedError


class PopulateDetailsDB(BackgroundTaskTemplate):
    id = "TASK_POPDET"
    trigger_options = {"trigger": "interval", "hours": 4}

    @classmethod
    def procedure(cls):
        APIBasicConfig.read()
        return DetailsProcessor(APIBasicConfig).process()


class PopulateQueueRuntimes(BackgroundTaskTemplate):
    id = "TASK_POPQUE"
    trigger_options = {"trigger": "interval", "minutes": 3}

    @classmethod
    def procedure(cls):
        """Process and updates queuing and running times."""
        populate_times.process_completed_times()


class VerifyComplete(BackgroundTaskTemplate):
    id = "TASK_VRFCMPT"
    trigger_options = {"trigger": "interval", "minutes": 10}

    @classmethod
    def procedure(cls):
        common_requests.verify_last_completed(1800)


class PopulateGraph(BackgroundTaskTemplate):
    id = "TASK_POPGRPH"
    trigger_options = {"trigger": "interval", "hours": 24}

    @classmethod
    def procedure(cls):
        """
        Process coordinates of nodes in a graph drawing and saves them.
        """
        process_graph_drawings.process_active_graphs()
