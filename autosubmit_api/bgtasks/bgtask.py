from abc import ABC, abstractmethod
from autosubmit_api.experiment import common_requests
from autosubmit_api.history.experiment_status_manager import ExperimentStatusManager
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.workers.business import populate_times, process_graph_drawings
from autosubmit_api.workers.populate_details.populate import DetailsProcessor

class BackgroundTask(ABC):

    @staticmethod
    @abstractmethod
    def run():
        raise NotImplementedError
    
    @property
    @abstractmethod
    def id(self) -> dict:
        raise NotImplementedError
    
    @property
    @abstractmethod
    def trigger_options(self) -> dict:
        raise NotImplementedError
    

class PopulateDetailsDB(BackgroundTask):
    id = "TASK_POPDET"
    trigger_options = {
        "trigger": "interval",
        "hours": 4
    }

    @staticmethod
    def run():
        APIBasicConfig.read()
        return DetailsProcessor(APIBasicConfig).process()
    

class PopulateQueueRuntimes(BackgroundTask):
    id = "TASK_POPQUE"
    trigger_options = {
        "trigger": "interval",
        "minutes": 3
    }

    @staticmethod
    def run():
        """ Process and updates queuing and running times. """
        populate_times.process_completed_times()
    

class PopulateRunningExperiments(BackgroundTask):
    id = "TASK_POPRUNEX"
    trigger_options = {
        "trigger": "interval",
        "minutes": 5
    }

    @staticmethod
    def run():
        """
        Updates STATUS of experiments.
        """
        ExperimentStatusManager().update_running_experiments()
    

class VerifyComplete(BackgroundTask):
    id = "TASK_VRFCMPT"
    trigger_options = {
        "trigger": "interval",
        "minutes": 10
    }

    @staticmethod
    def run():
        common_requests.verify_last_completed(1800) 
    

class PopulateGraph(BackgroundTask):
    id = "TASK_POPGRPH"
    trigger_options = {
        "trigger": "interval",
        "hours": 24
    }

    @staticmethod
    def run():
        """
        Process coordinates of nodes in a graph drawing and saves them.
        """
        process_graph_drawings.process_active_graphs()