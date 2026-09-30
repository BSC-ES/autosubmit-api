import pytest

from autosubmit_api.bgtasks.tasks.status_updater import StatusUpdater
from autosubmit_api.exceptions import JobListNotFoundError
from autosubmit_api.history.database_managers.database_models import RunningStatus
from autosubmit_api.repositories.experiment import create_experiment_repository
from autosubmit_api.repositories.experiment_status import create_experiment_status_repository


class TestStatusUpdater:
    def test_same_tables(self, fixture_mock_basic_config):
        experiment_repo = create_experiment_repository()
        experiment_status_repo = create_experiment_status_repository()

        experiment_status_repo.delete_all()
        exps_status = experiment_status_repo.get_all()
        assert len(exps_status) == 0

        # Run the task
        StatusUpdater.run()

        # Check the results
        experiments = experiment_repo.get_all()
        exps_status = experiment_status_repo.get_all()

        assert len(experiments) > 0 and len(exps_status) > 0
        assert len(experiments) == len(exps_status)
        assert set([x.id for x in experiments]) == set([x.exp_id for x in exps_status])
        assert set([x.name for x in experiments]) == set([x.name for x in exps_status])

        for e_st in exps_status:
            assert e_st.status in [RunningStatus.RUNNING, RunningStatus.NOT_RUNNING]

    def test_check_exp_running_without_job_list(
        self, fixture_mock_basic_config, monkeypatch: pytest.MonkeyPatch
    ):
        """
        An experiment without a job list should be considered as not running
        without logging an error.
        """

        def _raise_job_list_not_found(expid: str):
            raise JobListNotFoundError(expid)

        monkeypatch.setattr(
            "autosubmit_api.bgtasks.tasks.status_updater.create_jobs_repository",
            _raise_job_list_not_found,
        )

        assert StatusUpdater._check_exp_running("a1x4") is False
