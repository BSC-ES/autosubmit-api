from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import Column, Select, create_engine, or_, select

from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.database import tables
from autosubmit_api.database.common import (
    create_main_db_conn,
    execute_with_limit_offset,
)


def wildcard_search(query: str, column: Column) -> str:
    """
    Replace * to % for wildcard search and seek if the query is negated
    """
    # Replace * to % for wildcard search
    query = query.replace("*", "%")
    # Check if the query is negated
    if query.startswith("!"):
        return column.not_like(query[1:])
    return column.like(query)


def generate_query_listexp_extended(
    query: str = None,
    only_active: bool = False,
    owner: str = None,
    exp_type: str = None,
    autosubmit_version: str = None,
    hpc: str = None,
    order_by: str = None,
    order_desc: bool = False,
) -> Select:
    """
    Query listexp without accessing the view with status and total/completed jobs.
    """

    statement = (
        select(
            tables.ExperimentTable,
            tables.DetailsTable,
            tables.ExperimentStatusTable.c.exp_id,
            tables.ExperimentStatusTable.c.status,
        )
        .join(
            tables.DetailsTable,
            tables.ExperimentTable.c.id == tables.DetailsTable.c.exp_id,
            isouter=True,
        )
        .join(
            tables.ExperimentStatusTable,
            tables.ExperimentTable.c.id == tables.ExperimentStatusTable.c.exp_id,
            isouter=True,
        )
    )

    # Build filters
    filter_stmts = []

    if query:
        filter_stmts.append(
            or_(
                tables.ExperimentTable.c.name.like(f"%{query}%"),
                tables.ExperimentTable.c.description.like(f"%{query}%"),
                tables.DetailsTable.c.user.like(f"%{query}%"),
            )
        )

    if only_active:
        filter_stmts.append(tables.ExperimentStatusTable.c.status == "RUNNING")

    if owner:
        filter_stmts.append(wildcard_search(owner, tables.DetailsTable.c.user))

    if exp_type == "test":
        filter_stmts.append(tables.ExperimentTable.c.name.like("t%"))
    elif exp_type == "operational":
        filter_stmts.append(tables.ExperimentTable.c.name.like("o%"))
    elif exp_type == "experiment":
        filter_stmts.append(tables.ExperimentTable.c.name.not_like("t%"))
        filter_stmts.append(tables.ExperimentTable.c.name.not_like("o%"))

    if autosubmit_version:
        filter_stmts.append(
            wildcard_search(
                autosubmit_version, tables.ExperimentTable.c.autosubmit_version
            )
        )

    if hpc:
        filter_stmts.append(wildcard_search(hpc, tables.DetailsTable.c.hpc))

    statement = statement.where(*filter_stmts)

    # Order by
    ORDER_OPTIONS = {
        "expid": tables.ExperimentTable.c.name,
        "created": tables.DetailsTable.c.created,
        "description": tables.ExperimentTable.c.description,
    }
    order_col: Optional[Column[Any]] = None
    if order_by:
        order_col = ORDER_OPTIONS.get(order_by, None)

    if isinstance(order_col, Column):
        if order_desc:
            order_col = order_col.desc()
        statement = statement.order_by(order_col)

    return statement


class ExperimentJoinRepository(ABC):
    @abstractmethod
    def search(
        self,
        query: str = None,
        only_active: bool = False,
        owner: str = None,
        exp_type: str = None,
        autosubmit_version: str = None,
        hpc: str = None,
        order_by: str = None,
        order_desc: bool = False,
        limit: int = None,
        offset: int = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Search experiments with extended information.

        :return: A tuple with a list of experiments and the total number of rows
        """

    def drop_status_from_deleted_experiments(self) -> int:
        """
        Drop status records from experiments that are not in the experiments table
        """


class ExperimentJoinSQLRepository(ExperimentJoinRepository):
    def _get_connection(self):
        if APIBasicConfig.DATABASE_BACKEND == "postgres":
            # PostgreSQL
            return create_engine(APIBasicConfig.DATABASE_CONN_URL).connect()
        # SQLite
        return create_main_db_conn(read_only=True)

    def search(
        self,
        query: str = None,
        only_active: bool = False,
        owner: str = None,
        exp_type: str = None,
        autosubmit_version: str = None,
        hpc: str = None,
        order_by: str = None,
        order_desc: bool = False,
        limit: int = None,
        offset: int = None,
    ):
        statement = generate_query_listexp_extended(
            query=query,
            only_active=only_active,
            owner=owner,
            exp_type=exp_type,
            autosubmit_version=autosubmit_version,
            hpc=hpc,
            order_by=order_by,
            order_desc=order_desc,
        )
        with self._get_connection() as conn:
            query_result, total_rows = execute_with_limit_offset(
                statement=statement, conn=conn, limit=limit, offset=offset
            )

        result = [row._asdict() for row in query_result]
        return result, total_rows

    def drop_status_from_deleted_experiments(self) -> int:
        with self._get_connection() as conn:
            del_stmnt = tables.ExperimentStatusTable.delete().where(
                tables.ExperimentStatusTable.c.exp_id.not_in(
                    select(tables.ExperimentTable.c.id)
                )
            )
            result = conn.execute(del_stmnt)
            conn.commit()

        return result.rowcount


def create_experiment_join_repository() -> ExperimentJoinRepository:
    return ExperimentJoinSQLRepository()
