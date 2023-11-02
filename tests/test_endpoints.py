import json
import logging

import pytest
from autosubmit_api.builders.joblist_helper_builder import JobListHelperBuilder, JobListHelperDirector
from autosubmit_api.experiment import common_requests, common_db_requests
from autosubmit_api.performance.performance_metrics import PerformanceMetrics

from tests.common_fixtures import fixture_mock_basic_config
from tests.custom_utils import custom_return_value

class TestPerformance:

    def test_parallelization(self, fixture_mock_basic_config: fixture_mock_basic_config):
        expid = "a007"
        result = PerformanceMetrics(expid, JobListHelperDirector(JobListHelperBuilder(expid)).build_job_list_helper()).to_json()
        assert result["Parallelization"] == 8


class TestTree:

    def test_minimal_conf(self, fixture_mock_basic_config: fixture_mock_basic_config):
        expid = "a003"
        result = common_requests.get_experiment_tree_structured(expid, logging)

        assert result.get("total") == 8
        assert result.get("error") == False