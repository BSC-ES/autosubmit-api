from typing import List, Optional
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
    user: Optional[str]


class LoginResponse(AuthResponse):
    token: Optional[str]
    message: Optional[str]


class ExperimentRunsResponse(BaseModel):
    runs: List[BaseExperimentRun]


class RoutesResponse(BaseModel):
    routes: List[RouteInfo]


class ExperimentsSearchResponse(BaseModel):
    experiments: List[ExperimentSearchItem]
    pagination: PaginationInfo


class ExperimentJobsResponse(BaseModel):
    jobs: List[PklJobModel]


class ExperimentFSConfigResponse(BaseModel):
    config: dict


class ExperimentRunConfigResponse(BaseModel):
    run_id: Optional[int]
    config: dict


class ExperimentWrappersResponse(BaseModel):
    wrappers: List[BaseExperimentWrapper]


class PreferredUsernameResponse(BaseModel):
    user_id: str
    preferred_username: str
    created: str
    modified: str
