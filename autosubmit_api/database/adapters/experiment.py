from typing import Any, Dict
from autosubmit.database.db_manager import create_db_table_manager

from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.database import tables


class ExperimentDbAdapter:
    def __init__(self):
        self.table_manager = create_db_table_manager(
            table=tables.ExperimentTable,
            db_filepath=APIBasicConfig.DB_PATH,
        )

    def create_table(self):
        """
        Create the experiment table.
        """
        with self.table_manager.get_connection() as conn:
            self.table_manager.create_table(conn)

    def get_all(self):
        """
        Return all experiments.
        """
        with self.table_manager.get_connection() as conn:
            rows = self.table_manager.select_all(conn)
        return rows

    def get_by_expid(self, expid: str) -> Dict[str, Any]:
        """
        Get experiment by expid.

        :param expid: Experiment ID.
        :raises: sqlalchemy.orm.exc.NoResultFound if no experiment is found.
        :raises: sqlalchemy.orm.exc.MultipleResultsFound if more than one experiment is found.
        """
        with self.table_manager.get_connection() as conn:
            row = conn.execute(
                self.table_manager.table.select().where(
                    tables.ExperimentTable.name == expid
                )
            ).one()
        return row._mapping
