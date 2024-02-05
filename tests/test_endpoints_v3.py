from datetime import datetime, timedelta
from http import HTTPStatus
from uuid import uuid4
from flask.testing import FlaskClient
import jwt
from autosubmit_api import config
import pytest
from autosubmit_api.config.basicConfig import APIBasicConfig


class TestLogin:
    endpoint = f"/v3/login"

    def test_not_allowed_client(
        self,
        fixture_client: FlaskClient,
        fixture_mock_basic_config: APIBasicConfig,
        monkeypatch: pytest.MonkeyPatch,
    ):
        monkeypatch.setattr(APIBasicConfig, "ALLOWED_CLIENTS", [])

        response = fixture_client.get(self.endpoint)
        resp_obj: dict = response.get_json()
        
        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert resp_obj.get("authenticated") == False

    def test_redirect(
        self,
        fixture_client: FlaskClient,
        fixture_mock_basic_config: APIBasicConfig,
        monkeypatch: pytest.MonkeyPatch,
    ): 
        random_referer = str(f"https://${str(uuid4())}/")
        monkeypatch.setattr(APIBasicConfig, "ALLOWED_CLIENTS", [random_referer])

        response = fixture_client.get(self.endpoint, headers={
            "Referer": random_referer
        })
        
        assert response.status_code == HTTPStatus.FOUND
        assert config.CAS_LOGIN_URL in response.location
        assert random_referer in response.location


class TestVerifyToken:
    def test_unauthorized_no_token(self, fixture_client: FlaskClient):
        response = fixture_client.get(f"/v3/tokentest")
        resp_obj: dict = response.get_json()

        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert resp_obj.get("isValid") == False

    def test_unauthorized_random_token(self, fixture_client: FlaskClient):
        random_token = str(uuid4())
        response = fixture_client.get(
            f"/v3/tokentest", headers={"Authorization": random_token}
        )
        resp_obj: dict = response.get_json()

        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert resp_obj.get("isValid") == False

    def test_authorized(self, fixture_client: FlaskClient):
        random_user = str(uuid4())
        payload = {
            "user_id": random_user,
            "exp": (
                datetime.utcnow() + timedelta(seconds=config.JWT_EXP_DELTA_SECONDS)
            ),
        }
        jwt_token = jwt.encode(payload, config.JWT_SECRET, config.JWT_ALGORITHM)

        response = fixture_client.get(
            f"/v3/tokentest", headers={"Authorization": jwt_token}
        )
        resp_obj: dict = response.get_json()

        assert response.status_code == HTTPStatus.OK
        assert resp_obj.get("isValid") == True


class TestPerformance:
    def test_parallelization(self, fixture_client: FlaskClient):
        """
        Test parallelization without PROCESSORS_PER_NODE
        """
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
        """
        Test parallelization that comes from default platform
        """
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
