"""Runs of an experiment, ready to be serialized by the API."""

from fastapi import Path

from autosubmit_api.common.utils import timestamp_to_datetime_format
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.models.experiment import BaseExperimentRun
from autosubmit_api.models.responses import ExperimentRunsResponse
from autosubmit_api.persistance.experiment import ExperimentPaths
from autosubmit_api.repositories.experiment import create_experiment_repository
from autosubmit_api.repositories.experiment_run import (
    ExperimentRunModel,
    ExperimentRunRepository,
    create_experiment_run_repository,
)


def _has_run_history(expid: str) -> bool:
    """Whether the runs of the experiment can be read from its historical database.

    # TODO: Check if the postgres backend is changed
    An experiment that has never run has no historical database, and that is not an
    error: it simply has no runs. Currently, the postgres backend has a schema per experiment,
    created with the experiment, so the query already returns the right empty result
    there and only the file of the sqlite backend has to be checked.

    :param expid: Experiment identifier.
    :return: ``True`` if the runs of the experiment can be read.
    """
    if APIBasicConfig.DATABASE_BACKEND == "postgres":
        return True
    return Path(ExperimentPaths(expid).job_data_db).exists()


def _run_status(run: ExperimentRunModel) -> str:
    """Derive the state of a run from the job counters stored in the historical database.

    The historical database does not store the state of a run, so it is derived from
    the counters it does store:

    - ``RUNNING``: jobs are queuing, running or submitted.
    - ``COMPLETED``: every job of the run is completed.
    - ``FAILED``: there are failed jobs and nothing in flight.
    - ``UNKNOWN``: anything else, e.g. a run that was interrupted before finishing.

    :param run: Run of the historical database.
    :return: State of the run.
    """
    if (run.running or 0) > 0 or (run.queuing or 0) > 0 or (run.submitted or 0) > 0:
        return "RUNNING"

    total = run.total or 0
    if total > 0 and (run.completed or 0) >= total:
        return "COMPLETED"

    if (run.failed or 0) > 0:
        return "FAILED"

    return "UNKNOWN"


def _to_run_item(run: ExperimentRunModel) -> BaseExperimentRun:
    """Convert a run of the historical database into an API response.

    The times of the historical database are UNIX timestamps, and they are reported
    with the same helper as the job list, so every time of the API is formatted the
    same way. The timestamps it does not know (it stores a 0) are reported as ``None``.

    :param run: Run of the historical database.
    :return: Run ready to be serialized by the API.
    """
    return BaseExperimentRun(
        run_id=run.run_id,
        created=run.created,
        start=timestamp_to_datetime_format(run.start),
        finish=timestamp_to_datetime_format(run.finish),
        status=_run_status(run),
        chunk_unit=run.chunk_unit,
        chunk_size=run.chunk_size,
        queuing=run.queuing,
        running=run.running,
        submitted=run.submitted,
        completed=run.completed,
        failed=run.failed,
        suspended=run.suspended,
        total=run.total,
    )


class ExperimentRunsService:
    """Lists the runs of an experiment from its historical database.

    Only the data that the historical database stores per run is reported, so the
    response does not depend on the number of jobs of the experiment.
    """

    def __init__(self, expid: str, runs_repo: ExperimentRunRepository):
        self.expid = expid
        self.runs_repo = runs_repo

    def list_runs(self) -> ExperimentRunsResponse:
        """Runs of the experiment, newest first.

        :return: Runs of the experiment, or no runs if it has never run.
        """
        if not _has_run_history(self.expid):
            return ExperimentRunsResponse(runs=[])

        return ExperimentRunsResponse(
            runs=[_to_run_item(run) for run in self.runs_repo.get_all()]
        )


def create_experiment_runs_service(expid: str) -> ExperimentRunsService:
    """Builds the runs service of an experiment.

    :param expid: Experiment identifier.
    :return: Service that lists the runs of the experiment.
    :raises ExperimentNotFoundError: If the experiment does not exist
    """
    # Experiment should exist, whatever the backend is
    create_experiment_repository().get_by_expid(expid)

    return ExperimentRunsService(
        expid=expid, runs_repo=create_experiment_run_repository(expid)
    )
