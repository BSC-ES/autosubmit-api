from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.database.db_manager import DbManager
from autosubmit_api.experiment.common_db_requests import prepare_completed_times_db, prepare_status_db
from autosubmit_api.workers.populate_details.populate import DetailsProcessor

class ExtendedDB:
    def __init__(self, root_path: str, db_name: str, as_times_db_name: str) -> None:
        self.root_path = root_path
        self.db_name = db_name
        self.main_db_manager = DbManager(root_path, db_name)
        self.as_times_db_manager = DbManager(root_path, as_times_db_name)

    def prepare_db(self):
        """
        Create tables and views that are required
        """
        self.prepare_main_db()
        self.prepare_as_times_db()


    def prepare_main_db(self):
        APIBasicConfig.read()
        DetailsProcessor(APIBasicConfig).create_details_table_if_not_exists()
        self.main_db_manager.create_view(
            'listexp',
            'select id,name,user,created,model,branch,hpc,description from experiment left join details on experiment.id = details.exp_id'
            )
        
    def prepare_as_times_db(self):
        prepare_completed_times_db()
        prepare_status_db()
        self.as_times_db_manager.create_view('currently_running',
            'select s.name, s.status, t.total_jobs from experiment_status as s inner join experiment_times as t on s.name = t.name where s.status="RUNNING" ORDER BY t.total_jobs'
            )


