"""Tests of the job domain vocabulary."""

import datetime

import pytest

from autosubmit_api.common.utils import Status
from autosubmit_api.models.jobs import (
    MISSING_CATEGORY_VALUE,
    UNKNOWN_STATUS,
    JobCategoryProperty,
    format_category_value,
    normalize_filter_value,
    status_name,
)


class TestStatusName:
    @pytest.mark.parametrize(
        "code, expected",
        [
            (Status.COMPLETED, "COMPLETED"),
            (Status.WAITING, "WAITING"),
            (Status.FAILED, "FAILED"),
            (Status.UNKNOWN, "UNKNOWN"),
        ],
    )
    def test_numeric_code_becomes_its_name(self, code: int, expected: str):
        assert status_name(code) == expected

    @pytest.mark.parametrize("name", ["COMPLETED", "WAITING", "SUSPICIOUS"])
    def test_name_is_kept_as_it_is(self, name: str):
        assert status_name(name) == name

    def test_missing_status_is_unknown(self):
        assert status_name(None) == UNKNOWN_STATUS

    def test_unknown_code_is_reported_as_unknown(self):
        assert status_name(1234) == UNKNOWN_STATUS

    def test_both_representations_are_comparable(self):
        """The job list stores codes and the job data database names."""
        assert status_name(Status.COMPLETED) == status_name("COMPLETED")


class TestFormatCategoryValue:
    @pytest.mark.parametrize(
        "value, expected",
        [
            (Status.COMPLETED, "COMPLETED"),
            ("COMPLETED", "COMPLETED"),
            (None, UNKNOWN_STATUS),
        ],
    )
    def test_status_is_normalized_to_the_name(self, value, expected: str):
        assert format_category_value(JobCategoryProperty.STATUS, value) == expected

    @pytest.mark.parametrize(
        "value, expected",
        [
            (datetime.datetime(2000, 1, 1, 10, 30), "2000-01-01"),
            ("2000-01-01T00:00:00", "2000-01-01"),
            ("2000-01-01", "2000-01-01"),
            (None, MISSING_CATEGORY_VALUE),
        ],
    )
    def test_date_is_reduced_to_the_day(self, value, expected: str):
        assert format_category_value(JobCategoryProperty.DATE, value) == expected

    @pytest.mark.parametrize("prop", [JobCategoryProperty.MEMBER, JobCategoryProperty.SECTION])
    def test_other_properties_are_kept_as_they_are(self, prop: JobCategoryProperty):
        assert format_category_value(prop, "fc0") == "fc0"

    @pytest.mark.parametrize(
        "prop",
        [JobCategoryProperty.MEMBER, JobCategoryProperty.SECTION, JobCategoryProperty.CHUNK],
    )
    def test_missing_values_are_reported_as_na(self, prop: JobCategoryProperty):
        assert format_category_value(prop, None) == MISSING_CATEGORY_VALUE


class TestNormalizeFilterValue:
    def test_na_means_match_missing_values(self):
        assert normalize_filter_value(MISSING_CATEGORY_VALUE) is None

    @pytest.mark.parametrize("value", ["2000-01-01", "fc0", 1, None])
    def test_other_values_are_kept(self, value):
        assert normalize_filter_value(value) == value
