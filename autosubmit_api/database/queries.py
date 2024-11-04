from typing import Optional
from pyparsing import Any
from sqlalchemy import Column, Select, select, or_
from autosubmit_api.database import tables


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
    order_by: str = None,
    order_desc: bool = False,
) -> Select:
    """
    Query listexp without accessing the view with status and total/completed jobs.
    """

    statement = (
        select(
            tables.experiment_table,
            tables.details_table,
            tables.experiment_status_table.c.exp_id,
            tables.experiment_status_table.c.status,
        )
        .join(
            tables.details_table,
            tables.experiment_table.c.id == tables.details_table.c.exp_id,
            isouter=True,
        )
        .join(
            tables.experiment_status_table,
            tables.experiment_table.c.id == tables.experiment_status_table.c.exp_id,
            isouter=True,
        )
    )

    # Build filters
    filter_stmts = []

    if query:
        filter_stmts.append(
            or_(
                tables.experiment_table.c.name.like(f"%{query}%"),
                tables.experiment_table.c.description.like(f"%{query}%"),
                tables.details_table.c.user.like(f"%{query}%"),
            )
        )

    if only_active:
        filter_stmts.append(tables.experiment_status_table.c.status == "RUNNING")

    if owner:
        filter_stmts.append(wildcard_search(owner, tables.details_table.c.user))

    if exp_type == "test":
        filter_stmts.append(tables.experiment_table.c.name.like("t%"))
    elif exp_type == "operational":
        filter_stmts.append(tables.experiment_table.c.name.like("o%"))
    elif exp_type == "experiment":
        filter_stmts.append(tables.experiment_table.c.name.not_like("t%"))
        filter_stmts.append(tables.experiment_table.c.name.not_like("o%"))

    if autosubmit_version:
        filter_stmts.append(
            wildcard_search(
                autosubmit_version, tables.experiment_table.c.autosubmit_version
            )
        )

    statement = statement.where(*filter_stmts)

    # Order by
    ORDER_OPTIONS = {
        "expid": tables.experiment_table.c.name,
        "created": tables.details_table.c.created,
        "description": tables.experiment_table.c.description,
    }
    order_col: Optional[Column[Any]] = None
    if order_by:
        order_col = ORDER_OPTIONS.get(order_by, None)

    if isinstance(order_col, Column):
        if order_desc:
            order_col = order_col.desc()
        statement = statement.order_by(order_col)

    return statement
