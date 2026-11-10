from typing import Literal

from pydantic import BaseModel, RootModel

from autosubmit_api.models.experiment import (
    BaseExperimentRun,
    BaseExperimentWrapper,
    ExperimentSearchItem,
)
from autosubmit_api.models.jobs import JobCategoryProperty
from autosubmit_api.models.misc import RouteInfo
from autosubmit_api.models.pagination import PaginationInfo


class AuthResponse(BaseModel):
    authenticated: bool
    user: str | None


class LoginResponse(AuthResponse):
    token: str | None
    message: str | None


class ExperimentRunsResponse(BaseModel):
    runs: list[BaseExperimentRun]


class RoutesResponse(BaseModel):
    routes: list[RouteInfo]


class ExperimentsSearchResponse(BaseModel):
    experiments: list[ExperimentSearchItem]
    pagination: PaginationInfo


class ExperimentJobItem(BaseModel):
    """A job of the job list.

    Depending on the view, it contains different information about the job.
    """

    # ``quick`` view: minimum content of the job list
    name: str
    status: str
    # ``base`` view: content of the job list entry
    priority: int | None = None
    section: str | None = None  # Also returned by the ``extended`` view
    date: str | None = None
    member: str | None = None
    chunk: int | None = None  # Also returned by the ``extended`` view
    wrapper: str | None = None  # Also returned by the ``extended`` view
    split: int | None = None
    splits: int | None = None
    out_path_local: str | None = None
    err_path_local: str | None = None
    out_path_remote: str | None = None
    err_path_remote: str | None = None
    # ``extended`` view: execution times of the job
    submit: str | None = None
    start: str | None = None
    finish: str | None = None


class ExperimentJobsFilters(BaseModel):
    """Filters applied to the job list."""

    job_name: str | None = None
    status: str | None = None
    date: str | None = None
    member: str | None = None
    section: str | None = None
    wrapper: str | None = None
    chunk: int | Literal["NA"] | None = None


class ExperimentJobsResponse(BaseModel):
    jobs: list[ExperimentJobItem]
    filters: ExperimentJobsFilters
    pagination: PaginationInfo


class ExperimentFSConfigResponse(BaseModel):
    config: dict


class ExperimentRunConfigResponse(BaseModel):
    run_id: int | None
    config: dict


class ExperimentWrappersResponse(BaseModel):
    wrappers: list[BaseExperimentWrapper]


class ExperimentEtaResponse(BaseModel):
    eta_seconds: float | None
    chunks_total: int | None
    chunks_remaining: int | None
    avg_runtime_per_chunk_seconds: float | None


class PreferredUsernameResponse(BaseModel):
    user_id: str
    preferred_username: str
    created: str
    modified: str


class JobDetailResponse(BaseModel):
    # From pkl
    name: str
    status: str
    section: str | None = None
    date: str | None = None
    member: str | None = None
    chunk: int | None = None
    split: int | None = None
    splits: int | None = None
    out_path_local: str | None = None
    err_path_local: str | None = None
    # From config
    chunk_size: int | None = None
    chunk_unit: str | None = None
    platform: str | None = None
    # From historical DB
    remote_id: int | None = None
    qos: str | None = None
    workflow_commit: str | None = None
    processors: int | None = None  # Requested ncpus
    submit: str | None = None
    start: str | None = None
    finish: str | None = None
    wallclock: str | None = None
    # Wrapper data
    last_wrapper: str | None = None


class ExperimentJobsCategoryTree(
    RootModel[dict[str, "ExperimentJobsCategoryTree | int"]]
):
    """Counters of the jobs category tree, nested one level per filtered property."""


class ExperimentJobsCategoryTreeResponse(BaseModel):
    """The job counters of an experiment, grouped in two trees.

    - ``category_tree`` counts every job of the experiment.
    - ``wrapper_tree`` only counts the jobs that a wrapper holds.
    """

    properties_hierarchy: list[JobCategoryProperty]
    """Properties of each level of ``category_tree``, from the root to the leaves."""

    category_tree: ExperimentJobsCategoryTree
    """Counters of every job, by date, member, section and status."""

    wrapper_hierarchy: list[JobCategoryProperty] | None = None
    """Properties of each level of ``wrapper_tree``, ``None`` if there is no packaging."""

    wrapper_tree: ExperimentJobsCategoryTree | None = None
    """Counters of the packaged jobs, by wrapper and status.

    The jobs that no wrapper packages are not part of the packaging, so they are
    not counted here. The whole tree is ``None`` when no job is packaged.
    """
