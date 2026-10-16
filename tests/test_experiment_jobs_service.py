"""Tests of the experiment job list service, without going through HTTP."""

import datetime

import pytest

from autosubmit_api.common.utils import Status
from autosubmit_api.exceptions import ExperimentNotFoundError, InternalError
from autosubmit_api.models.jobs import UNSET, JobCategoryProperty, JobView
from autosubmit_api.models.pagination import Page
from autosubmit_api.models.requests import JobsSearchRequest
from autosubmit_api.repositories.jobs import JobData
from autosubmit_api.services.experiment_jobs import ExperimentJobsService

EXPID = "a003"

# Fields returned by each view, on top of name and status
CONTENT_FIELDS = {
    "priority",
    "section",
    "date",
    "member",
    "chunk",
    "split",
    "splits",
    "out_path_local",
    "err_path_local",
    "out_path_remote",
    "err_path_remote",
}
TIME_FIELDS = {"submit", "start", "finish"}
# The extended view locates the job (section and chunk) and reports its times
EXTENDED_FIELDS = {"section", "chunk"} | TIME_FIELDS


def make_job(name: str, status: int = Status.COMPLETED, chunk: int | None = 1) -> JobData:
    return JobData(
        id=1,
        name=name,
        status=status,
        priority=0,
        section="SIM",
        date=datetime.datetime(2000, 1, 1),
        member="fc0",
        chunk=chunk,
        split=None,
        splits=None,
        out_path_local="out.log",
        err_path_local="err.log",
        out_path_remote="remote.out",
        err_path_remote="remote.err",
    )


class FakeJobsRepository:
    """Returns a fixed job list and records the filters it receives."""

    def __init__(self, jobs: list[JobData]):
        self.jobs = jobs
        self.filters: dict = {}

    def search(self, **filters):
        self.filters = filters
        page: Page = filters.get("page", Page())
        return page.apply(self.jobs), len(self.jobs)


class FakeJobDataRepository:
    """Returns fixed job data records and records the requested job names."""

    def __init__(self, records: list = None, error: Exception | None = None):
        self.records = records or []
        self.error = error
        self.requested_names: list[str] | None = None

    def get_last_job_data_by_name_list(self, job_names: list[str]):
        self.requested_names = job_names
        if self.error is not None:
            raise self.error
        return self.records


class FakeJobData:
    """Stand-in of a record of the job data database.

    That database stores the status name (``COMPLETED``), unlike the jobs
    repository which stores its numeric code.
    """

    def __init__(
        self,
        job_name: str,
        status: str = Status.VALUE_TO_KEY[Status.COMPLETED],
        submit: int = 0,
        start: int = 0,
        finish: int = 0,
    ):
        self.job_name = job_name
        self.status = status
        self.submit = submit
        self.start = start
        self.finish = finish


class FakeJobDataRepositoryFactory:
    """Builds the fake job data repository and remembers if it was used."""

    def __init__(self, records: list = None, error: Exception | None = None):
        self.repository = FakeJobDataRepository(records, error)
        self.calls = 0

    def __call__(self, expid: str) -> FakeJobDataRepository:
        self.calls += 1
        return self.repository


class FailingJobsRepository:
    """Repository that fails the way a broken data source would."""

    def __init__(self, error: Exception):
        self.error = error

    def search(self, **filters):
        raise self.error


@pytest.fixture
def jobs():
    return [make_job("a003_1_SIM"), make_job("a003_2_SIM"), make_job("a003_INI", chunk=None)]


@pytest.fixture
def jobs_repo(jobs):
    return FakeJobsRepository(jobs)


@pytest.fixture
def job_data_factory():
    return FakeJobDataRepositoryFactory()


@pytest.fixture
def service(jobs_repo, job_data_factory):
    return ExperimentJobsService(
        jobs_repo=jobs_repo, expid=EXPID, job_data_repo_factory=job_data_factory
    )


class TestViews:
    def test_quick_view_returns_only_the_name_and_status(self, service, jobs):
        response = service.list_jobs(JobsSearchRequest(view="quick"))

        assert len(response.jobs) == len(jobs)
        for item in response.jobs:
            assert item.model_fields_set == {"name", "status"}

    def test_base_view_returns_the_job_content(self, service):
        response = service.list_jobs(JobsSearchRequest(view="base"))

        item = response.jobs[0]
        assert item.model_fields_set == {"name", "status"} | CONTENT_FIELDS
        assert item.date == "2000-01-01"
        assert item.status == "COMPLETED"

    def test_base_view_does_not_return_the_job_times(self, service):
        response = service.list_jobs(JobsSearchRequest(view="base"))

        for item in response.jobs:
            assert not item.model_fields_set & TIME_FIELDS

    def test_extended_view_returns_the_job_location_and_times(
        self, jobs_repo, job_data_factory
    ):
        job_data_factory.repository.records = [
            FakeJobData(
                job_name="a003_1_SIM",
                submit=1705073838,
                start=1705073840,
                finish=1705073850,
            )
        ]
        service = ExperimentJobsService(
            jobs_repo=jobs_repo, expid=EXPID, job_data_repo_factory=job_data_factory
        )

        response = service.list_jobs(JobsSearchRequest(view="extended"))

        item = response.jobs[0]
        assert item.model_fields_set == {"name", "status"} | EXTENDED_FIELDS
        assert item.section == "SIM"
        assert item.chunk == 1
        assert item.submit is not None
        assert item.start is not None
        assert item.finish is not None
        # Times are ISO datetime strings with timezone information
        datetime.datetime.fromisoformat(item.submit)
        # The job without job data reports unknown times
        assert response.jobs[1].model_fields_set == {"name", "status"} | EXTENDED_FIELDS
        assert response.jobs[1].submit is None

    @pytest.mark.parametrize("view", [JobView.QUICK, JobView.BASE])
    def test_other_views_do_not_read_the_job_data(
        self, jobs_repo, job_data_factory, view: JobView
    ):
        service = ExperimentJobsService(
            jobs_repo=jobs_repo, expid=EXPID, job_data_repo_factory=job_data_factory
        )

        service.list_jobs(JobsSearchRequest(view=view))

        assert job_data_factory.calls == 0

    def test_extended_view_reads_the_job_data_of_the_page_only(
        self, jobs_repo, job_data_factory
    ):
        service = ExperimentJobsService(
            jobs_repo=jobs_repo, expid=EXPID, job_data_repo_factory=job_data_factory
        )

        service.list_jobs(JobsSearchRequest(view="extended", page_size=2))

        assert job_data_factory.calls == 1
        assert job_data_factory.repository.requested_names == [
            "a003_1_SIM",
            "a003_2_SIM",
        ]

    def test_default_view_is_base(self):
        assert JobsSearchRequest().view is JobView.BASE


class TestFilters:
    def test_na_is_translated_to_match_missing_values(self, service, jobs_repo):
        service.list_jobs(JobsSearchRequest(date="NA", chunk="NA"))

        assert jobs_repo.filters["date"] is None
        assert jobs_repo.filters["chunk"] is None

    def test_omitted_filters_are_not_applied(self, service, jobs_repo):
        service.list_jobs(JobsSearchRequest(member="fc0"))

        assert jobs_repo.filters["member"] == "fc0"
        assert jobs_repo.filters["job_name"] is UNSET
        assert jobs_repo.filters["date"] is UNSET
        assert jobs_repo.filters["section"] is UNSET
        assert jobs_repo.filters["chunk"] is UNSET

    @pytest.mark.parametrize("job_name", [None, ""])
    def test_an_absent_or_empty_job_name_is_not_a_filter(
        self, service, jobs_repo, job_name: str | None
    ):
        """A job always has a name, so the name filter has no empty value."""
        response = service.list_jobs(JobsSearchRequest(job_name=job_name))

        assert jobs_repo.filters["job_name"] is UNSET
        assert "job_name" not in response.filters.model_fields_set
        assert response.filters.model_dump(exclude_unset=True) == {}

    def test_job_name_and_status_are_forwarded(self, service, jobs_repo):
        service.list_jobs(JobsSearchRequest(job_name="*SIM", status="COMPLETED"))

        assert jobs_repo.filters["job_name"] == "*SIM"
        assert jobs_repo.filters["status"] == "COMPLETED"

    def test_the_response_reports_the_filters_that_were_applied(self, service):
        response = service.list_jobs(
            JobsSearchRequest(date="2000-01-01", member="fc0", chunk="NA")
        )

        assert response.filters.model_fields_set == {"date", "member", "chunk"}
        assert response.filters.date == "2000-01-01"
        assert response.filters.member == "fc0"
        # A filter for the jobs without a value is reported as it was asked for
        assert response.filters.chunk == "NA"

    def test_the_response_does_not_report_the_filters_that_were_not_used(
        self, service
    ):
        response = service.list_jobs(JobsSearchRequest(member="fc0"))

        assert response.filters.model_fields_set == {"member"}
        assert response.filters.model_dump(exclude_unset=True) == {"member": "fc0"}

    def test_the_response_reports_no_filters_when_none_was_used(self, service):
        response = service.list_jobs(JobsSearchRequest())

        assert response.filters.model_fields_set == set()

    def test_the_request_can_filter_by_every_job_category_property(self):
        """The filters echo is built from the job category properties."""
        for prop in JobCategoryProperty:
            assert prop.value in JobsSearchRequest.model_fields


class TestPagination:
    def test_unpaginated_by_default(self, service, jobs_repo):
        response = service.list_jobs(JobsSearchRequest())

        assert jobs_repo.filters["page"] == Page()
        assert response.pagination.page == 1
        assert response.pagination.page_size is None
        assert response.pagination.total_pages == 1
        assert response.pagination.page_items == 3
        assert response.pagination.total_items == 3

    def test_page_is_forwarded_to_the_repository(self, service, jobs_repo):
        service.list_jobs(JobsSearchRequest(page=2, page_size=2))

        assert jobs_repo.filters["page"] == Page(limit=2, offset=2)

    def test_envelope_describes_the_requested_page(self, service):
        response = service.list_jobs(JobsSearchRequest(page=2, page_size=2))

        assert response.pagination.page == 2
        assert response.pagination.page_size == 2
        assert response.pagination.total_pages == 2
        assert response.pagination.page_items == 1
        assert response.pagination.total_items == 3


class TestFailures:
    def test_job_list_failure_is_reported_as_an_internal_error(self):
        service = ExperimentJobsService(
            jobs_repo=FailingJobsRepository(ValueError("corrupted pkl")), expid=EXPID
        )

        with pytest.raises(InternalError, match="Error while reading the job list") as exc:
            service.list_jobs(JobsSearchRequest())

        # The original failure is kept as the cause for the logs
        assert isinstance(exc.value.__cause__, ValueError)

    def test_job_data_failure_is_reported_as_an_internal_error(self, jobs_repo):
        factory = FakeJobDataRepositoryFactory(error=OSError("cannot open database"))
        service = ExperimentJobsService(
            jobs_repo=jobs_repo, expid=EXPID, job_data_repo_factory=factory
        )

        with pytest.raises(
            InternalError, match="Error while reading the last job data"
        ) as exc:
            service.list_jobs(JobsSearchRequest(view="extended"))

        assert isinstance(exc.value.__cause__, OSError)

    def test_domain_errors_are_not_translated(self):
        """A missing experiment must stay a 404 instead of becoming a 500."""
        service = ExperimentJobsService(
            jobs_repo=FailingJobsRepository(ExperimentNotFoundError(EXPID)),
            expid=EXPID,
        )

        with pytest.raises(ExperimentNotFoundError):
            service.list_jobs(JobsSearchRequest())
