from dataclasses import FrozenInstanceError

import pytest

from autosubmit_api.models.pagination import UNPAGINATED, Page, PaginationInfo


class TestPageOf:
    def test_no_page_size_is_unpaginated(self):
        page = Page.of(page=1, page_size=None)

        assert page == UNPAGINATED
        assert page.limit is None
        assert page.offset == 0
        assert page.is_paginated is False

    @pytest.mark.parametrize("page_size", [0, -1])
    def test_non_positive_page_size_is_unpaginated(self, page_size: int):
        """The API expresses an unbounded page size with a non-positive value."""
        page = Page.of(page=4, page_size=page_size)

        assert page == UNPAGINATED

    @pytest.mark.parametrize(
        "page, page_size, expected_limit, expected_offset",
        [
            (1, 12, 12, 0),
            (2, 12, 12, 12),
            (3, 10, 10, 20),
            (None, 5, 5, 0),
            (0, 5, 5, 0),
        ],
    )
    def test_page_is_translated_to_limit_and_offset(
        self,
        page: int | None,
        page_size: int,
        expected_limit: int,
        expected_offset: int,
    ):
        result = Page.of(page=page, page_size=page_size)

        assert result.limit == expected_limit
        assert result.offset == expected_offset
        assert result.is_paginated is True


class TestPageNumber:
    @pytest.mark.parametrize(
        "page, expected_number",
        [
            (Page(limit=10), 1),
            (Page(limit=10, offset=10), 2),
            (Page(limit=10, offset=25), 3),
        ],
    )
    def test_number_of_a_paginated_result(self, page: Page, expected_number: int):
        assert page.number == expected_number

    def test_number_is_one_without_pagination(self):
        assert UNPAGINATED.number == 1

    def test_page_is_immutable(self):
        with pytest.raises(FrozenInstanceError):
            Page(limit=10).limit = 20  # type: ignore[misc]


class TestPageInvariants:
    """A page that is neither bounded nor tight has no meaning, so it is rejected."""

    @pytest.mark.parametrize("limit", [0, -1])
    def test_a_bounded_page_needs_at_least_one_item(self, limit: int):
        with pytest.raises(ValueError, match="limit of a page must be 1 or greater"):
            Page(limit=limit)

    def test_an_unbounded_page_cannot_skip_items(self):
        with pytest.raises(ValueError, match="cannot skip items"):
            Page(offset=30)

    def test_a_bounded_page_cannot_skip_backwards(self):
        with pytest.raises(ValueError, match="offset of a page cannot be negative"):
            Page(limit=10, offset=-1)


class TestPageApply:
    def test_unpaginated_returns_every_item(self):
        assert UNPAGINATED.apply([1, 2, 3]) == [1, 2, 3]

    @pytest.mark.parametrize(
        "limit, offset, expected",
        [
            (2, 0, [1, 2]),
            (2, 2, [3, 4]),
            (2, 3, [4]),
            (10, 0, [1, 2, 3, 4]),
            (5, 10, []),
        ],
    )
    def test_paginated_slice(self, limit: int, offset: int, expected: list):
        items = [1, 2, 3, 4]

        assert Page(limit=limit, offset=offset).apply(items) == expected


class TestPaginationInfo:
    def test_bounded_page(self):
        info = PaginationInfo.from_page(
            Page(limit=10, offset=20), total_items=25, page_items=5
        )

        assert isinstance(info, PaginationInfo)
        assert info.page == 3
        assert info.page_size == 10
        assert info.total_pages == 3
        assert info.page_items == 5
        assert info.total_items == 25

    def test_unbounded_page_fits_in_one_page(self):
        info = PaginationInfo.from_page(UNPAGINATED, total_items=25, page_items=25)

        assert info.page == 1
        assert info.page_size is None
        assert info.total_pages == 1

    @pytest.mark.parametrize("total_items", [0, 1])
    def test_at_least_one_page(self, total_items: int):
        """``total_pages`` is always at least 1, even without results."""
        info = PaginationInfo.from_page(
            Page(limit=10), total_items=total_items, page_items=0
        )

        assert info.total_pages == 1

    @pytest.mark.parametrize(
        "total_items, limit, expected_total_pages",
        [(20, 10, 2), (21, 10, 3), (9, 10, 1), (100, 1000, 1)],
    )
    def test_total_pages_is_rounded_up(
        self, total_items: int, limit: int, expected_total_pages: int
    ):
        info = PaginationInfo.from_page(
            Page(limit=limit), total_items=total_items, page_items=limit
        )

        assert info.total_pages == expected_total_pages

    def test_page_beyond_the_last_one_is_reported_as_requested(self):
        """The envelope describes the page that was asked for, empty if out of range."""
        info = PaginationInfo.from_page(
            Page.of(page=5, page_size=100), total_items=8, page_items=0
        )

        assert info.page == 5
        assert info.page_size == 100
        assert info.total_pages == 1
        assert info.page_items == 0
        assert info.total_items == 8
