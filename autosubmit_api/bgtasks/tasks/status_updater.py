import time
from typing import Dict, List, Optional

from autosubmit_api.bgtasks.bgtask import BackgroundTaskTemplate
from autosubmit_api.experiment.common_requests import _is_exp_running
from autosubmit_api.history.database_managers.database_models import RunningStatus
from autosubmit_api.repositories.experiment import (
    ExperimentModel,
    create_experiment_repository,
)
from autosubmit_api.repositories.experiment_status import (
    ExperimentStatusModel,
    create_experiment_status_repository,
)
from autosubmit_api.repositories.jobs import create_jobs_repository
from autosubmit_api.repositories.join.experiment_join import (
    create_experiment_join_repository,
)


class StatusUpdater(BackgroundTaskTemplate):
    id = "TASK_STTSUPDTR"
    trigger_options = {"trigger": "interval", "minutes": 1}

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
    def _get_current_status(cls) -> Dict[str, ExperimentStatusModel]:
        """
        Get the current status of the experiments.
        """
        status_repository = create_experiment_status_repository()
        experiment_statuses = status_repository.get_all()
        # Filter out terminal statuses
        terminal_statuses = [
            RunningStatus.ARCHIVED,
            RunningStatus.DELETED,
            RunningStatus.NOT_RUNNING,
        ]
        mutable_statuses = {
            row.name: row
            for row in experiment_statuses
            if row.status not in terminal_statuses
        }

        cls.logger.debug(
            f"[{cls.id}] Loaded {len(mutable_statuses)} mutable experiments "
            f"(filtered out {len(experiment_statuses) - len(mutable_statuses)} terminal statuses)"
        )

        return mutable_statuses

    @classmethod
    def _check_exp_running(cls, expid: str, status_row: Optional[ExperimentStatusModel] = None) -> bool:
        """
        Decide if the experiment is running using last_heartbeat as the main signal.

        Priority order:
        1. Check as_times.db last_heartbeat column (most reliable, updated by backend every 2 min)
        2. Check pickle file age (secondary, faster than filesystem exhaustive check)
        3. Check run.log file (last resort, most exhaustive and slow)
        """
        MAX_HEARTBEAT_AGE = 150 # 2.5 minutes
        MAX_PKL_AGE = 600  # 10 minutes
        MAX_PKL_AGE_EXHAUSTIVE = 3600  # 1 hour

        is_running = False

        try:
            current_time = int(time.time())
            # Priority 1: Check last_heartbeat timestamp from as_times.db
            if status_row and status_row.last_heartbeat:
                try:
                    from datetime import datetime as dt
                    heartbeat_dt = dt.fromisoformat(status_row.last_heartbeat)
                    heartbeat_timestamp = int(heartbeat_dt.timestamp())
                    heartbeat_age = current_time - heartbeat_timestamp

                    # Fresh heartbeat signal, experiment is still running
                    if heartbeat_age < MAX_HEARTBEAT_AGE:
                        is_running = True
                        return is_running
                except Exception as exc:
                    cls.logger.warning(
                        f"[{cls.id}] Could not parse heartbeat for {expid}: {exc}"
                    )
            else:
                try:
                    job_list_repo = create_jobs_repository(expid)
                    pkl_age = current_time - job_list_repo.get_last_modified_timestamp()

                    # Priority 2: Check pickle file age
                    if pkl_age < MAX_PKL_AGE:  # First running check
                        is_running = True
                        return is_running

                    # Priority 3: Exhaustive check using filesystem
                    elif pkl_age < MAX_PKL_AGE_EXHAUSTIVE:  # Exhaustive check
                        _, _, _flag, _, _ = _is_exp_running(expid)  # Exhaustive validation
                        if _flag:
                            is_running = True
                            return is_running

                except Exception as exc:
                    cls.logger.warning(
                        f"[{cls.id}] Could not check pickle file for {expid}: {exc}"
                    )

            cls.logger.debug(
                f"[{cls.id}] Experiment {expid} is not running: "
                f"heartbeat_age={heartbeat_age if status_row and status_row.last_heartbeat else 'N/A'}s, "
                f"pkl_age={pkl_age if 'pkl_age' in locals() else 'N/A'}s"
            )
        except Exception as exc:
            cls.logger.error(
                f"[{cls.id}] Error while checking if experiment {expid} is running: {exc}"
            )

        return is_running

    @classmethod
    def _update_experiment_status(cls, experiment: ExperimentStatusModel, is_running: bool, status_row: Optional[ExperimentStatusModel] = None):
        """
        Update experiment status using guarded conditional update.

        Guard against overwritting ARCHIVED/DELETED/NOT RUNNING status.
        """
        status_repository = create_experiment_status_repository()
        new_status = RunningStatus.RUNNING if is_running else RunningStatus.NOT_RUNNING

        # Get the last_heartbeat if available (old experiments might not have it)
        last_heartbeat = status_row.last_heartbeat if status_row else None

        try:
            # Use guarded upsert to protect terminal states
            success = status_repository.upsert_status(
                exp_id=experiment.exp_id,
                expid=experiment.name,
                status=new_status,
                last_heartbeat=last_heartbeat,
            )

            if not success:
                # Update was rejected: log warning
                current_status = status_row.status if status_row else "UNKNOWN"
                cls.logger.warning(
                    f"[{cls.id}] Status update rejected for experiment {experiment.name}: "
                    f"attempted to update {new_status} on old state {current_status}"
                )
            else:
                cls.logger.info(
                    f"[{cls.id}] Status updated for experiment {experiment.name} to {new_status}"
                )
        except Exception as exc:
            cls.logger.error(
                f"[{cls.id}] Error while updating status for experiment {experiment.name}: {exc}"
            )

    @classmethod
    def procedure(cls):
        """
        Updates STATUS of RUNNING experiments (RUNNING -> NOT RUNNING).

        Skipts ARCHIVED, DELETED and NOT RUNNING experiments.
        Uses last_heartbeat as the main signal for RUNNING detection.
        """
        try:
            cls._clear_missing_experiments()
        except Exception as exc:
            cls.logger.error(
                f"[{cls.id}] Error while clearing missing experiments: {exc}"
            )
            return

        # Read experiments table
        try:
            exp_list = cls._get_experiments()
        except Exception as exc:
            cls.logger.error(
                f"[{cls.id}] Error loading experiments: {exc}"
            )
            return

        # Read current status of RUNNING experiments
        try:
            current_status_dict = cls._get_current_status()
        except Exception as exc:
            cls.logger.error(
                f"[{cls.id}] Error loading current experiment statuses: {exc}"
            )
            return

        # Check every experiment status & update (skip terminal statuses)
        for experiment in current_status_dict.values():
            cls.logger.error(
                f"[{cls.id}] Processing experiment {experiment.name} with current status {experiment.status}"
            )
            exp_name = experiment.name
            status_row = current_status_dict.get(exp_name)

            if status_row is None:
                # New experiment or no status yet: create with NOT RUNNING for retro-compatibility
                try:
                    cls.logger.info(
                        f"[{cls.id}] Initializing new experiment {exp_name} status"
                    )
                    # Set missing experiments as NOT RUNNING by default
                    cls._update_experiment_status(experiment, is_running=False, status_row=None)
                except Exception as exc:
                    cls.logger.error(
                        f"[{cls.id}] Error initializing status for experiment {exp_name}: {exc}"
                    )
                continue

            # Check if experiment is running
            is_running = cls._check_exp_running(exp_name, status_row)
            new_status = (
                RunningStatus.RUNNING if is_running else RunningStatus.NOT_RUNNING
            )

            # Only update if status changed
            if status_row.status != new_status:
                cls.logger.info(
                    f"[{cls.id}] Updating status of {experiment.name} to {new_status}"
                )
                cls._update_experiment_status(experiment, is_running, status_row)

            cls.logger.info(
                f"[{cls.id}] Status updater completed"
            )
