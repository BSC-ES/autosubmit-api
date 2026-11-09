from __future__ import annotations

import datetime
import heapq
import re
from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from typing import Any, NamedTuple

from sqlalchemy import Connection, Engine, Table, create_engine, false, func, select

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
from autosubmit_api.repositories.job_packages import (
    JobPackagesRepository,
    create_job_packages_repository,
    get_wrapper_jobs_table,
)

STRING_TO_CODE = common_utils.Status.STRING_TO_CODE


class JobRow(NamedTuple):
    """A job of the pkl job list, in the compact form used to filter and page it."""

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
    """Builds a ``JobRow`` from a job entry of the parsed pkl job list.
    
    :param job: A job of the pkl job list.
    :return: A ``JobRow`` instance, in the compact form used to filter and page it.
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
    """Order shared with the SQL repository: by name, case-insensitively.
    
    :param row: A job of the pkl in the compact form used to filter and page it.
    :return: A tuple containing the lowercase name and the original name.
    """
    return (row.name.lower(), row.name)


class JobsRepository(ABC):
    @abstractmethod
    def get_all(self) -> list[JobData]:
        """Gets all jobs."""

    @abstractmethod
    def get_last_modified_timestamp(self) -> int:
        """Gets the last modified UNIX timestamp of the jobs."""

    @abstractmethod
    def get_by_name(self, name: str) -> JobData | None:
        """Gets a job by its name."""

    @abstractmethod
    def get_by_names(self, names: list[str]) -> list[JobData]:
        """Gets jobs matching any of the given names."""

    @abstractmethod
    def search(
        self,
        job_name: str | Unset = UNSET,
        status: str | None | Unset = UNSET,
        date: str | None | Unset = UNSET,
        member: str | None | Unset = UNSET,
        section: str | None | Unset = UNSET,
        wrapper: str | None | Unset = UNSET,
        chunk: int | None | Unset = UNSET,
        with_wrapper: bool = False,
        page: Page = UNPAGINATED,
    ) -> tuple[list[JobData], int]:
        """Searches jobs applying the given filters.

        Filters are combined with AND. For the property filters, ``UNSET`` means
        "do not filter by this property", ``None`` means "match the jobs without
        a value" and any other value is compared against the normalized value.

        ``job_name`` is a wildcard expression instead of a property filter, and
        every job has a name, so it has no empty value: ``UNSET`` is its only way
        of not filtering.

        ``wrapper`` is a property filter, but it is not stored in the job list, so
        reading it is not free: the backend decides how to get it and only does it
        when the filter is set or ``with_wrapper`` requests it.

        :param with_wrapper: Whether the returned jobs report their wrapper.
        :param page: Slice of the matching jobs to return, paginated by job name.
        :returns: A tuple containing the jobs of the page and the total count of
            the jobs matching the filters (before pagination).
        """

    @abstractmethod
    def get_properties_counts(
        self, groupings: Sequence[Sequence[JobCategoryProperty]]
    ) -> list[dict[tuple, int]]:
        """Gets the number of jobs for each combination of the given properties.

        It works like a SQL GROUP BY query: the keys of the returned mappings
        follow the order of their grouping and the values are normalized with
        :func:`format_category_value`.

        ``wrapper`` is not stored in the job list, so grouping by it requires
        reading the packaging, which the backend only does when it is requested.

        :param groupings: The properties to group by, one grouping per tree to
            build. The backends read all of them in the same pass, so two
            groupings do not read the job list twice.
        :return: One mapping per grouping, in the same order. Each mapping goes
            from the combination of property values to the number of jobs with
            that combination.
        """


class JobsPklRepository(JobsRepository):
    PROPERTY_ORDER: tuple[JobCategoryProperty, ...] = (
        JobCategoryProperty.DATE,
        JobCategoryProperty.MEMBER,
        JobCategoryProperty.SECTION,
        JobCategoryProperty.WRAPPER,
        JobCategoryProperty.CHUNK,
        JobCategoryProperty.STATUS,
    )
    """Properties of a job that can be grouped, in the order they are read."""

    def __init__(
        self,
        expid: str,
        wrapper_repo_factory: Callable[
            ..., JobPackagesRepository
        ] = create_job_packages_repository,
    ) -> None:
        self.expid = expid
        self.pkl_reader = PklReader(expid)
        self._wrapper_repo_factory = wrapper_repo_factory
        self._wrappers: dict[str, str] | None = None

    def _wrapper_map(
        self, job_names: list[str] | None = None, wrapper: str | None = None
    ) -> dict[str, str]:
        """Gets the wrapper of the jobs, keyed by job name.

        The pkl job list does not store the packaging: it comes from the packaging
        database. An experiment that has not been packaged yet has no wrappers,
        which is not an error.

        :param job_names: Only these jobs. ``None`` reads the whole packaging.
        :param wrapper: Only the jobs of this wrapper. ``None`` does not filter.
        :return: The wrapper of each packaged job. Jobs outside a wrapper are not
            included.
        """
        if self._wrappers is not None and job_names is None and wrapper is None:
            return self._wrappers

        for preview in (False, True):
            try:
                wrappers = self._wrapper_repo_factory(
                    self.expid, preview=preview
                ).get_wrapper_map(job_names, wrapper)
            except Exception as exc:
                logger.debug("Error while reading the job wrappers: %s", exc)
                continue

            if wrappers or preview:
                # Nothing else to try: either the packaging was found or the
                # experiment has no preview packaging either
                if job_names is None and wrapper is None:
                    self._wrappers = wrappers
                return wrappers

        return {}

    def _rows(self) -> tuple[JobRow, ...]:
        """Gets the jobs of the pkl in the compact form used to filter and page them.

        Only the rows of the returned page become ``JobData``, so a big job list does
        not require building a big list of models.

        :return: The jobs of the pkl in the compact form used to filter and page them.
        """
        return tuple(_to_row(job) for job in self.pkl_reader.parse_job_list())

    @staticmethod
    def _row_to_job_data(row: JobRow, wrapper: str | None = None) -> JobData:
        """Builds the ``JobData`` only for the rows being returned.
        
        :param row: A job of the pkl in the compact form used to filter and page it.
        :param wrapper: The wrapper of the job, when it was requested.
        :return: The job data model of the row.
        """
        return JobData(**row._asdict(), wrapper=wrapper)

    @staticmethod
    def _matches_property(job: Any, prop: JobCategoryProperty, expected: Any) -> bool:
        """Checks a single property filter against a raw job entry of the pkl list.

        :param job: A job of the pkl in the compact form used to filter and page it.
        :param prop: The property to check.
        :param expected: The expected value of the property
        :return: True if the job matches the filter, False otherwise.
        """
        if expected is UNSET:
            return True

        expected = normalize_filter_value(expected)
        raw_value = getattr(job, prop.value)
        if expected is None:
            return raw_value is None
        return format_category_value(prop, raw_value) == expected

    @staticmethod
    def _matches_wrapper(
        job: Any, expected: Any, wrappers: dict[str, str], filter_by_absence: bool
    ) -> bool:
        """Checks the wrapper filter against a job.

        The wrapper is not part of the job of the pkl list, so it is looked up in
        the packaging of the experiment.

        :param job: A job of the pkl in the compact form used to filter and page it.
        :param expected: The expected wrapper, ``UNSET`` to not filter, ``None`` for
            the jobs outside a wrapper.
        :param wrappers: The wrapper of each packaged job, keyed by job name. It may
            only hold the wrappers of one wrapper, or of the jobs of the page.
        :param filter_by_absence: Whether ``wrappers`` holds every packaged job, which
            is required to tell the jobs without a wrapper apart.
        :return: True if the job matches the filter, False otherwise.
        """
        if expected is UNSET:
            return True

        if expected is None:
            return filter_by_absence and job.name not in wrappers
        return wrappers.get(job.name) == expected

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
        """Checks if a job of the pkl job list matches the given filters.

        :param job: A job of the pkl in the compact form used to filter and page it.
        :param job_name: The job name filter, as a wildcard expression.
        :param status: The job status filter.
        :param date: The job date filter.
        :param member: The job member filter.
        :param section: The job section filter.
        :param chunk: The job chunk filter.
        :return: True if the job matches the filters, False otherwise.
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
        """Compares a value with a wildcard expression.

        The expression can contain '*' as wildcard, and '!' as negation.
        If the expression is empty, it matches everything. Examples:
        - 'test*' matches 'test123', 'test_abc', etc. Not matching '123test'.
        - '!test*' does not match 'test123', 'test_abc', etc

        :param expression: The wildcard expression to compare against.
        :param value: The value to compare.
        :return: True if the value matches the expression, False otherwise.
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
        """Gets all jobs from the pkl job list."""
        return [self._row_to_job_data(row) for row in self._rows()]

    def get_last_modified_timestamp(self) -> int:
        return self.pkl_reader.get_modified_time()

    def get_by_name(self, name: str) -> JobData | None:
        """Gets a job by its name from the pkl job list."""
        for row in self._rows():
            if row.name == name:
                return self._row_to_job_data(row)
        return None

    def get_by_names(self, names: list[str]) -> list[JobData]:
        """Gets all jobs whose names are in the given list."""
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
        wrapper: str | None | Unset = UNSET,
        chunk: int | None | Unset = UNSET,
        with_wrapper: bool = False,
        page: Page = UNPAGINATED,
    ) -> tuple[list[JobData], int]:
        """Searches jobs by the given filters in a deterministic order (job name).

        :param job_name: Filter by job name.
        :param status: Filter by job status.
        :param date: Filter by job date.
        :param member: Filter by job member.
        :param section: Filter by job section.
        :param wrapper: Filter by job wrapper, read from the packaging database.
        :param chunk: Filter by job chunk.
        :param with_wrapper: Whether the returned jobs report their wrapper.
        :param page: Slice of the matching jobs to return, paginated by job name.
        :returns: A tuple containing the jobs of the page and the total count of
            the jobs matching the filters (before pagination).
        """
        if wrapper is not UNSET:
            expected_wrapper = normalize_filter_value(wrapper)
        else:
            expected_wrapper = UNSET

        # The wrapper of a job is not in the pkl, so it is read from the packaging
        # database: only the page when it is just returned, and the whole packaging
        # when the jobs have to be filtered or grouped by it.
        if expected_wrapper is UNSET and with_wrapper:
            wrappers = {}
            needs_full_map = False
        elif expected_wrapper is None:
            wrappers = self._wrapper_map()
            needs_full_map = True
        else:
            wrappers = self._wrapper_map(wrapper=expected_wrapper)
            needs_full_map = False

        matching_rows = [
            row
            for row in self._rows()
            if self._matches_filters(
                row, job_name, status, date, member, section, chunk
            )
            and self._matches_wrapper(row, expected_wrapper, wrappers, needs_full_map)
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

        if with_wrapper and expected_wrapper is UNSET:
            # The wrapper of the jobs of the page only
            wrappers = self._wrapper_map(job_names=[row.name for row in page_rows])

        return [
            self._row_to_job_data(row, wrappers.get(row.name)) for row in page_rows
        ], len(matching_rows)

    def get_properties_counts(
        self, groupings: Sequence[Sequence[JobCategoryProperty]]
    ) -> list[dict[tuple, int]]:
        """Gets the number of jobs for each combination of the given properties.

        The whole packaging is read at most once, and only when one of the
        groupings uses the wrapper.

        :param groupings: The properties to group by, one grouping per tree to
            build.
        :return: One mapping per grouping, in the same order.
        """
        groupings = [
            [JobCategoryProperty(prop) for prop in grouping]
            for grouping in groupings
        ]
        wrappers = (
            self._wrapper_map()
            if any(JobCategoryProperty.WRAPPER in grouping for grouping in groupings)
            else {}
        )

        # Dates, members, sections, wrappers, chunks and statuses are shared by
        # many jobs, so normalizing the values is done once per distinct value
        # instead of once per job and grouping.
        properties = [
            prop for prop in self.PROPERTY_ORDER if any(prop in g for g in groupings)
        ]
        normalized: dict[JobCategoryProperty, dict[Any, Any]] = {
            prop: {} for prop in properties
        }
        positions = [
            [properties.index(prop) for prop in grouping] for grouping in groupings
        ]

        counts: list[dict[tuple, int]] = [{} for _ in groupings]
        for row in self._rows():
            values = []
            for prop in properties:
                cache = normalized[prop]
                raw_value = (
                    wrappers.get(row.name)
                    if prop is JobCategoryProperty.WRAPPER
                    else getattr(row, prop.value)
                )
                value = cache.get(raw_value)
                if value is None:
                    value = cache[raw_value] = format_category_value(prop, raw_value)
                values.append(value)

            for order, grouping_counts in zip(positions, counts):
                key = tuple(values[position] for position in order)
                grouping_counts[key] = grouping_counts.get(key, 0) + 1
        return counts


class JobsSQLRepository(JobsRepository):
    def __init__(
        self,
        expid: str,
        engine: Engine,
        table: Table,
        wrapper_table: Table | None = None,
    ) -> None:
        self.expid = expid
        self.engine = engine
        self.table = table
        self.wrapper_table = wrapper_table
        self._wrappers_subquery: Any = None

        # Check table schema
        if tables.check_table_schema(self.engine, [self.table]) is None:
            raise ValueError(
                f"Table schema for {self.table.name} does not match expected schema."
            )

    def _wrapper_subquery(self) -> Any:
        """Builds the subquery with the wrapper of each job, once per repository.

        The packaging table keeps the packages of every run, so the wrapper of a
        job is the one of its latest package (a v2 table has the run id and every
        revision has a package id). An experiment without a packaging table has no
        wrappers, which is not an error.

        :return: Subquery with the columns ``job_name`` and ``wrapper``, or
            ``None`` if the experiment has no packaging table.
        """
        if self.wrapper_table is None:
            return None
        if self._wrappers_subquery is not None:
            return self._wrappers_subquery

        wrapper_table = self.wrapper_table
        if "package_id" in wrapper_table.c:
            # One row per job: the packaging of its latest package
            latest_packages = (
                select(
                    wrapper_table.c.job_name.label("job_name"),
                    func.max(wrapper_table.c.package_id).label("package_id"),
                )
                .group_by(wrapper_table.c.job_name)
                .subquery()
            )
            statement = (
                select(
                    wrapper_table.c.job_name.label("job_name"),
                    wrapper_table.c.package_name.label("wrapper"),
                )
                .select_from(
                    wrapper_table.join(
                        latest_packages,
                        (wrapper_table.c.job_name == latest_packages.c.job_name)
                        & (wrapper_table.c.package_id == latest_packages.c.package_id),
                    )
                )
            )
        else:
            statement = select(
                wrapper_table.c.job_name.label("job_name"),
                wrapper_table.c.package_name.label("wrapper"),
            )

        self._wrappers_subquery = statement.subquery()
        return self._wrappers_subquery

    def _with_wrappers(self, statement, wrapper_subquery):
        """Adds the wrapper of the jobs and applies the wrapper filter.

        :param statement: Statement of the job list.
        :param wrapper_subquery: Subquery with the wrapper of each job.
        :return: The statement joined with the wrappers.
        """
        return statement.select_from(
            self.table.outerjoin(
                wrapper_subquery,
                wrapper_subquery.c.job_name == self.table.c.name,
            )
        ).add_columns(wrapper_subquery.c.wrapper)

    
    @staticmethod
    def _to_job_data(row: Any) -> JobData:
        """Builds a ``JobData`` instance from a raw SQL row."""
        return JobData(
            id=row.id,
            name=row.name,
            status=STRING_TO_CODE.get(row.status, common_utils.Status.UNKNOWN),
            priority=row.priority,
            section=row.section,
            date=row.date,
            member=row.member,
            wrapper=getattr(row, "wrapper", None),
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
        """Converts a wildcard expression to a SQL LIKE pattern.
        
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
        """Gets all jobs from SQL database."""
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
        """Gets the column to compare the given property against.

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
        wrapper: str | None | Unset = UNSET,
        chunk: int | None | Unset = UNSET,
        with_wrapper: bool = False,
        page: Page = UNPAGINATED,
    ) -> tuple[list[JobData], int]:
        """Searches jobs by the given filters in a deterministic order (job name).

        :returns: A tuple containing the jobs of the page and the total count of
            the jobs matching the filters (before pagination).
        """
        wrapper_subquery = (
            self._wrapper_subquery()
            if wrapper is not UNSET or with_wrapper
            else None
        )

        with self.engine.connect() as conn:
            statement = self.table.select()
            if wrapper_subquery is not None:
                statement = self._with_wrappers(statement, wrapper_subquery)

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

            if wrapper is not UNSET:
                expected_wrapper = normalize_filter_value(wrapper)
                wrapper_column = (
                    wrapper_subquery.c.wrapper
                    if wrapper_subquery is not None
                    else None
                )
                if wrapper_column is None:
                    # The experiment has no packaging: no job has a wrapper
                    statement = statement.where(false())
                elif expected_wrapper is None:
                    statement = statement.where(wrapper_column.is_(None))
                else:
                    statement = statement.where(wrapper_column == expected_wrapper)

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
        self, groupings: Sequence[Sequence[JobCategoryProperty]]
    ) -> list[dict[tuple, int]]:
        """Gets the number of jobs for each combination of the given properties.

        Each grouping is a GROUP BY query. They share the connection and the
        subquery of the wrappers, which is built once per repository.

        :param groupings: The properties to group by, one grouping per tree to
            build.
        :return: One mapping per grouping, in the same order.
        """
        groupings = [
            [JobCategoryProperty(prop) for prop in grouping]
            for grouping in groupings
        ]
        with self.engine.connect() as conn:
            return [
                self._grouped_counts(conn, grouping) for grouping in groupings
            ]

    def _grouped_counts(
        self, conn: Connection, properties: Sequence[JobCategoryProperty]
    ) -> dict[tuple, int]:
        """Counts the jobs of each combination of properties with a GROUP BY query.

        :param conn: Connection to the database of the job list.
        :param properties: The properties to group by.
        :return: A mapping from the combination of property values to the number
            of jobs with that combination.
        """
        wrapper_subquery = (
            self._wrapper_subquery()
            if JobCategoryProperty.WRAPPER in properties
            else None
        )
        columns = [
            (
                wrapper_subquery.c.wrapper
                if prop is JobCategoryProperty.WRAPPER
                and wrapper_subquery is not None
                else self._property_column(self.table, prop)
            )
            for prop in properties
        ]
        statement = select(func.count().label("jobs_count"), *columns)
        if wrapper_subquery is not None:
            statement = statement.select_from(
                self.table.outerjoin(
                    wrapper_subquery,
                    wrapper_subquery.c.job_name == self.table.c.name,
                )
            )
        statement = statement.group_by(*columns)

        counts: dict[tuple, int] = {}
        for row in conn.execute(statement).all():
            # Positional access: the first column is the counter and the
            # expressions returned by _property_column may be unlabeled.
            key = tuple(
                format_category_value(prop, row[position + 1])
                for position, prop in enumerate(properties)
            )
            counts[key] = row[0]
        return counts


def create_jobs_repository(expid: str) -> JobsRepository:
    """Factory function to create a JobsRepository instance.
    
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
            return JobsSQLRepository(
                expid,
                engine,
                table,
                wrapper_table=get_wrapper_jobs_table(expid, engine),
            )
    else:
        exp_paths = ExperimentPaths(expid)

        if is_gt_4_2_0:
            engine = create_sqlite_db_engine(exp_paths.job_list_db, read_only=True)
            table = tables.JobsTable
            return JobsSQLRepository(
                expid,
                engine,
                table,
                wrapper_table=get_wrapper_jobs_table(expid, engine),
            )

    return JobsPklRepository(expid)
