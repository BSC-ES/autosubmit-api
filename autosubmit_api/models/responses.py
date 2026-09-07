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
