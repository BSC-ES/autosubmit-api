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


# TODO: Use ``sentinel()`` when upgrading to Python 3.15, https://docs.python.org/3.15/builtins/functions.html#sentinel
UNSET = Unset()


class JobCategoryProperty(str, Enum):
    """Properties used to filter jobs."""

    JOB_NAME = "job_name"
    """Name of the job."""

    DATE = "date"
    """Start date the job belongs to."""

    MEMBER = "member"
    """Member the job belongs to."""

    SECTION = "section"
    """Section the job belongs to."""

    CHUNK = "chunk"
    """Chunk the job belongs to."""

    STATUS = "status"
    """Current status of the job."""


class JobView(str, Enum):
    """Content returned for each job of an experiment."""

    QUICK = "quick"
    """Minimal information the job list needs: the name and the status of each job."""

    BASE = "base"
    """Content of the job list entry."""

    EXTENDED = "extended"
    """Reports where the job is.
    
    Its section, how the job is grouped, and whether it runs within a chunk and its execution times,
    necessary for the job list of the tree view.
    """


JOBS_CATEGORY_HIERARCHY: tuple[JobCategoryProperty, ...] = (
    JobCategoryProperty.DATE,
    JobCategoryProperty.MEMBER,
    JobCategoryProperty.SECTION,
    JobCategoryProperty.STATUS,
)
"""Order in which the job properties are shown in teh jobs category tree. Used as filters."""

MISSING_CATEGORY_VALUE = "NA"
"""Default value for a job property that is not set."""

UNKNOWN_STATUS = common_utils.Status.VALUE_TO_KEY[common_utils.Status.UNKNOWN]
"""Default value for a job status that is not set."""

DATE_FORMAT = "%Y-%m-%d"
"""Format used to represent a job date in the API."""


def status_name(status: int | str | None) -> str:
    """Gets the name of a job status.

    We have two type of status encodings.
    - The pkl file stores the numeric code of the status (``5``).
    - The job data database stores its name (``COMPLETED``).
    Both representations are normalized to the name.
    Unknown values are kept as UNKNOWN, so they are all equal
    to an identical status.

    :param status: The job status, either as a numeric code or as a name.
    :return: The name of the job status.
    """
    if status is None:
        return UNKNOWN_STATUS
    if isinstance(status, int):
        return common_utils.Status.VALUE_TO_KEY.get(status, UNKNOWN_STATUS)
    return status


class JobData(BaseModel):
    """A single job of the experiment job list."""

    id: int | None
    """Unique identifier of the job."""

    name: str
    """Name of the job."""

    status: int | None = common_utils.Status.UNKNOWN
    """Current status of the job. Defaults to UNKNOWN if not set."""

    priority: int
    """Order in which the job is executed within its section. Lower values are executed first."""

    section: str
    """Section the job belongs to."""

    date: datetime.datetime | None
    """Start date the job belongs to."""

    member: str | None
    """Member the job belongs to."""

    chunk: int | None
    """Chunk the job belongs to."""

    splits: int | None
    """Split the job belongs to. ``-1`` if it is not part of a split."""

    out_path_local: str | None
    """Path to the job output file in the local filesystem."""

    err_path_local: str | None
    """Path to the job error file in the local filesystem."""

    out_path_remote: str | None
    """Path to the job output file in the remote filesystem."""

    err_path_remote: str | None
    """Path to the job error file in the remote filesystem."""


def format_category_value(prop: JobCategoryProperty, value: Any) -> Any:
    """Normalizes a raw job property to be returned by the API.

    The pkl and the SQL backends store the same information differently.
    Normalization is needed to return a consistent representation.

    - ``date``: ``YYYY-MM-DD`` string.
    - ``status``: status name (e.g. ``COMPLETED``) instead of its numeric code.
    - missing values: ``NA`` (``UNKNOWN`` for status).

    :param prop: The job property to normalize.
    :param value: The raw value of the job property.
    :return: The normalized value of the job property.
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
    """Normalizes a job filter value received from the API.

    ``NA`` is the value exposed by the category tree for the jobs without a
    value, so it is translated to ``None`` to make it usable as a filter by both
    backends.

    :param value: The raw value of the job filter.
    :return: The normalized value of the job filter.
    """
    if value == MISSING_CATEGORY_VALUE:
        return None
    return value
