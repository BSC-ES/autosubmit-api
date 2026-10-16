"""Job list of an experiment, ready to be serialized by the API."""

from collections.abc import Callable
from datetime import datetime
from typing import Any

from autosubmit_api.common.utils import Status, timestamp_to_datetime_format
from autosubmit_api.components.jobs.utils import get_fixed_experiment_times
from autosubmit_api.exceptions import DomainError, InternalError
from autosubmit_api.models.jobs import UNSET, JobCategoryProperty, JobView, Unset
from autosubmit_api.models.pagination import Page, PaginationInfo
from autosubmit_api.models.requests import JobsSearchRequest
from autosubmit_api.models.responses import (
    ExperimentJobItem,
    ExperimentJobsFilters,
    ExperimentJobsResponse,
)
from autosubmit_api.repositories.job_data import (
    ExperimentJobDataModel,
    ExperimentJobDataRepository,
    create_experiment_job_data_repository,
)
from autosubmit_api.repositories.jobs import (
    JobData,
    JobsRepository,
    create_jobs_repository,
)


def _to_filter(value: Any) -> Any:
    """
    Translates an HTTP filter parameter into a repository filter value.

    - ``None`` (not provided): ``UNSET``, meaning "do not filter".
    - ``NA``: ``None``, meaning "jobs without a value for this property".
    - anything else: the value itself.
    """
    if value is None:
        return UNSET
    if value == "NA":
        return None
    return value


def _to_name_filter(name: str | None) -> str | Unset:
    """
    Translates the HTTP job name parameter into a repository filter value.

    A job always has a name, so this filter has no empty value: an absent or empty
    parameter means "do not filter by name".
    """
    return name if name else UNSET


def _applied_filters(query: JobsSearchRequest) -> ExperimentJobsFilters:
    """
    Gets the filters of the search that were applied to the job list.

    The filters that were not used are left unset, so they are excluded from the
    payload: that tells them apart from a filter for the jobs without a value for
    the property (``"NA"``).
    """
    return ExperimentJobsFilters(
        **{
            prop.value: value
            for prop in JobCategoryProperty
            if (value := getattr(query, prop.value)) is not None
        }
    )


def _job_content(job: JobData) -> dict[str, Any]:
    """Content of a job of the job list, as returned by the ``base`` view."""
    return {
        "priority": job.priority,
        "section": job.section,
        "date": (
            job.date.date().isoformat() if isinstance(job.date, datetime) else None
        ),
        "member": job.member,
        "chunk": job.chunk,
        "split": job.split,
        "splits": job.splits,
        "out_path_local": job.out_path_local,
        "err_path_local": job.err_path_local,
        "out_path_remote": job.out_path_remote,
        "err_path_remote": job.err_path_remote,
    }


def _job_times(
    expid: str, job: JobData, last_job_data: ExperimentJobDataModel | None
) -> dict[str, Any]:
    """
    Execution times of a job, as returned by the ``extended`` view.

    The times of the job data are only used when that record matches the status of
    the job: a job that ran after its last record has no times to report, and they
    are reported as ``None``.
    """
    submit, start, finish = get_fixed_experiment_times(expid, job, last_job_data)
    return {
        "submit": timestamp_to_datetime_format(submit),
        "start": timestamp_to_datetime_format(start),
        "finish": timestamp_to_datetime_format(finish),
    }


class ExperimentJobsService:
    """
    Builds the job list of an experiment applying its filters and the view.

    Each job comes from the jobs repository (pkl or database). The ``extended``
    view reports the execution times of the job, which come from the historical job
    data: that is the only view that needs the job data repository, and it is built
    on demand so the other views keep a single query.
    """

    def __init__(
        self,
        jobs_repo: JobsRepository,
        expid: str,
        job_data_repo_factory: Callable[
            [str], ExperimentJobDataRepository
        ] = create_experiment_job_data_repository,
    ):
        self.jobs_repo = jobs_repo
        self.expid = expid
        self._job_data_repo_factory = job_data_repo_factory

    def list_jobs(self, query: JobsSearchRequest) -> ExperimentJobsResponse:
        """
        Gets the page of jobs matching the filters of the validated ``query``.

        :param query: Validated request, holding the filters, the view and the
            pagination of the job list.
        """
        page = Page.of(query.page, query.page_size)

        try:
            jobs, total_items = self.jobs_repo.search(
                job_name=_to_name_filter(query.job_name),
                status=_to_filter(query.status),
                date=_to_filter(query.date),
                member=_to_filter(query.member),
                section=_to_filter(query.section),
                chunk=_to_filter(query.chunk),
                page=page,
            )
        except DomainError:
            raise
        except Exception as exc:
            raise InternalError("Error while reading the job list") from exc

        last_job_data = self._get_last_job_data(jobs, query.view)
        jobs_list = [
            self._build_item(job, query.view, last_job_data.get(job.name))
            for job in jobs
        ]

        return ExperimentJobsResponse(
            jobs=jobs_list,
            filters=_applied_filters(query),
            pagination=PaginationInfo.from_page(
                page, total_items=total_items, page_items=len(jobs_list)
            ),
        )

    def _get_last_job_data(
        self, jobs: list[JobData], view: JobView
    ) -> dict[str, ExperimentJobDataModel]:
        """
        Gets the last job data of ``jobs``, only needed by the extended view.
        """
        if view is not JobView.EXTENDED or not jobs:
            return {}

        try:
            job_data_repo = self._job_data_repo_factory(self.expid)
            return {
                job_data.job_name: job_data
                for job_data in job_data_repo.get_last_job_data_by_name_list(
                    [job.name for job in jobs]
                )
            }
        except DomainError:
            raise
        except Exception as exc:
            raise InternalError("Error while reading the last job data") from exc

    def _build_item(
        self,
        job: JobData,
        view: JobView,
        last_job_data: ExperimentJobDataModel | None = None,
    ) -> ExperimentJobItem:
        """
        Builds the item of a job with the content of the requested view.

        The fields of the other views are left unset (instead of ``None``) so the
        response model can exclude them from the payload. Within a view, a field is
        always present and ``None`` means that its value is unknown.
        """
        fields: dict[str, Any] = {
            "name": job.name,
            "status": Status.VALUE_TO_KEY.get(job.status, "UNKNOWN"),
        }

        if view is JobView.BASE:
            fields.update(_job_content(job))
        elif view is JobView.EXTENDED:
            fields.update(_job_times(self.expid, job, last_job_data))

        return ExperimentJobItem(**fields)


def create_experiment_jobs_service(expid: str) -> ExperimentJobsService:
    """
    Builds the job list service of an experiment.

    :raises ExperimentNotFoundError: If the experiment does not exist
    """
    return ExperimentJobsService(jobs_repo=create_jobs_repository(expid), expid=expid)
