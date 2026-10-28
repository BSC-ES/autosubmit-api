from __future__ import annotations

import datetime
import heapq
import re
from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any, NamedTuple

from sqlalchemy import Engine, Table, create_engine, func, select

from autosubmit_api.common import utils as common_utils
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.database import tables
from autosubmit_api.database.common import (
    create_sqlite_db_engine,
    iter_param_chunks,
)
from autosubmit_api.logger import logger
from autosubmit_api.models.jobs import (
    UNSET,
    JobCategoryProperty,
    JobData,
    Unset,
    format_category_value,
    normalize_filter_value,
)
from autosubmit_api.models.pagination import UNPAGINATED, Page
from autosubmit_api.persistance.experiment import ExperimentPaths
from autosubmit_api.persistance.pkl_reader import PklReader
from autosubmit_api.repositories.experiment import create_experiment_repository

STRING_TO_CODE = common_utils.Status.STRING_TO_CODE


class JobRow(NamedTuple):
    """
    A job of the pkl job list, in the compact form used to filter and page it.
    """

    id: int | None
    name: str
    status: int | None
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


def _to_row(job: Any) -> JobRow:
    """
    Builds a ``JobRow`` from a job entry of the parsed pkl job list.
    """
    return JobRow(
        id=job.id,
        name=job.name,
        status=(
            job.status if job.status is not None else common_utils.Status.UNKNOWN
        ),
        priority=job.priority,
        section=job.section,
        date=job.date,
        member=job.member,
        chunk=job.chunk,
        split=job.split,
        splits=job.splits,
        out_path_local=job.out_path_local,
        err_path_local=job.err_path_local,
        out_path_remote=job.out_path_remote,
        err_path_remote=job.err_path_remote,
    )


def _order_key(row: JobRow) -> tuple[str, str]:
    """
    Order shared with the SQL repository: by name, case-insensitively.
    """
    return (row.name.lower(), row.name)


class JobsRepository(ABC):
    @abstractmethod
    def get_all(self) -> list[JobData]:
        """
        Gets all jobs
        """

    @abstractmethod
    def get_last_modified_timestamp(self) -> int:
        """
        Gets the last modified UNIX timestamp of the jobs
        """

    @abstractmethod
    def get_by_name(self, name: str) -> JobData | None:
        """
        Gets a job by its name
        """

    @abstractmethod
    def get_by_names(self, names: list[str]) -> list[JobData]:
        """
        Gets jobs matching any of the given names
        """

    @abstractmethod
    def search(
        self,
        job_name: str | Unset = UNSET,
        status: str | None | Unset = UNSET,
        date: str | None | Unset = UNSET,
        member: str | None | Unset = UNSET,
        section: str | None | Unset = UNSET,
        chunk: int | None | Unset = UNSET,
        page: Page = UNPAGINATED,
    ) -> tuple[list[JobData], int]:
        """
        Searches jobs applying the given filters.

        Filters are combined with AND. For the property filters, ``UNSET`` means
        "do not filter by this property", ``None`` means "match the jobs without
        a value" and any other value is compared against the normalized value.

        ``job_name`` is a wildcard expression instead of a property filter, and
        every job has a name, so it has no empty value: ``UNSET`` is its only way
        of not filtering.

        :param page: Slice of the matching jobs to return, paginated by job name.
        :returns: A tuple containing the jobs of the page and the total count of
            the jobs matching the filters (before pagination).
        """

    @abstractmethod
    def get_properties_counts(
        self, properties: Sequence[JobCategoryProperty]
    ) -> dict[tuple, int]:
        """
        Gets the number of jobs for each combination of the given properties,
        similar to a SQL GROUP BY query.

        The keys of the returned mapping follow the order of ``properties`` and
        the values are normalized with :func:`format_category_value`.
        """


class JobsPklRepository(JobsRepository):
    def __init__(self, expid: str) -> None:
        self.expid = expid
        self.pkl_reader = PklReader(expid)

    def _rows(self) -> tuple[JobRow, ...]:
        """
        Gets the jobs of the pkl in the compact form used to filter and page them.

        Only the rows of the returned page become ``JobData``, so a big job list does
        not require building a big list of models.
        """
        return tuple(_to_row(job) for job in self.pkl_reader.parse_job_list())

    @staticmethod
    def _row_to_job_data(row: JobRow) -> JobData:
        """
        Builds the ``JobData`` only for the rows being returned.
        """
        return JobData(**row._asdict())

    @staticmethod
    def _matches_property(job: Any, prop: JobCategoryProperty, expected: Any) -> bool:
        """
        Checks a single property filter against a raw job entry of the pkl list.
        """
        if expected is UNSET:
            return True

        expected = normalize_filter_value(expected)
        raw_value = getattr(job, prop.value)
        if expected is None:
            return raw_value is None
        return format_category_value(prop, raw_value) == expected

    @classmethod
    def _matches_filters(
        cls,
        job: Any,
        job_name: str | Unset,
        status: Any,
        date: Any,
        member: Any,
        section: Any,
        chunk: Any,
    ) -> bool:
        """
        Checks if a job of the pkl job list matches the given filters.
        """
        if job_name is not UNSET and not cls._wildcard_compare(job_name, job.name):
            return False

        return all(
            cls._matches_property(job, prop, expected)
            for prop, expected in (
                (JobCategoryProperty.STATUS, status),
                (JobCategoryProperty.DATE, date),
                (JobCategoryProperty.MEMBER, member),
                (JobCategoryProperty.SECTION, section),
                (JobCategoryProperty.CHUNK, chunk),
            )
        )

    @staticmethod
    def _wildcard_compare(expression: str | None, value: str) -> bool:
        """
        Compares a value with a wildcard expression.
        The expression can contain '*' as wildcard, and '!' as negation.
        If the expression is empty, it matches everything.
        Examples:
        - 'test*' matches 'test123', 'test_abc', etc. Not matching '123test'.
        - '!test*' does not match 'test123', 'test_abc', etc
        """
        if not expression:
            return True

        # Case-insensitive comparison
        expression = expression.lower()
        value = value.lower()

        if expression.startswith("!"):
            return not JobsPklRepository._wildcard_compare(expression[1:], value)

        # Transform to regex style: escape metacharacters, then convert '*' wildcard to '.*'
        escaped_expression = re.escape(expression)
        pattern = escaped_expression.replace(r"\*", ".*")
        pattern = f"^.*{pattern}.*$"  # Match the whole string
        return bool(re.fullmatch(pattern, value))

    def get_all(self) -> list[JobData]:
        """
        Gets all jobs from the pkl job list
        """
        return [self._row_to_job_data(row) for row in self._rows()]

    def get_last_modified_timestamp(self) -> int:
        return self.pkl_reader.get_modified_time()

    def get_by_name(self, name: str) -> JobData | None:
        """
        Gets a job by its name from the pkl job list
        """
        for row in self._rows():
            if row.name == name:
                return self._row_to_job_data(row)
        return None

    def get_by_names(self, names: list[str]) -> list[JobData]:
        """
        Gets all jobs whose names are in the given list.
        """
        name_set = set(names)
        return [
            self._row_to_job_data(row) for row in self._rows() if row.name in name_set
        ]

    def search(
        self,
        job_name: str | Unset = UNSET,
        status: str | None | Unset = UNSET,
        date: str | None | Unset = UNSET,
        member: str | None | Unset = UNSET,
        section: str | None | Unset = UNSET,
        chunk: int | None | Unset = UNSET,
        page: Page = UNPAGINATED,
    ) -> tuple[list[JobData], int]:
        """
        Searches jobs by the given filters in a deterministic order (job name).

        :returns: A tuple containing the jobs of the page and the total count of
            the jobs matching the filters (before pagination).
        """
        matching_rows = [
            row
            for row in self._rows()
            if self._matches_filters(
                row, job_name, status, date, member, section, chunk
            )
        ]

        # Deterministic backend-agnostic order shared with the SQL repository.
        # Offset pagination is only reliable if the order is stable across
        # different backends and across different calls to the same backend.
        # name is the unique key (primary key in the jobs table).
        if page.is_paginated:
            # Only the rows of the page are needed
            page_rows = heapq.nsmallest(
                page.offset + page.limit, matching_rows, key=_order_key
            )[page.offset :]
        else:
            page_rows = sorted(matching_rows, key=_order_key)

        return [self._row_to_job_data(row) for row in page_rows], len(matching_rows)

    def get_properties_counts(
        self, properties: Sequence[JobCategoryProperty]
    ) -> dict[tuple, int]:
        """
        Gets the number of jobs for each combination of the given properties.
        """
        properties = [JobCategoryProperty(prop) for prop in properties]
        counts: dict[tuple, int] = {}
        for row in self._rows():
            key = tuple(
                format_category_value(prop, getattr(row, prop.value))
                for prop in properties
            )
            counts[key] = counts.get(key, 0) + 1
        return counts


class JobsSQLRepository(JobsRepository):
    def __init__(self, expid: str, engine: Engine, table: Table) -> None:
        self.expid = expid
        self.engine = engine
        self.table = table

        # Check table schema
        if tables.check_table_schema(self.engine, [self.table]) is None:
            raise ValueError(
                f"Table schema for {self.table.name} does not match expected schema."
            )

    
    @staticmethod
    def _to_job_data(row: Any) -> JobData:
        """
        Builds a ``JobData`` instance from a raw SQL row.
        """
        return JobData(
            id=row.id,
            name=row.name,
            status=STRING_TO_CODE.get(row.status, common_utils.Status.UNKNOWN),
            priority=row.priority,
            section=row.section,
            date=row.date,
            member=row.member,
            chunk=row.chunk,
            split=row.split,
            splits=row.splits,
            out_path_local=row.local_logs_out,
            err_path_local=row.local_logs_err,
            out_path_remote=row.remote_logs_out,
            err_path_remote=row.remote_logs_err,
        )

    @staticmethod
    def _wildcard_to_sql_like(expression: str) -> tuple[bool, str]:
        """
        Converts a wildcard expression to a SQL LIKE pattern.
        The expression can contain '*' as wildcard, and '!' as negation prefix.
        Special SQL LIKE characters '%' and '_' are escaped with a backslash.
        """
        negated = False
        if expression.startswith("!"):
            negated = True
            expression = expression[1:]

        # Escape SQL LIKE special characters
        pattern = (
            expression.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        )
        # Convert wildcard '*' to SQL LIKE '%'
        pattern = pattern.replace("*", "%")
        pattern = f"%{pattern}%"  # Match anywhere in the string

        return negated, pattern

    def get_all(self) -> list[JobData]:
        """
        Gets all jobs from SQL database
        """
        with self.engine.connect() as conn:
            result = conn.execute(self.table.select())
            return [self._to_job_data(row) for row in result]

    def get_last_modified_timestamp(self) -> int:
        with self.engine.connect() as conn:
            statement = (
                self.table.select().order_by(self.table.c.modified.desc()).limit(1)
            )
            result = conn.execute(statement).first()
            if result is not None:
                # Try to convert the modified timestamp iso string to int
                try:
                    _date = datetime.datetime.fromisoformat(result.modified)
                    return int(_date.timestamp())
                except Exception:
                    logger.warning(
                        f"Failed to convert modified timestamp '{result.modified}' to int for experiment {self.expid}."
                    )
                    return 0
            else:
                logger.warning(
                    f"No jobs found in the database for experiment {self.expid} to get last modified timestamp."
                )
                return 0

    def get_by_name(self, name: str) -> JobData | None:
        with self.engine.connect() as conn:
            statement = self.table.select().where(self.table.c.name == name)
            result = conn.execute(statement).first()
            if result is not None:
                return self._to_job_data(result)
            else:
                return None

    def get_by_names(self, names: list[str]) -> list[JobData]:
        rows = []
        with self.engine.connect() as conn:
            # Names are bound as query parameters, so the lookup is split in
            # chunks that fit in a single statement (see iter_param_chunks)
            for chunk in iter_param_chunks(names):
                statement = self.table.select().where(self.table.c.name.in_(chunk))
                result = conn.execute(statement).all()

                for row in result:
                    rows.append(self._to_job_data(row))
        return rows

    @staticmethod
    def _property_column(table: Table, prop: JobCategoryProperty):
        """
        Gets the column to compare the given property against.

        Dates are stored as ISO-8601 datetime strings, so only the date part is
        compared, keeping the same ``YYYY-MM-DD`` vocabulary as the pkl backend.
        """
        if prop is JobCategoryProperty.DATE:
            return func.substr(table.c.date, 1, 10)
        return getattr(table.c, prop.value)

    def search(
        self,
        job_name: str | Unset = UNSET,
        status: str | None | Unset = UNSET,
        date: str | None | Unset = UNSET,
        member: str | None | Unset = UNSET,
        section: str | None | Unset = UNSET,
        chunk: int | None | Unset = UNSET,
        page: Page = UNPAGINATED,
    ) -> tuple[list[JobData], int]:
        """
        Searches jobs by the given filters in a deterministic order (job name).

        :returns: A tuple containing the jobs of the page and the total count of
            the jobs matching the filters (before pagination).
        """

        with self.engine.connect() as conn:
            statement = self.table.select()

            if job_name is not UNSET:
                negated, pattern = self._wildcard_to_sql_like(job_name)
                if negated:
                    statement = statement.where(
                        self.table.c.name.notilike(pattern, escape="\\")
                    )
                else:
                    statement = statement.where(
                        self.table.c.name.ilike(pattern, escape="\\")
                    )

            for prop, expected in (
                (JobCategoryProperty.STATUS, status),
                (JobCategoryProperty.DATE, date),
                (JobCategoryProperty.MEMBER, member),
                (JobCategoryProperty.SECTION, section),
                (JobCategoryProperty.CHUNK, chunk),
            ):
                if expected is UNSET:
                    continue
                expected = normalize_filter_value(expected)
                column = self._property_column(self.table, prop)
                if expected is None:
                    statement = statement.where(column.is_(None))
                else:
                    statement = statement.where(
                        column == format_category_value(prop, expected)
                    )

            # Deterministic order shared with the PKL repository.
            # Job name is the unique key (primary key in the jobs table).
            ordered_statement = statement.order_by(
                func.lower(self.table.c.name), self.table.c.name
            )

            if page.is_paginated:
                # The total is only needed when a slice was requested
                count_statement = select(func.count()).select_from(statement.subquery())
                counter = conn.execute(count_statement).scalar()
                if page.offset:
                    ordered_statement = ordered_statement.offset(page.offset)
                ordered_statement = ordered_statement.limit(page.limit)
            else:
                counter = None

            result = conn.execute(ordered_statement).all()
            if counter is None:
                counter = len(result)

            filtered_jobs = [self._to_job_data(row) for row in result]
            return filtered_jobs, counter

    def get_properties_counts(
        self, properties: Sequence[JobCategoryProperty]
    ) -> dict[tuple, int]:
        """
        Gets the number of jobs for each combination of the given properties.
        """
        properties = [JobCategoryProperty(prop) for prop in properties]
        columns = [self._property_column(self.table, prop) for prop in properties]
        with self.engine.connect() as conn:
            statement = select(
                func.count().label("jobs_count"), *columns
            ).group_by(*columns)
            result = conn.execute(statement).all()

        counts: dict[tuple, int] = {}
        for row in result:
            # Positional access: the first column is the counter and the
            # expressions returned by _property_column may be unlabeled.
            key = tuple(
                format_category_value(prop, row[position + 1])
                for position, prop in enumerate(properties)
            )
            counts[key] = row[0]
        return counts


def create_jobs_repository(expid: str) -> JobsRepository:
    """
    Factory function to create a JobsRepository instance.
    It decides whether to use the SQL or PKL repository based on the
    existence of the SQLite database.

    :raises ExperimentNotFoundError: If the experiment does not exist
    """
    # Experiment should exist
    experiment = create_experiment_repository().get_by_expid(expid)
    is_gt_4_2_0 = common_utils.is_db_version_4_2_0_or_higher(
        experiment.autosubmit_version
    )

    if APIBasicConfig.DATABASE_BACKEND == "postgres":
        # Postgres
        if is_gt_4_2_0:
            engine = create_engine(APIBasicConfig.DATABASE_CONN_URL)
            table = tables.table_change_schema(expid, tables.JobsTable)
            return JobsSQLRepository(expid, engine, table)
    else:
        exp_paths = ExperimentPaths(expid)

        if is_gt_4_2_0:
            engine = create_sqlite_db_engine(exp_paths.job_list_db, read_only=True)
            table = tables.JobsTable
            return JobsSQLRepository(expid, engine, table)

    return JobsPklRepository(expid)
