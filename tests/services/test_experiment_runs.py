import pytest

from autosubmit_api.exceptions import InternalError
from autosubmit_api.models.responses import ExperimentRunsResponse
from autosubmit_api.repositories.experiment_run import ExperimentRunModel
from autosubmit_api.services.experiment_runs import ExperimentRunsService

EXPID = "a000"



def make_run(run_id: int = 1) -> ExperimentRunModel:
    return ExperimentRunModel(
        run_id=run_id,
        created="2026-11-24 00:00:00",
        modified=None,
        start=1712847236,
        finish=1712850000,
        chunk_unit="month",
        chunk_size=4,
        completed=8,
        total=8,
        failed=0,
        queuing=0,
        running=0,
        submitted=0,
        suspended=0,
        metadata=None,
    )


class MockExperimentRunRepository:
    """Returns a fixed run list and records whether it was read."""

    def __init__(self, runs: list[ExperimentRunModel] = None, error: Exception = None):
        self.runs = runs or []
        self.error = error
        self.reads = 0

    def get_all(self) -> list[ExperimentRunModel]:
        self.reads += 1
        if self.error is not None:
            raise self.error
        return self.runs


@pytest.fixture
def history_exists():
    """Returns a function that always returns True, meaning the experiment has run history."""

    def _history_exists(expid: str) -> bool:
        return True

    return _history_exists


class TestListRuns:
    def test_runs_reported_newest_first(self, history_exists):
        """The runs of an experiment are reported from newest to oldest."""
        runs = [make_run(run_id=3), make_run(run_id=2), make_run(run_id=1)]
        service = ExperimentRunsService(
            expid="a3tb",
            runs_repo=MockExperimentRunRepository(runs),
            history_exists=history_exists,
        )

        response = service.list_runs()

        assert isinstance(response, ExperimentRunsResponse)
        assert [run.run_id for run in response.runs] == [3, 2, 1]

    def test_exp_without_run_history_returns_empty_list(self):
        """An experiment that has never run returns an empty list of runs."""
        repo = MockExperimentRunRepository([make_run()])
        service = ExperimentRunsService(
            expid="EXPID", runs_repo=repo, history_exists=lambda expid: False
        )

        assert service.list_runs().runs == []
        # The historical runs db should not be opened
        assert repo.reads == 0

    def test_history_checked_for_exp(self, history_exists):
        """The service checks whether the experiment has run history."""
        checked: list[str] = []

        def _history_exists(expid: str) -> bool:
            checked.append(expid)
            return True

        service = ExperimentRunsService(
            expid=EXPID,
            runs_repo=MockExperimentRunRepository(),
            history_exists=_history_exists,
        )

        service.list_runs()

        assert checked == [EXPID]

    def test_failing_repo_reported_as_internal_error(self, history_exists):
        """If the repository fails, the service raises an InternalError."""
        service = ExperimentRunsService(
            expid=EXPID,
            runs_repo=MockExperimentRunRepository(error=OSError("cannot read the database")),
            history_exists=history_exists,
        )

        with pytest.raises(InternalError) as error:
            service.list_runs()

        assert "Error while reading experiment runs" in str(error.value)

    def test_failing_history_check_reported_as_internal_error(self):
        """If the history check fails, the service raises an InternalError."""
        def _history_exists(expid: str) -> bool:
            raise OSError("cannot check history")

        service = ExperimentRunsService(
            expid=EXPID,
            runs_repo=MockExperimentRunRepository(),
            history_exists=_history_exists,
        )

        with pytest.raises(InternalError):
            service.list_runs()
