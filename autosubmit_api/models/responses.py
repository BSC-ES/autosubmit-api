from pydantic import BaseModel

from autosubmit_api.database.models import PklJobModel
from autosubmit_api.models.experiment import (
    BaseExperimentRun,
    BaseExperimentWrapper,
    ExperimentSearchItem,
)
from autosubmit_api.models.misc import PaginationInfo, RouteInfo


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


class ExperimentJobsResponse(BaseModel):
    jobs: list[PklJobModel]


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


class ExperimentJobsCategoryTreeResponse(BaseModel):
    ...
