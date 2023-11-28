from sqlalchemy import select, or_
from autosubmit_api.database import tables
from autosubmit_api.database.common import create_main_db_conn
from autosubmit_api.logger import logger


def query_listexp_extended(
    query: str = None,
    only_active: bool = False,
    owner: str = None,
    exp_type: str = None,
    limit: int = None,
    offset: int = None,
):
    """
    Query listexp without accessing the view with status and total/completed jobs.
    """

    statement = (
        select(
            tables.experiment_table,
            tables.details_table,
            tables.experiment_times_table.c.exp_id,
            tables.experiment_times_table.c.total_jobs,
            tables.experiment_times_table.c.completed_jobs,
            tables.experiment_status_table.c.exp_id,
            tables.experiment_status_table.c.status,
        )
        .join(
            tables.details_table,
            tables.experiment_table.c.id == tables.details_table.c.exp_id,
            isouter=True,
        )
        .join(
            tables.experiment_times_table,
            tables.experiment_table.c.id == tables.experiment_times_table.c.exp_id,
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
                tables.experiment_table.c.name.like(f"{query}%"),
                tables.experiment_table.c.description.like(f"%{query}%"),
                tables.details_table.c.user.like(f"%{query}%"),
            )
        )

    if only_active:
        filter_stmts.append(tables.experiment_status_table.c.status == "RUNNING")

    if owner:
        filter_stmts.append(tables.details_table.c.user == owner)

    if exp_type == "test":
        filter_stmts.append(tables.experiment_table.c.name.like(f"t%"))
    elif exp_type == "operational":
        filter_stmts.append(tables.experiment_table.c.name.like(f"o%"))
    elif exp_type == "experiment":
        filter_stmts.append(tables.experiment_table.c.name.not_like(f"t%"))
        filter_stmts.append(tables.experiment_table.c.name.not_like(f"o%"))

    # logger.debug(str(filter_stmts))
    statement = statement.where(*filter_stmts)

    # Add limit and offset
    statement = statement.offset(offset)
    if limit > 0:
        statement = statement.limit(limit)

    # Execute query
    conn = create_main_db_conn()
    logger.debug(statement.compile(conn))
    query_result = conn.execute(statement).all()
    conn.close()

    return query_result
