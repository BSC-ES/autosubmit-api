from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator

from autosubmit_api.common.utils import Status

PAGINATION_LIMIT_DEFAULT = 12
PAGINATION_LIMIT_MAX = 1000


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

    @field_validator("status")
    @classmethod
    def _check_status(cls, status: str | None) -> str | None:
        if status is not None and status not in Status.STRING_TO_CODE:
            raise ValueError(
                "Invalid job status. Allowed values: "
                f"{', '.join(sorted(Status.STRING_TO_CODE))}"
            )
        return status

    page: Annotated[int, Field(ge=1, description="Page number", example=1)] = 1
    page_size: Annotated[
        int | None,
        Field(
            ge=1,
            le=PAGINATION_LIMIT_MAX,
            description="Page size. Omit to disable pagination",
            example=12,
        ),
    ] = None


class PreferredUsernameRequest(BaseModel):
    preferred_username: str = Field(
        ..., min_length=1, description="Preferred Linux username"
    )
