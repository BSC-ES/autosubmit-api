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
    def _get_mutable_statuses(
        cls, experiment_statuses: Optional[List[ExperimentStatusModel]] = None
    ) -> Dict[str, ExperimentStatusModel]:
        """
        Return only mutable experiment statuses.
        """
        if experiment_statuses is None:
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
        check_pickle = True

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
                    # Heartbeat is stale, don't fall back to pickle
                    check_pickle = False
                except Exception as exc:
                    cls.logger.warning(
                        f"[{cls.id}] Could not parse heartbeat for {expid}: {exc}"
                    )
                    # Unparsable heartbeat, fall back to pickle check
                    check_pickle = True
            
            # Priority 2 and 3: Check pickle file if no valid heartbeat
            if check_pickle:
                try:
                    job_list_repo = create_jobs_repository(expid)
                    pkl_age = current_time - job_list_repo.get_last_modified_timestamp()

                    # Priority 2: Check pickle file age
                    if pkl_age < MAX_PKL_AGE:  # First running check
                        is_running = True
                        return is_running

                    # Priority 3: Check using filesystem
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
                f"[{cls.id}] Experiment {expid} is not running"
            )
        except Exception as exc:
            cls.logger.error(
                f"[{cls.id}] Error while checking if experiment {expid} is running: {exc}"
            )

        return is_running

    @classmethod
    def _update_experiment_status(
        cls,
        experiment: ExperimentModel,
        is_running: bool,
        status_row: Optional[ExperimentStatusModel] = None,
    ):
        """
        Update experiment status using guarded conditional update.

        Guard against overwritting ARCHIVED/DELETED/NOT RUNNING status.
        """
        status_repository = create_experiment_status_repository()
        new_status = RunningStatus.RUNNING if is_running else RunningStatus.NOT_RUNNING

        # Get the last_heartbeat if available (old experiments might not have it)
        last_heartbeat = status_row.last_heartbeat if status_row else None

        try:
            success = status_repository.upsert_status(
                exp_id=experiment.id,
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

        Skips ARCHIVED, DELETED and NOT_RUNNING experiments (terminal statuses).
        Checks RUNNING status and empty status experiments.
        Uses last_heartbeat as the main signal for RUNNING detection.
        """
        try:
            cls._clear_missing_experiments()
        except Exception as exc:
            cls.logger.error(
                f"[{cls.id}] Error while clearing missing experiments: {exc}"
            )
            return

        status_repository = create_experiment_status_repository()

        # Read current status snapshots once.
        try:
            all_status_rows = status_repository.get_all()
        except Exception as exc:
            cls.logger.error(
                f"[{cls.id}] Error loading current experiment statuses: {exc}"
            )
            return

        all_status_dict = {row.name: row for row in all_status_rows}
        current_status_dict = cls._get_mutable_statuses(all_status_rows)
        all_experiments = {
            experiment.name: experiment for experiment in cls._get_experiments()
        }

        # Initialize experiments that are not yet present in the status table.
        for exp_name, experiment in all_experiments.items():
            if exp_name in all_status_dict:
                continue

            try:
                cls.logger.debug(
                    f"[{cls.id}] Initializing new experiment {exp_name} status"
                )
                cls._update_experiment_status(
                    experiment,
                    is_running=False,
                    status_row=None,
                )
            except Exception as exc:
                cls.logger.error(
                    f"[{cls.id}] Error initializing status for experiment {exp_name}: {exc}"
                )

        # Evaluate only mutable experiments (RUNNING and empty status)
        for exp_name, status_row in current_status_dict.items():
            experiment = all_experiments.get(exp_name)
            if experiment is None:
                cls.logger.warning(
                    f"[{cls.id}] Experiment {exp_name} found in status table but not in experiments table"
                )
                continue

            is_running = cls._check_exp_running(exp_name, status_row)
            new_status = (
                RunningStatus.RUNNING if is_running else RunningStatus.NOT_RUNNING
            )

            # Only update if status changed
            if status_row.status != new_status:
                cls.logger.debug(
                    f"[{cls.id}] Updating status of {experiment.name} to {new_status}"
                )
                cls._update_experiment_status(experiment, is_running, status_row)

        cls.logger.debug(f"[{cls.id}] Status updater completed")
