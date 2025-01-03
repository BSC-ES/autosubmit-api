from unittest.mock import patch
from autosubmit_api.experiment.common_requests import get_experiment_data


class TestGetExperimentData:
    def test_valid(self, fixture_mock_basic_config):
        expid = "a1ve"
        result = get_experiment_data(expid)

        assert result.get("expid") == expid
        assert result.get("description") == "networkx pkl"
        assert result.get("total_jobs") == 8
        assert result.get("completed_jobs") == 8
        assert result.get("path") != "NA"
        assert len(result.get("time_last_access")) > 0

    def test_fail_as_conf(self, fixture_mock_basic_config):
        """
        When experiment is archived, the AutosubmitConfigurationFacadeBuilder will raise
        an exception because the experiment directory is not found.
        """
        expid = "a1ve"

        with patch(
            "autosubmit_api.experiment.common_requests.AutosubmitConfigurationFacadeBuilder"
        ) as mock:
            mock.side_effect = Exception("AutosubmitConfig failed")
            result = get_experiment_data(expid)

            assert result.get("expid") == expid
            assert result.get("description") == "networkx pkl"
            assert result.get("total_jobs") == 8
            assert result.get("completed_jobs") == 8

            # Failed ones giving default values
            assert result.get("path") == "NA"
            assert len(result.get("time_last_access")) == 0

    def test_dbs_missing(self, fixture_mock_basic_config):
        expid = "a1ve"

        with patch(
            "autosubmit_api.experiment.common_requests.create_experiment_repository"
        ) as exp_repo_mock, patch(
            "autosubmit_api.experiment.common_requests.DbRequests"
        ) as dbrequests_mock, patch(
            "autosubmit_api.experiment.common_requests.ExperimentHistoryBuilder"
        ) as history_mock:
            exp_repo_mock.side_effect = Exception("Experiment repository failed")
            dbrequests_mock.get_specific_experiment_status.side_effect = Exception(
                "Experiment status failed"
            )
            history_mock.side_effect = Exception("Experiment history failed")

            result = get_experiment_data(expid)

            # Successful ones
            assert result.get("expid") == expid
            assert result.get("path") != "NA"
            assert len(result.get("time_last_access")) > 0

            # Failed ones giving default values
            assert result.get("description") == ""
            assert result.get("total_jobs") == 0
            assert result.get("completed_jobs") == 0
