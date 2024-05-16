from sqlalchemy import select
from autosubmit_api.database import tables
from autosubmit_api.database.common import create_main_db_conn


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
