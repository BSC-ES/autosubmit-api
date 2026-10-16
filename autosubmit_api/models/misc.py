from typing import Annotated

from pydantic import BaseModel, Field


class RouteInfo(BaseModel):
    path: Annotated[str, Field(description="Path of the route", example="/")]
    methods: list[Annotated[str, Field(description="HTTP methods", example="GET")]]
