from __future__ import annotations

import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel

from autosubmit_api.common import utils as common_utils


class Unset:
    """Sentinel for an argument that was not provided.

    The job filters use it to distinguish between omitted
    filters (``UNSET``: do not filter by this property) from a
    ``None``value (``None``: filter for the jobs where the property is not set).
    """

    __slots__ = ()

    def __repr__(self) -> str:
        return "UNSET"


UNSET = Unset()


class JobCategoryProperty(str, Enum):
    """Properties used to filter jobs."""

    JOB_NAME = "job_name"
    DATE = "date"
    MEMBER = "member"
    SECTION = "section"
    CHUNK = "chunk"
    STATUS = "status"


class JobView(str, Enum):
    """
    Content returned for each job of an experiment.

    - `QUICK`` is the minimum a job list needs: the name and the status of each job.
    - ``BASE`` is the content of the job list entry
    - ``EXTENDED`` reports the execution times of the job, necessary for the job list of the tree view.
    """

    QUICK = "quick"
    BASE = "base"
    EXTENDED = "extended"


# Order in which the job properties are shown in the jobs category tree and used as filters.
JOBS_CATEGORY_HIERARCHY: tuple[JobCategoryProperty, ...] = (
    JobCategoryProperty.DATE,
    JobCategoryProperty.MEMBER,
    JobCategoryProperty.SECTION,
    JobCategoryProperty.STATUS,
)

MISSING_CATEGORY_VALUE = "NA"

UNKNOWN_STATUS = common_utils.Status.VALUE_TO_KEY[common_utils.Status.UNKNOWN]

DATE_FORMAT = "%Y-%m-%d"


def status_name(status: int | str | None) -> str:
    """
    Gets the name of a job status.

    We have two type of status encodings.
    - The pkl file stores the numeric code of the status (``5``).
    - The job data database stores its name (``COMPLETED``).
    Both representations are normalized to the name.
    Unknown values are kept as UNKNOWN, so they are all equal
    to an identical status.
    """
    if status is None:
        return UNKNOWN_STATUS
    if isinstance(status, int):
        return common_utils.Status.VALUE_TO_KEY.get(status, UNKNOWN_STATUS)
    return status


class JobData(BaseModel):
    """A single job of the experiment job list."""

    id: int | None
    name: str
    status: int | None = common_utils.Status.UNKNOWN
    priority: int
    section: str
    date: datetime.datetime | None
    member: str | None
    chunk: int | None
    split: int | None
    splits: int | None
    out_path_local: str | None
    err_path_local: str | None
    out_path_remote: str | None
    err_path_remote: str | None


def format_category_value(prop: JobCategoryProperty, value: Any) -> Any:
    """Normalizes a raw job property to be returned by the API.

    The pkl and the SQL backends store the same information differently.
    Normalization is needed to return a consistent representation.

    - ``date``: ``YYYY-MM-DD`` string.
    - ``status``: status name (e.g. ``COMPLETED``) instead of its numeric code.
    - missing values: ``NA`` (``UNKNOWN`` for status).
    """
    prop = JobCategoryProperty(prop)

    if value is None:
        if prop is JobCategoryProperty.STATUS:
            return status_name(value)
        return MISSING_CATEGORY_VALUE

    if prop is JobCategoryProperty.STATUS:
        return status_name(value)

    if prop is JobCategoryProperty.DATE:
        if isinstance(value, datetime.datetime):
            return value.strftime(DATE_FORMAT)
        if isinstance(value, str):
            try:
                return datetime.datetime.fromisoformat(value).strftime(DATE_FORMAT)
            except ValueError:
                return value

    return value


def normalize_filter_value(value: Any) -> Any:
    """
    Normalizes a job filter value received from the API.

    ``NA`` is the value exposed by the category tree for the jobs without a
    value, so it is translated to ``None`` to make it usable as a filter by both
    backends.
    """
    if value == MISSING_CATEGORY_VALUE:
        return None
    return value
