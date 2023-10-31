from autosubmit_api.builders.joblist_helper_builder import JobListHelperBuilder, JobListHelperDirector
from autosubmit_api.performance.performance_metrics import PerformanceMetrics

from tests.common_fixtures import fixture_mock_basic_config

class TestPerformance:

    def test_parallelization(self, fixture_mock_basic_config: fixture_mock_basic_config):
        expid = "a007"
        result = PerformanceMetrics(expid, JobListHelperDirector(JobListHelperBuilder(expid)).build_job_list_helper()).to_json()
        assert result["Parallelization"] == 8