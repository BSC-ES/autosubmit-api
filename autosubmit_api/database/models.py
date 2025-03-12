import datetime
from typing import Any, Optional
from pydantic import BaseModel
from autosubmit_api.common import utils as common_utils


class BaseExperimentModel(BaseModel):
    id: int
    name: str
    description: str
    autosubmit_version: Optional[str] = None


class ExperimentModel(BaseExperimentModel):
    user: Optional[str] = None
    created: Optional[str] = None
    model: Optional[str] = None
    branch: Optional[str] = None
    hpc: Optional[str] = None
    status: Optional[str] = None
    modified: Optional[str] = None
    total_jobs: Optional[int] = None
    completed_jobs: Optional[int] = None
    wrapper: Optional[str] = None


class BaseJobModel(BaseModel):
    name: str
    status: Optional[int] = common_utils.Status.UNKNOWN


class PklJobModel(BaseJobModel):
    name: str
    id: Any
    status: Optional[int] = common_utils.Status.UNKNOWN
    priority: int
    section: str
    date: Optional[datetime.datetime]
    member: Optional[str]
    chunk: Optional[int]
    out_path_local: Optional[str]
    err_path_local: Optional[str]
    out_path_remote: Optional[str]
    err_path_remote: Optional[str]
    wrapper_type: Optional[str]
