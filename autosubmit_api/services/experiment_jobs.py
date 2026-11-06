"""Job list of an experiment, ready to be serialized by the API."""

from collections.abc import Callable
from datetime import datetime
from typing import Any

from autosubmit_api.common.utils import Status, timestamp_to_datetime_format
from autosubmit_api.components.jobs.utils import get_fixed_experiment_times
from autosubmit_api.exceptions import DomainError, InternalError
from autosubmit.api.logger import logger
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
from autosubmit_api.repositories.job_packages import(
    JobPackageModel,
    JobPackagesRepository,
    create_job_packages_repository,
)
from autosubmit_api.repositories.jobs import (
    JobData,
    JobsRepository,
    create_jobs_repository,
)


def _to_filter(value: Any) -> Any:
    """Translates an HTTP filter parameter into a repository filter value.

    - ``None`` (not provided): ``UNSET``, meaning "do not filter".
    - ``NA``: ``None``, meaning "jobs without a value for this property".
    - Anything else: the value itself.

    :param value: Filter value received from the HTTP request.
    :return: ``UNSET`` if the ``value`` is ``None``, ``None`` if it is ``NA``,
        otherwise ``value`` unchanged.
    """
    if value is None:
        return UNSET
    if value == "NA":
        return None
    return value


def _to_name_filter(name: str | None) -> str | Unset:
    """Translates the HTTP job name parameter into a repository filter value.

    A job always has a name, so this filter has no empty value: an absent or empty
    parameter means "do not filter by name".

    :param name: Job name received from the HTTP request.
    :return: ``UNSET`` if the ``name`` is ``None`` or empty
    """
    return name if name else UNSET


def _applied_filters(query: JobsSearchRequest) -> ExperimentJobsFilters:
    """Gets the filters of the search that were applied to the job list.

    The filters that were not used are left unset, so they are excluded from the
    payload: that tells them apart from a filter for the jobs without a value for
    the property (``"NA"``).

    :param query: Validated request, holding the filters, the view and the
        pagination of the job list.
    :return: Filters that were applied to the job list.
    """
    return ExperimentJobsFilters(
        **{
            prop.value: value
            for prop in JobCategoryProperty
            if (value := getattr(query, prop.value)) is not None
        }
    )


def _job_content(job: JobData) -> dict[str, Any]:
    """Content of a job of the job list, as returned by the ``base`` view.
    
    :param job: Job data from the jobs repository.
    :return: Dictionary with the job content.
    """
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
    """Execution times of a job, as returned by the ``extended`` view.

    The times of the job data are only used when that record matches the status of
    the job: a job that ran after its last record has no times to report, and they
    are reported as ``None``.

    :param expid: Experiment identifier.
    :param job: Job data from the jobs repository.
    :param last_job_data: Last job data of the job, or ``None`` if it does not exist.
    :return: Dictionary with the job execution times.
    """
    submit, start, finish = get_fixed_experiment_times(expid, job, last_job_data)
    return {
        "submit": timestamp_to_datetime_format(submit),
        "start": timestamp_to_datetime_format(start),
        "finish": timestamp_to_datetime_format(finish),
    }


class ExperimentJobsService:
    """Builds the job list of an experiment applying its filters and the view.

    Each job comes from the jobs repository (pkl or database). The ``extended``
    view reports where the job is and its execution times, and the times come from
    the historical job data: that is the only view that needs the job data
    repository, and it is built on demand so the other views keep a single query.

    The ``base`` and ``extended`` views also report the wrapper (job package) the
    job list is part of. That mapping lives int he packaging database, so it is read
    once per page and only when the view reports it.
    """

    def __init__(
        self,
        jobs_repo: JobsRepository,
        expid: str,
        job_data_repo_factory: Callable[
            [str], ExperimentJobDataRepository
        ] = create_experiment_job_data_repository,
        wrapper_repo_factory: Callable[..., JobPackagesRepository] = (
            create_job_packages_repository
        ),
    ):
        self.jobs_repo = jobs_repo
        self.expid = expid
        self._job_data_repo_factory = job_data_repo_factory
        self._wrapper_repo_factory = wrapper_repo_factory

    def list_jobs(self, query: JobsSearchRequest) -> ExperimentJobsResponse:
        """Gets the page of jobs matching the filters of the validated ``query``.

        :param query: Validated request, holding the filters, the view and the
            pagination of the job list.
        :return: Job list response, with the jobs, the applied filters and the
            pagination information.
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
        wrappers = self._get_wrappers(jobs, query.view)
        jobs_list = [
            self._build_item(
                job, query.view, last_job_data.get(job.name), wrappers.get(job.name)
            )
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
        """Gets the last job data of ``jobs``, only needed by the extended view.

        :param jobs: Jobs of the job list.
        :param view: View of the job list, to know if the last job data is needed.
        :return: Dictionary of last job data, keyed by job name.
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

    def _get_wrappers(self, jobs: list[JobData], view: JobView) -> dict[str, str]:
        """Gets the wrappers of ``jobs``, only needed by the base and extended views.

        Wrappers are optional: an experiment that has not yet run has no wrapper for
        its jobs, so a missing or unreadable packaging db means "no wrapper" instead
        of an error, which is what the job list has to report for those jobs.

        The lookup is done for the jobs of the page only, with a single query.

        :param jobs: Jobs of the job list.
        :param view: View of the job list, to know if the wrappers are needed.
        :return: Dictionary of wrappers, keyed by job name. Jobs without a wrapper are not
            included.
        """
        if view in JobView.QUICK or not jobs:
            return {}

        job_names = [job.name for job in jobs]
        packages = self._read_packages(job_names, preview=False)
        if not packages:
            packages = self._read_packages(job_names, preview=True)

        wrappers: dict[str, str] = {}
        for package in packages:
            if package.package_name:
                wrappers.setdefault(package.job_name, package.package_name)
        return wrappers

    def _read_packages(
        self, job_names: list[str], preview: bool = False
    ) -> list[JobPackageModel]:
        """Reads the packaging of ``job_names`` from the packaging database.

        :param job_names: Job names to look up.
        :param preview: Whether to read the packaging of an experiment that has not run yet.
        :return: Packaging of the requested jobs, empty if the experiment has no packaging
            yet or if it cannot be read.
        """
        try:
            return self._wrapper_repo_factory(
                self.expid, preview=preview
            ).get_by_job_name_list(job_names)
        except DomainError:
            raise
        except Exception as exc:
            logger.warning(
                "Error while reading the job packaging of experiment %s: %s",
                self.expid,
                exc,
            )
            return []

    def _build_item(
        self,
        job: JobData,
        view: JobView,
        last_job_data: ExperimentJobDataModel | None = None,
        wrapper: str | None = None,
    ) -> ExperimentJobItem:
        """Builds the item of a job with the content of the requested view.

        The fields of the other views are left unset (instead of ``None``) so the
        response model can exclude them from the payload. Within a view, a field is
        always present and ``None`` means that its value is unknown.

        :param job: Job data from the jobs repository.
        :param view: View of the job list, to know which fields to include.
        :param last_job_data: Last job data of the job, or ``None`` if it does not exist. Only needed by the extended view.
        :param wrapper: Wrapper of the job, or ``None`` if it has none.
        :return: Job list item with the content of the requested view.
        """
        fields: dict[str, Any] = {
            "name": job.name,
            "status": Status.VALUE_TO_KEY.get(job.status, "UNKNOWN"),
        }

        if view is JobView.BASE:
            fields.update(_job_content(job), wrapper=wrapper)
        elif view is JobView.EXTENDED:
            # Section and chunk are there to locate the job: the job list of the
            # tree view groups the jobs by section and only estimates the time of
            # arrival of the sections that run within chunks.
            fields.update(
                section=job.section,
                chunk=job.chunk,
                wrapper=wrapper,
                **_job_times(self.expid, job, last_job_data),
            )

        return ExperimentJobItem(**fields)


def create_experiment_jobs_service(expid: str) -> ExperimentJobsService:
    """Builds the job list service of an experiment.

    :param expid: Experiment identifier.
    :return: Service that builds the job list of the experiment.
    :raises ExperimentNotFoundError: If the experiment does not exist
    """
    return ExperimentJobsService(jobs_repo=create_jobs_repository(expid), expid=expid)
