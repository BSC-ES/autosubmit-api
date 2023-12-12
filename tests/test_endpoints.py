from flask.testing import FlaskClient

from autosubmit_api.experiment import common_requests
from autosubmit_api.performance.performance_metrics import PerformanceMetrics

from tests.common_fixtures import fixture_mock_basic_config, fixture_client, fixture_app
from tests.custom_utils import custom_return_value


class TestPerformance:
    def test_parallelization(
        self, fixture_mock_basic_config, fixture_client: FlaskClient
    ):
        expid = "a007"
        response = fixture_client.get(f"/v3/performance/{expid}")
        resp_obj: dict = response.get_json()
        assert resp_obj["Parallelization"] == 8

    def test_parallelization_platforms(
        self, fixture_mock_basic_config, fixture_client: FlaskClient
    ):
        expid = "a003"
        response = fixture_client.get(f"/v3/performance/{expid}")
        resp_obj: dict = response.get_json()
        assert resp_obj["Parallelization"] == 16


class TestTree:
    def test_minimal_conf(self, fixture_mock_basic_config, fixture_client: FlaskClient):
        expid = "a003"
        response = fixture_client.get(f"/v3/tree/{expid}")
        resp_obj: dict = response.get_json()

        assert resp_obj["total"] == 8
        assert resp_obj["error"] == False
