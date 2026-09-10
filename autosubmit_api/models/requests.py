from typing import Annotated, Literal, Optional
from pydantic import BaseModel, Field

PAGINATION_LIMIT_DEFAULT = 12


class ExperimentsSearchRequest(BaseModel):
    query: Optional[str] = None
    only_active: bool = True
    owner: Optional[str] = None
    exp_type: Optional[Literal["test", "operational", "experiment"]] = None
    autosubmit_version: Optional[str] = None
    hpc: Optional[str] = None

    order_by: Optional[Literal["expid", "created", "description"]] = None
    order_desc: bool = True

    page: Annotated[int, Field(ge=1, description="Page number", example=1)] = 1
    page_size: int = PAGINATION_LIMIT_DEFAULT


class JobsSearchRequest(BaseModel):
    view: Annotated[
        Literal["quick", "base", "extended"],
        Field(description="View type", example="base"),
    ] = "base"
    date: Annotated[
        str | Literal["NA"] | None,
        Field(description="Filter by job date", example="2026-12-25"),
    ] = None
    member: Annotated[
        str | Literal["NA"] | None,
        Field(description="Filter by job member", example="fc0"),
    ] = None
    section: Annotated[
        str | Literal["NA"] | None,
        Field(description="Filter by job section", example="SIM"),
    ] = None
    chunk: Annotated[
        int | Literal["NA"] | None, Field(description="Filter by job chunk", example=1)
    ] = None


class PreferredUsernameRequest(BaseModel):
    preferred_username: str = Field(
        ..., min_length=1, description="Preferred Linux username"
    )
