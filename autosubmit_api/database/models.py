from typing import Optional
from pydantic import BaseModel


class Experiment(BaseModel):
    id: int
    name: str
    description: str
    autosubmit_version: Optional[str] = None
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
