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

