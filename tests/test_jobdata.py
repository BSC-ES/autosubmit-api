from autosubmit_api.database.db_jobdata import JobDataStructure, ExperimentRun


class TestJobDataStructure:
    def test_valid_operations(self, fixture_mock_basic_config):
        expid = "a003"
        job_data_db = JobDataStructure(expid, None)

        last_exp_run = job_data_db.get_max_id_experiment_run()

        assert isinstance(last_exp_run, ExperimentRun)
        assert last_exp_run.run_id == 3
        assert last_exp_run.total == 8

        exp_run = job_data_db.get_experiment_run_by_id(2)
        assert isinstance(exp_run, ExperimentRun)
        assert exp_run.run_id == 2
        assert exp_run.total == 8

        # Run greater that the last one
        exp_run = job_data_db.get_experiment_run_by_id(4)
        assert exp_run is None

        job_data = job_data_db.get_current_job_data(3)
        assert isinstance(job_data, list)
        assert len(job_data) == 8

    def test_invalid_operations(self, fixture_mock_basic_config):
        expid = "404"
        job_data_db = JobDataStructure(expid, None)

        last_exp_run = job_data_db.get_max_id_experiment_run()
        assert last_exp_run is None

        exp_run = job_data_db.get_experiment_run_by_id(2)
        assert exp_run is None
