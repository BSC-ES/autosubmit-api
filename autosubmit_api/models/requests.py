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
