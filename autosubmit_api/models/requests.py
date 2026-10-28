import re
from typing import Annotated, Literal

from pydantic import BaseModel, Field, field_validator

from autosubmit_api.common.utils import Status
from autosubmit_api.models.jobs import MISSING_CATEGORY_VALUE, JobView

PAGINATION_LIMIT_DEFAULT = 12
PAGINATION_LIMIT_MAX = 1000

DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class ExperimentsSearchRequest(BaseModel):
    query: str | None = None
    only_active: bool = True
    owner: str | None = None
    exp_type: Literal["test", "operational", "experiment"] | None = None
    autosubmit_version: str | None = None
    hpc: str | None = None

    order_by: Literal["expid", "created", "description"] | None = None
    order_desc: bool = False

    page: Annotated[
        int, Field(ge=1, description="Page number", json_schema_extra={"example": 1})
    ] = 1
    page_size: int = PAGINATION_LIMIT_DEFAULT


class JobsSearchRequest(BaseModel):
    view: Annotated[JobView,
        Field(description="View type", json_schema_extra={"example": "base"}),] = (
        JobView.BASE
    )
    job_name: Annotated[
        str | None,
        Field(
            description="Job name. Wildcard supported",
            json_schema_extra={"example": "example_job_*"},
        ),
    ] = None
    status: Annotated[
        str | None,
        Field(description="Job status", json_schema_extra={"example": "COMPLETED"}),
    ] = None
    date: Annotated[
        str | None,
        Field(
            description=(
                "Filter by job date in YYYY-MM-DD format. Use "
                f"'{MISSING_CATEGORY_VALUE}' for the jobs without a date"
            ),
            json_schema_extra={"example": "2000-01-01"},
        ),
    ] = None
    member: Annotated[
        str | None,
        Field(
            description=(
                "Filter by job member. Use "
                f"'{MISSING_CATEGORY_VALUE}' for the jobs without a member"
            ),
            json_schema_extra={"example": "fc0"},
        ),
    ] = None
    section: Annotated[
        str | None,
        Field(
            description="Filter by job section",
            json_schema_extra={"example": "SIM"},
        ),
    ] = None
    chunk: Annotated[
        int | Literal["NA"] | None,
        Field(
            description=(
                "Filter by job chunk. Use "
                f"'{MISSING_CATEGORY_VALUE}' for the jobs without a chunk"
            ),
            json_schema_extra={"example": 1},
        ),
    ] = None

    @field_validator("job_name")
    @classmethod
    def _check_job_name(cls, job_name: str | None) -> str | None:
        """A job always has a name, so an empty name is not a filter."""
        return job_name or None

    @field_validator("status")
    @classmethod
    def _check_status(cls, status: str | None) -> str | None:
        if status is not None and status not in Status.STRING_TO_CODE:
            raise ValueError(
                "Invalid job status. Allowed values: "
                f"{', '.join(sorted(Status.STRING_TO_CODE))}"
            )
        return status

    @field_validator("date")
    @classmethod
    def _check_date(cls, date: str | None) -> str | None:
        if date is None or date == MISSING_CATEGORY_VALUE:
            return date
        if not DATE_PATTERN.match(date):
            raise ValueError(
                f"Invalid date. Expected YYYY-MM-DD or '{MISSING_CATEGORY_VALUE}'"
            )
        return date

    page: Annotated[
        int, Field(ge=1, description="Page number", json_schema_extra={"example": 1})
    ] = 1
    page_size: Annotated[
        int | None,
        Field(
            ge=1,
            le=PAGINATION_LIMIT_MAX,
            description="Page size. Omit to disable pagination",
            json_schema_extra={"example": 12},
        ),
    ] = None


class PreferredUsernameRequest(BaseModel):
    preferred_username: str = Field(
        ..., min_length=1, description="Preferred Linux username"
    )
