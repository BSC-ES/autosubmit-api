from typing import Annotated, Literal

from pydantic import BaseModel, Field

PAGINATION_LIMIT_DEFAULT = 12


class ExperimentsSearchRequest(BaseModel):
    query: str | None = None
    only_active: bool = True
    owner: str | None = None
    exp_type: Literal["test", "operational", "experiment"] | None = None
    autosubmit_version: str | None = None
    hpc: str | None = None

    order_by: Literal["expid", "created", "description"] | None = None
    order_desc: bool = True

    page: Annotated[int, Field(ge=1, description="Page number", example=1)] = 1
    page_size: int = PAGINATION_LIMIT_DEFAULT


class JobsSearchRequest(BaseModel):
    view: Annotated[
        Literal["quick", "base"], Field(description="View type", example="base")
    ] = "base"
    job_name: Annotated[
        str | None,
        Field(description="Job name. Wildcard supported", example="example_job_*"),
    ] = None
    status: Annotated[
        str | None, Field(description="Job status", example="COMPLETED")
    ] = None

    page: Annotated[int, Field(ge=1, description="Page number", example=1)] = 1
    page_size: Annotated[
        int | None,
        Field(ge=1, description="Page size. Omit to disable pagination", example=12),
    ] = None


class PreferredUsernameRequest(BaseModel):
    preferred_username: str = Field(
        ..., min_length=1, description="Preferred Linux username"
    )
