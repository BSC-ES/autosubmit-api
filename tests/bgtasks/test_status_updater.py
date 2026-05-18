from datetime import datetime, timedelta

import pytest

from autosubmit_api.common.utils import LOCAL_TZ
from autosubmit_api.bgtasks.tasks.status_updater import StatusUpdater
from autosubmit_api.history.database_managers.database_models import RunningStatus
from autosubmit_api.repositories.experiment import create_experiment_repository
from autosubmit_api.repositories.experiment_status import (
    create_experiment_status_repository,
    ExperimentStatusModel,
)

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

    def test_get_mutable_status_filters_terminal_statuses(
        self, fixture_mock_basic_config
    ):
        """Test _get_mutable_statuses excludes NOT_RUNNING, ARCHIVED and DELETED statuses."""
        experiment_status_repo = create_experiment_status_repository()
        experiment_status_repo.delete_all()

        experiment_status_repo.upsert_status(1, "a003", RunningStatus.RUNNING)
        experiment_status_repo.upsert_status(2, "a007", RunningStatus.NOT_RUNNING)
        experiment_status_repo.upsert_status(3, "a3tb", RunningStatus.ARCHIVED)
        experiment_status_repo.upsert_status(4, "a3t2", RunningStatus.DELETED)
        experiment_status_repo.upsert_status(5, "a5xx", "")

        # Act
        statuses = StatusUpdater._get_mutable_statuses()

        # Assert
        assert set(statuses.keys()) == {"a003", "a5xx"}
        assert statuses["a003"].status == RunningStatus.RUNNING
        assert statuses["a5xx"].status == ""

    def test_missing_experiments_are_initialized_as_not_running(
        self, fixture_mock_basic_config, monkeypatch
    ):
        """Test that experiments missing from the status table are initialized with NOT_RUNNING status."""
        # TODO: This tests needs to be changed for issue #287
        # In future implmementations, not all missing statuses will be initialized as NOT_RUNNING
        experiment_repo = create_experiment_repository()
        experiment_status_repo = create_experiment_status_repository()

        # Delete all experiment statuses entries, but not experiments
        experiment_status_repo.delete_all()
        experiments = experiment_repo.get_all()
        assert len(experiments) > 0

        StatusUpdater.run()

        exps_status = experiment_status_repo.get_all()

        assert len(experiments) == len(exps_status)
        assert set(x.id for x in experiments) == set(x.exp_id for x in exps_status)
        assert set(x.name for x in experiments) == set(x.name for x in exps_status)
        assert all(x.status == RunningStatus.NOT_RUNNING for x in exps_status)

    def test_only_mutable_experiments_are_evaluated(
        self, fixture_mock_basic_config, monkeypatch
    ):
        """Test that experiments with mutable statuses are evaluated
        and experiments with terminal statuses are not evaluated.
        RUNNING and "" statuses are mutable, while NOT_RUNNING, ARCHIVED and DELETED are terminal.
        """
        experiment_repo = create_experiment_repository()
        experiment_status_repo = create_experiment_status_repository()

        experiments = experiment_repo.get_all()
        assert len(experiments) >= 5

        running_exp = experiments[0]
        empty_exp = experiments[1]
        archived_exp = experiments[2]
        deleted_exp = experiments[3]
        not_running_exp = experiments[4]

        experiment_status_repo.delete_all()
        experiment_status_repo.upsert_status(
            running_exp.id, running_exp.name, RunningStatus.RUNNING
        )
        experiment_status_repo.upsert_status(empty_exp.id, empty_exp.name, "")
        experiment_status_repo.upsert_status(
            archived_exp.id, archived_exp.name, RunningStatus.ARCHIVED
        )
        experiment_status_repo.upsert_status(
            deleted_exp.id, deleted_exp.name, RunningStatus.DELETED
        )
        experiment_status_repo.upsert_status(
            not_running_exp.id, not_running_exp.name, RunningStatus.NOT_RUNNING
        )

        checked_experiments = []

        def _mock_check_exp_running(expid, status_row=None):
            checked_experiments.append(expid)
            if expid == running_exp.name:
                return True
            elif expid == empty_exp.name:
                return False
            else:
                raise ValueError(f"Unexpected experiment name: {expid}")

        monkeypatch.setattr(
            StatusUpdater,
            "_check_exp_running",
            _mock_check_exp_running,
        )

        StatusUpdater.run()

        # Mutable statuses must have been checked
        assert set(checked_experiments) == {running_exp.name, empty_exp.name}
        # Terminal statuses must not have been checked
        assert archived_exp.name not in checked_experiments
        assert deleted_exp.name not in checked_experiments
        assert not_running_exp.name not in checked_experiments

        # Statuses must have been updated according to the fake_check_exp_running logic
        assert (
            experiment_status_repo.get_by_expid(running_exp.name).status
            == RunningStatus.RUNNING
        )
        assert (
            experiment_status_repo.get_by_expid(empty_exp.name).status
            == RunningStatus.NOT_RUNNING
        )
        assert (
            experiment_status_repo.get_by_expid(archived_exp.name).status
            == RunningStatus.ARCHIVED
        )
        assert (
            experiment_status_repo.get_by_expid(deleted_exp.name).status
            == RunningStatus.DELETED
        )
        assert (
            experiment_status_repo.get_by_expid(not_running_exp.name).status
            == RunningStatus.NOT_RUNNING
        )

    def test_check_exp_running_prioritizes_heartbeat_over_pkl(
        self, fixture_mock_basic_config, monkeypatch
    ):
        """Test that _check_exp_running prioritizes heartbeat age over pkl age."""
        now = datetime.now(tz=LOCAL_TZ)
        fresh_heartbeat = (now - timedelta(minutes=1)).isoformat()

        status_row = ExperimentStatusModel(
            exp_id=1,
            name="a003",
            status=RunningStatus.RUNNING,
            seconds_diff=0,
            modified=now.isoformat(),
            last_heartbeat=fresh_heartbeat,
        )

        monkeypatch.setattr(
            "autosubmit_api.bgtasks.tasks.status_updater.time.time",
            lambda: int(now.timestamp()),
        )

        def _should_not_be_called(_):
            raise AssertionError("create_jobs_repository should not be called")

        monkeypatch.setattr(
            "autosubmit_api.bgtasks.tasks.status_updater.create_jobs_repository",
            _should_not_be_called,
        )

        assert StatusUpdater._check_exp_running("a003", status_row) is True

    def test_stale_heartbeat_changes_running_to_not_running(
        self, fixture_mock_basic_config, monkeypatch
    ):
        """Test that RUNNING experiment with stale heartbeat become NOT_RUNNING."""
        experiment_repo = create_experiment_repository()
        experiment_status_repo = create_experiment_status_repository()

        experiments = experiment_repo.get_all()
        assert len(experiments) >= 1
        exp = experiments[0]

        now = datetime.now(tz=LOCAL_TZ)
        stale_heartbeat = (
            now - timedelta(minutes=3)
        ).isoformat()  # 3 min old > 150s threshold

        experiment_status_repo.delete_all()
        experiment_status_repo.upsert_status(
            exp.id, exp.name, RunningStatus.RUNNING, last_heartbeat=stale_heartbeat
        )

        monkeypatch.setattr(
            "autosubmit_api.bgtasks.tasks.status_updater.time.time",
            lambda: int(now.timestamp()),
        )

        # Mock create_jobs_repository to avoid pickle checks. This is tested in other unit tests
        def mock_jobs_repo(expid):
            raise AssertionError(
                "Should not reach pickle check if last_heartbeat is present"
            )

        monkeypatch.setattr(
            "autosubmit_api.bgtasks.tasks.status_updater.create_jobs_repository",
            mock_jobs_repo,
        )

        StatusUpdater.run()

        status = experiment_status_repo.get_by_expid(exp.name)
        assert status.status == RunningStatus.NOT_RUNNING

    def test_unparsable_heartbeat_falls_back_to_pickle(
        self, fixture_mock_basic_config, monkeypatch
    ):
        """Test that if last_heartbeat is unparsable, it falls back to checking the pickle file."""
        experiment_repo = create_experiment_repository()
        experiment_status_repo = create_experiment_status_repository()

        experiments = experiment_repo.get_all()
        assert len(experiments) >= 1
        exp = experiments[0]

        now = datetime.now(tz=LOCAL_TZ)
        unparsable_heartbeat = "not-a-timestamp"

        experiment_status_repo.delete_all()
        experiment_status_repo.upsert_status(
            exp.id, exp.name, RunningStatus.RUNNING, last_heartbeat=unparsable_heartbeat
        )

        monkeypatch.setattr(
            "autosubmit_api.bgtasks.tasks.status_updater.time.time",
            lambda: int(now.timestamp()),
        )

        # Mock create_jobs_repository to return fresh pickle
        # 1 min old < 10 min threshold
        class MockJobsRepo:
            def get_last_modified_timestamp(self):
                return int((now - timedelta(minutes=1)).timestamp())

        monkeypatch.setattr(
            "autosubmit_api.bgtasks.tasks.status_updater.create_jobs_repository",
            lambda expid: MockJobsRepo(),
        )

        StatusUpdater.run()

        status = experiment_status_repo.get_by_expid(exp.name)
        # Unparsable heartbeat should fall back to pickle check, which is fresh, so stay as RUNNING
        assert status.status == RunningStatus.RUNNING

    @pytest.mark.parametrize(
        "upsert_error",
        [False, True],
        ids=[
            "experiment status not found returns 0",
            "upsert failure raises exception",
        ],
    )
    def test_unsuccessfull_upsert(
        self, fixture_mock_basic_config, monkeypatch, upsert_error, caplog
    ):
        """Test that if upsert fails, it's logged and if experiment status not found upsert return 0 and log a warning."""
        experiment_repo = create_experiment_repository()
        experiment_status_repo = create_experiment_status_repository()

        experiments = experiment_repo.get_all()
        assert len(experiments) >= 1

        now = datetime.now(tz=LOCAL_TZ)

        experiment_status_repo.delete_all()

        monkeypatch.setattr(
            "autosubmit_api.bgtasks.tasks.status_updater.time.time",
            lambda: int(now.timestamp()),
        )

        def mock_upsert_status(*args, **kwargs):
            if upsert_error:
                raise Exception("Upsert failed")
            else:
                return 0

        monkeypatch.setattr(
            "autosubmit_api.repositories.experiment_status.ExperimentStatusSQLRepository.upsert_status",
            mock_upsert_status,
        )

        # Run the updater with caplog to catch logs
        # Act
        caplog.clear()
        StatusUpdater.run()

        # Assert
        if upsert_error:
            # Exception raised by repository should be caught and logged as error
            assert any(
                rec.levelname == "ERROR" and "Upsert failed" in rec.message
                for rec in caplog.records
            )
        else:
            # Upsert returning 0 should log a warning about rejected update
            assert any(
                rec.levelname == "WARNING" and "Status update rejected" in rec.message
                for rec in caplog.records
            )

    def test_clear_missing_experiments_logs_warning_when_raises_exception(
        self, fixture_mock_basic_config, monkeypatch, caplog
    ):
        """Test that if _clear_missing_experiments raises an exception, it's logged as a warning and exits early."""
        experiment_status_repo = create_experiment_status_repository()
        experiment_status_repo.delete_all()

        # Mock _clear_missing_experiments to raise an exception
        def mock_clear_missing_experiments():
            raise Exception("Database error during clear")

        monkeypatch.setattr(
            StatusUpdater, "_clear_missing_experiments", mock_clear_missing_experiments
        )

        # Run the updater with caplog to catch logs
        # Act
        caplog.clear()
        StatusUpdater.run()

        # Assert
        assert any(
            rec.levelname == "ERROR" and "Database error during clear" in rec.message
            for rec in caplog.records
        )

        # Assert that it returns early: status table should still be empty
        statuses = experiment_status_repo.get_all()
        assert len(statuses) == 0

    def test_set_status_repository_get_all_logs_error_when_raises_exception(
        self, fixture_mock_basic_config, monkeypatch, caplog
    ):
        """Test that if _get_all raises an exception, it is logged and the updater exists early."""
        experiment_status_repo = create_experiment_status_repository()
        experiment_status_repo.delete_all()

        # Mock _get_all to raise an exception
        def mock_create():
            repo = create_experiment_status_repository()
            def mock_get_all():
                raise Exception("Database error during get_all")
            repo.get_all = mock_get_all
            return repo

        monkeypatch.setattr(
            "autosubmit_api.bgtasks.tasks.status_updater.create_experiment_status_repository",
            mock_create
        )

        # Run the updater with caplog to catch logs
        # Act
        caplog.clear()
        StatusUpdater.run()

        # Assert
        assert any(
            rec.levelname == "ERROR" and "Database error during get_all" in rec.message
            for rec in caplog.records
        )

        # Assert that it returns early: status table should still be empty
        statuses = experiment_status_repo.get_all()
        assert len(statuses) == 0

    def test_update_experiment_status_logs_error_when_upsert_fails(
        self, fixture_mock_basic_config, monkeypatch, caplog
    ):
        """Test that if upsert_status raises an exception during status update, 
        it is logged as an error and the updater continues updating other experiments."""
        experiment_repo = create_experiment_repository()
        experiment_status_repo = create_experiment_status_repository()

        experiments = experiment_repo.get_all()
        assert len(experiments) >= 1
        exp = experiments[0]

        now = datetime.now(tz=LOCAL_TZ)

        experiment_status_repo.delete_all()
        experiment_status_repo.upsert_status(
            exp.id, exp.name, RunningStatus.RUNNING, last_heartbeat=now.isoformat()
        )

        # Mock upsert_status to raise an exception for a specific experiment
        def mock_create():
            repo = create_experiment_status_repository()
            def mock_upsert_status(*args, **kwargs):
                raise Exception("Database error during upsert")
            repo.upsert_status = mock_upsert_status
            return repo
        monkeypatch.setattr(
            "autosubmit_api.bgtasks.tasks.status_updater.create_experiment_status_repository",
            mock_create
        )

        # Run the updater with caplog to catch logs
        # Act
        caplog.clear()
        StatusUpdater.run()

        # Assert
        assert any(
            rec.levelname == "ERROR" and "Database error during upsert" in rec.message
            for rec in caplog.records
        )
