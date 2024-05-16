import os
import time
from typing import List

from autosubmit_api.bgtasks.bgtask import BackgroundTaskTemplate
from autosubmit_api.database.adapters import (
    ExperimentStatusDbAdapter,
    ExperimentDbAdapter,
    ExperimentJoinDbAdapter,
)
from autosubmit_api.database.models import ExperimentModel
from autosubmit_api.experiment.common_requests import _is_exp_running
from autosubmit_api.history.database_managers.database_models import RunningStatus
from autosubmit_api.persistance.experiment import ExperimentPaths


class StatusUpdater(BackgroundTaskTemplate):
    id = "TASK_STTSUPDTR"
    trigger_options = {"trigger": "interval", "minutes": 5}

    @classmethod
    def _clear_missing_experiments(cls):
        """
        Clears the experiments that are not in the experiments table
        """

        try:
            ExperimentJoinDbAdapter().drop_status_from_deleted_experiments()
        except Exception as exc:
            cls.logger.error(
                f"[{cls.id}] Error while clearing missing experiments status: {exc}"
            )

    @classmethod
    def _get_experiments(cls) -> List[ExperimentModel]:
        """
        Get the experiments list
        """
        query_result = ExperimentDbAdapter().get_all()
        return [ExperimentModel.model_validate(row._mapping) for row in query_result]

    @classmethod
    def _check_exp_running(cls, expid: str) -> bool:
        """
        Decide if the experiment is running
        """
        MAX_PKL_AGE = 600  # 10 minutes
        MAX_PKL_AGE_EXHAUSTIVE = 3600  # 1 hour

        is_running = False
        try:
            pkl_path = ExperimentPaths(expid).job_list_pkl
            pkl_age = int(time.time()) - int(os.stat(pkl_path).st_mtime)

            if pkl_age < MAX_PKL_AGE:  # First running check
                is_running = True
            elif pkl_age < MAX_PKL_AGE_EXHAUSTIVE:  # Exhaustive check
                _, _, _flag, _, _ = _is_exp_running(expid)  # Exhaustive validation
                if _flag:
                    is_running = True
        except Exception as exc:
            cls.logger.error(
                f"[{cls.id}] Error while checking experiment {expid}: {exc}"
            )

        return is_running

    @classmethod
    def _update_experiment_status(cls, experiment: ExperimentModel, is_running: bool):
        try:
            ExperimentStatusDbAdapter().upsert_status(
                experiment.id,
                experiment.name,
                RunningStatus.RUNNING if is_running else RunningStatus.NOT_RUNNING,
            )
        except Exception as exc:
            cls.logger.error(
                f"[{cls.id}] Error while doing database operations on experiment {experiment.name}: {exc}"
            )

    @classmethod
    def procedure(cls):
        """
        Updates STATUS of experiments.
        """
        cls._clear_missing_experiments()

        # Read experiments table
        exp_list = cls._get_experiments()

        # Read current status of all experiments
        current_status = ExperimentStatusDbAdapter().get_all_dict()

        # Check every experiment status & update
        for experiment in exp_list:
            is_running = cls._check_exp_running(experiment.name)
            new_status = (
                RunningStatus.RUNNING if is_running else RunningStatus.NOT_RUNNING
            )
            if current_status.get(experiment.name) != new_status:
                cls.logger.info(
                    f"[{cls.id}] Updating status of {experiment.name} to {new_status}"
                )
                cls._update_experiment_status(experiment, is_running)
