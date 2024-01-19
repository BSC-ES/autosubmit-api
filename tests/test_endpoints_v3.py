from flask.testing import FlaskClient

from tests.common_fixtures import fixture_mock_basic_config, fixture_client, fixture_app


class TestPerformance:
    def test_parallelization(self, fixture_client: FlaskClient):
        expid = "a007"
        response = fixture_client.get(f"/v3/performance/{expid}")
        resp_obj: dict = response.get_json()
        assert resp_obj["error"] == False
        assert resp_obj["Parallelization"] == 8

        expid = "a3tb"
        response = fixture_client.get(f"/v3/performance/{expid}")
        resp_obj: dict = response.get_json()
        assert resp_obj["error"] == False
        assert resp_obj["Parallelization"] == 768

    def test_parallelization_platforms(self, fixture_client: FlaskClient):
        expid = "a003"
        response = fixture_client.get(f"/v3/performance/{expid}")
        resp_obj: dict = response.get_json()
        assert resp_obj["error"] == False
        assert resp_obj["Parallelization"] == 16


class TestTree:
    def test_tree(self, fixture_client: FlaskClient):
        expid = "a003"
        response = fixture_client.get(f"/v3/tree/{expid}")
        resp_obj: dict = response.get_json()

        assert resp_obj["error"] == False
        assert resp_obj["total"] == 8


class TestQuick:
    def test_quick(self, fixture_client: FlaskClient):
        expid = "a007"
        response = fixture_client.get(f"/v3/quick/{expid}")
        resp_obj: dict = response.get_json()

        assert resp_obj["error"] == False
        assert resp_obj["total"] == len(resp_obj["tree_view"])
        assert resp_obj["total"] == len(resp_obj["view_data"])


class TestGraph:
    def test_graph(self, fixture_client: FlaskClient):
        expid = "a003"
        response = fixture_client.get(f"/v3/graph/{expid}/standard/none")
        resp_obj: dict = response.get_json()

        assert resp_obj["error"] == False
        assert resp_obj["total_jobs"] == len(resp_obj["nodes"])


class TestExpCount:
    def test_exp_count(self, fixture_client: FlaskClient):
        expid = "a007"
        response = fixture_client.get(f"/v3/expcount/{expid}")
        resp_obj: dict = response.get_json()

        assert resp_obj["error"] == False
        assert resp_obj["total"] == sum(
            [resp_obj["counters"][key] for key in resp_obj["counters"]]
        )
        assert resp_obj["expid"] == expid


class TestSummary:
    def test_summary(self, fixture_client: FlaskClient):
        expid = "a007"
        response = fixture_client.get(f"/v3/summary/{expid}")
        resp_obj: dict = response.get_json()

        assert resp_obj["error"] == False
        assert resp_obj["n_sim"] > 0
