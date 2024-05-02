from typing import Dict, List
from sqlalchemy import select
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.database import tables
from autosubmit_api.database.table_manager import create_db_table_manager
from autosubmit_api.persistance.experiment import ExperimentPaths



class ExperimentStructureDbRepository:
    def __init__(self, expid: str):
        APIBasicConfig.read()
        self.table_manager = create_db_table_manager(
            table=tables.ExperimentStructureTable,
            db_filepath=ExperimentPaths(expid).structure_db,
            schema=expid,
        )
        # with self.table_manager.get_connection() as conn:
        #     self.table_manager.create_table(conn)

    def get_structure(self):
        structure: Dict[str, List[str]] = {}

        with self.table_manager.get_connection() as conn:
            rows = conn.execute(
                select(self.table_manager.table)
            ).all()
        
        for row in rows:
            edge = row._asdict()
            _from, _to = edge.get("e_from"), edge.get("e_to")
            
            structure.setdefault(_from, []).append(_to)
            structure.setdefault(_to, [])

        return structure

