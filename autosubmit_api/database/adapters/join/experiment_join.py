from sqlalchemy import select
from autosubmit_api.database import tables
from autosubmit_api.database.common import (
    create_main_db_conn,
    execute_with_limit_offset,
)
from autosubmit_api.database.queries import generate_query_listexp_extended


class ExperimentJoinDbAdapter:
    """
    Adapter for experiments using Experiment, ExperimentStatus and ExperimentDetails tables.
    """

    def _get_connection(self):
        return create_main_db_conn()

    def drop_status_from_deleted_experiments(self) -> int:
        with self._get_connection() as conn:
            del_stmnt = tables.experiment_status_table.delete().where(
                tables.experiment_status_table.c.exp_id.not_in(
                    select(tables.experiment_table.c.id)
                )
            )
            result = conn.execute(del_stmnt)
            conn.commit()

        return result.rowcount

    def search(
        self,
        query: str = None,
        only_active: bool = False,
        owner: str = None,
        exp_type: str = None,
        autosubmit_version: str = None,
        order_by: str = None,
        order_desc: bool = False,
        limit: int = None,
        offset: int = None,
    ):
        """
        Search experiments with extended information.
        """
        statement = generate_query_listexp_extended(
            query=query,
            only_active=only_active,
            owner=owner,
            exp_type=exp_type,
            autosubmit_version=autosubmit_version,
            order_by=order_by,
            order_desc=order_desc,
        )
        with self._get_connection() as conn:
            query_result, total_rows = execute_with_limit_offset(
                statement=statement,
                conn=conn,
                limit=limit,
                offset=offset,
            )

        return query_result, total_rows
