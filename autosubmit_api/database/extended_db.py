from autosubmit_api.database.db_manager import DbManager

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
        self.main_db_manager.create_table(
            'details',
            [
                'exp_id integer PRIMARY KEY',
                'user text NOT NULL',
                'created text NOT NULL',
                'model text NOT NULL',
                'branch text NOT NULL',
                'hpc text NOT NULL',
                'FOREIGN KEY (exp_id) REFERENCES experiment (id)'
            ])
        self.main_db_manager.create_view(
            'listexp',
            'select id,name,user,created,model,branch,hpc,description from experiment left join details on experiment.id = details.exp_id'
            )
        
    def prepare_as_times_db(self):
        self.as_times_db_manager.create_table(
            'experiment_status',
            [
                'exp_id integer PRIMARY KEY',
                'name text NOT NULL',
                'status text NOT NULL',
                'seconds_diff integer NOT NULL',
                'modified text NOT NULL',
                'FOREIGN KEY (exp_id) REFERENCES experiment (id)'
            ])
        self.as_times_db_manager.create_table(
            'experiment_times',
            [
                'exp_id integer PRIMARY KEY',
                'name text NOT NULL',
                'created int NOT NULL',
                'modified int NOT NULL',
                'total_jobs int NOT NULL',
                'completed_jobs int NOT NULL',
                'FOREIGN KEY (exp_id) REFERENCES experiment (id)'
            ]
        )
        self.as_times_db_manager.create_view('currently_running',
            'select s.name, s.status, t.total_jobs from experiment_status as s inner join experiment_times as t on s.name = t.name where s.status="RUNNING" ORDER BY t.total_jobs'
            )


