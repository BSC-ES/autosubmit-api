from typing import Annotated

from pydantic import BaseModel, Field


class RouteInfo(BaseModel):
    path: Annotated[
        str, Field(description="Path of the route", json_schema_extra={"example": "/"})
    ]
    methods: list[
        Annotated[
            str, Field(description="HTTP methods", json_schema_extra={"example": "GET"})
        ]
    ]


class PaginationInfo(BaseModel):
    page: Annotated[
        int, Field(1, ge=1, description="Page number", json_schema_extra={"example": 1})
    ]
    page_size: Annotated[
        int | None,
        Field(
            description="Number of items per page", json_schema_extra={"example": 12}
        ),
    ]
    total_pages: Annotated[
        int,
        Field(
            1,
            ge=1,
            description="Total number of pages",
            json_schema_extra={"example": 1},
        ),
    ]
    page_items: Annotated[
        int,
        Field(
            ge=0,
            description="Number of items in the current page",
            json_schema_extra={"example": 1},
        ),
    ]
    total_items: Annotated[
        int,
        Field(
            ge=0, description="Total number of items", json_schema_extra={"example": 1}
        ),
    ]
