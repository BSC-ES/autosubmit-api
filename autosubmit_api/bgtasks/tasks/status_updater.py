import time
from typing import Dict, List

from autosubmit_api.bgtasks.bgtask import BackgroundTaskTemplate
from autosubmit_api.experiment.common_requests import _is_exp_running
from autosubmit_api.history.database_managers.database_models import RunningStatus
from autosubmit_api.persistance.pkl_reader import PklReader
from autosubmit_api.repositories.experiment import (
    ExperimentModel,
    create_experiment_repository,
)
from autosubmit_api.repositories.experiment_status import (
    create_experiment_status_repository,
)
from autosubmit_api.repositories.join.experiment_join import (
    create_experiment_join_repository,
)


class StatusUpdater(BackgroundTaskTemplate):
    id = "TASK_STTSUPDTR"
    trigger_options = {"trigger": "interval", "minutes": 5}

    @classmethod
    def _clear_missing_experiments(cls):
        """
        Clears the experiments that are not in the experiments table
        """
        try:
            experiment_join_repo = create_experiment_join_repository()
            experiment_join_repo.drop_status_from_deleted_experiments()
        except Exception as exc:
            cls.logger.error(
                f"[{cls.id}] Error while clearing missing experiments status: {exc}"
            )

    @classmethod
    def _get_experiments(cls) -> List[ExperimentModel]:
        """
        Get the experiments list
        """
        experiment_repository = create_experiment_repository()
        return experiment_repository.get_all()

    @classmethod
    def _get_current_status(cls) -> Dict[str, str]:
        """
        Get the current status of the experiments
        """
        status_repository = create_experiment_status_repository()
        experiment_statuses = status_repository.get_all()
        return {row.name: row.status for row in experiment_statuses}

    @classmethod
    def _check_exp_running(cls, expid: str) -> bool:
        """
        Decide if the experiment is running
        """
        MAX_PKL_AGE = 600  # 10 minutes
        MAX_PKL_AGE_EXHAUSTIVE = 3600  # 1 hour

        is_running = False
        try:
            pkl_reader = PklReader(expid)
            pkl_age = int(time.time()) - pkl_reader.get_modified_time()

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
        status_repository = create_experiment_status_repository()
        try:
            status_repository.upsert_status(
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
        current_status = cls._get_current_status()

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
