from datetime import datetime, timedelta
from http import HTTPStatus
import random
from uuid import uuid4
from flask.testing import FlaskClient
import jwt
import pytest
from autosubmit_api import config
from autosubmit_api.views.v4 import PAGINATION_LIMIT_DEFAULT
from tests.custom_utils import custom_return_value


class TestCASV2Login:
    endpoint = f"/v4/auth/cas/v2/login"

    def test_redirect(
        self, fixture_client: FlaskClient, monkeypatch: pytest.MonkeyPatch
    ):
        random_url = f"https://${str(uuid4())}/"
        monkeypatch.setattr(config, "CAS_SERVER_URL", random_url)
        assert random_url == config.CAS_SERVER_URL

        response = fixture_client.get(self.endpoint)

        assert response.status_code == HTTPStatus.FOUND
        assert config.CAS_SERVER_URL in response.location

    def test_invalid_client(
        self, fixture_client: FlaskClient, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr("autosubmit_api.views.v4.validate_client", custom_return_value(False))
        response = fixture_client.get(self.endpoint, query_string={
            "service": "asd"
        })
        assert response.status_code == HTTPStatus.UNAUTHORIZED

class TestJWTVerify:
    endpoint = f"/v4/auth/verify-token"

    def test_unauthorized_no_token(self, fixture_client: FlaskClient):
        response = fixture_client.get(self.endpoint)
        resp_obj: dict = response.get_json()

        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert resp_obj.get("authenticated") == False
        assert resp_obj.get("user") == None

    def test_unauthorized_random_token(self, fixture_client: FlaskClient):
        random_token = str(uuid4())
        response = fixture_client.get(
            self.endpoint, headers={"Authorization": random_token}
        )
        resp_obj: dict = response.get_json()

        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert resp_obj.get("authenticated") == False
        assert resp_obj.get("user") == None

    def test_authorized(self, fixture_client: FlaskClient):
        random_user = str(uuid4())
        payload = {
            "user_id": random_user,
            "sub": random_user,
            "iat": int(datetime.now().timestamp()),
            "exp": (
                datetime.utcnow() + timedelta(seconds=config.JWT_EXP_DELTA_SECONDS)
            ),
        }
        jwt_token = jwt.encode(payload, config.JWT_SECRET, config.JWT_ALGORITHM)

        response = fixture_client.get(
            self.endpoint, headers={"Authorization": jwt_token}
        )
        resp_obj: dict = response.get_json()

        assert response.status_code == HTTPStatus.OK
        assert resp_obj.get("authenticated") == True
        assert resp_obj.get("user") == random_user


class TestExperimentList:
    endpoint = f"/v4/experiments"

    def test_page_size(self, fixture_client: FlaskClient):
        # Default page size
        response = fixture_client.get(self.endpoint)
        resp_obj: dict = response.get_json()
        assert resp_obj["pagination"]["page_size"] == PAGINATION_LIMIT_DEFAULT

        # Any page size
        page_size = random.randint(2, 100)
        response = fixture_client.get(
            self.endpoint, query_string={"page_size": page_size}
        )
        resp_obj: dict = response.get_json()
        assert resp_obj["pagination"]["page_size"] == page_size

        # Unbounded page size
        response = fixture_client.get(self.endpoint, query_string={"page_size": -1})
        resp_obj: dict = response.get_json()
        assert resp_obj["pagination"]["page_size"] == None
        assert (
            resp_obj["pagination"]["page_items"]
            == resp_obj["pagination"]["total_items"]
        )
        assert resp_obj["pagination"]["page"] == 1
        assert resp_obj["pagination"]["page"] == resp_obj["pagination"]["total_pages"]
