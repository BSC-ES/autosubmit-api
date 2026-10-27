from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Annotated, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


@dataclass(frozen=True)
class Page:
    """
    The page of a result that is being requested.

    A page is either unbounded (return everything) or bounded (``limit`` items
    starting at ``offset``).

    - unbounded: ``limit`` is ``None`` and ``offset`` is ``0``
    - bounded: ``limit`` is 1 or greater and ``offset`` is not negative
    """

    limit: int | None = None
    offset: int = 0

    def __post_init__(self) -> None:
        if self.limit is None:
            if self.offset != 0:
                raise ValueError("An unbounded page cannot skip items")
        elif self.limit < 1:
            raise ValueError("The limit of a page must be 1 or greater")
        elif self.offset < 0:
            raise ValueError("The offset of a page cannot be negative")

    @classmethod
    def of(cls, page: int | None = None, page_size: int | None = None) -> Page:
        """Builds the page with a ``page``/``page_size`` pair.

        A missing or non-positive ``page_size`` means "do not paginate".
        The page number is ignored in that case.
        """
        if page_size is None or page_size <= 0:
            return UNPAGINATED
        return cls(limit=page_size, offset=(max(page or 1, 1) - 1) * page_size)

    @property
    def is_paginated(self) -> bool:
        """Whether a maximum number of items was requested."""
        return self.limit is not None

    @property
    def number(self) -> int:
        """The number of this page, or 1 when there is no pagination."""
        if self.limit is None:
            return 1
        return self.offset // self.limit + 1

    def apply(self, items: Sequence[T]) -> list[T]:
        """Returns the items covered by this page."""
        if self.limit is None:
            return list(items)
        return list(items[self.offset : self.offset + self.limit])


UNPAGINATED = Page()


class PaginationInfo(BaseModel):
    """Description of the page of a result set that is being returned."""

    page: Annotated[int, Field(1, ge=1, description="Page number", json_schema_extra={"example": 1})]
    page_size: Annotated[
        int | None, Field(ge=1, description="Number of items per page", json_schema_extra={"example": 12})
    ]
    total_pages: Annotated[
        int, Field(1, ge=1, description="Total number of pages", json_schema_extra={"example": 1})
    ]
    page_items: Annotated[
        int, Field(ge=0, description="Number of items in the current page", json_schema_extra={"example": 1})
    ]
    total_items: Annotated[
        int, Field(ge=0, description="Total number of items", json_schema_extra={"example": 1})
    ]

    @classmethod
    def from_page(
        cls, page: Page, *, total_items: int, page_items: int
    ) -> PaginationInfo:
        """Builds the wrapper of ``page`` out of the totals of the query."""
        total_pages = 1
        if page.limit is not None:
            total_pages = max(1, math.ceil(total_items / page.limit))
        return cls(
            page=page.number,
            page_size=page.limit,
            total_pages=total_pages,
            page_items=page_items,
            total_items=total_items,
        )
