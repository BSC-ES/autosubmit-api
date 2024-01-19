import random
from flask.testing import FlaskClient
from autosubmit_api.views.v4 import PAGINATION_LIMIT_DEFAULT

from tests.common_fixtures import fixture_mock_basic_config, fixture_client, fixture_app


class TestExperimentList:
    def test_page_size(self, fixture_client: FlaskClient):
        # Default page size
        response = fixture_client.get(f"/v4/experiments")
        resp_obj: dict = response.get_json()
        assert resp_obj["pagination"]["page_size"] == PAGINATION_LIMIT_DEFAULT

        # Any page size
        page_size = random.randint(2, 100)
        response = fixture_client.get(f"/v4/experiments?page_size={str(page_size)}")
        resp_obj: dict = response.get_json()
        assert resp_obj["pagination"]["page_size"] == page_size

        # Unbounded page size
        response = fixture_client.get(f"/v4/experiments?page_size=-1")
        resp_obj: dict = response.get_json()
        assert resp_obj["pagination"]["page_size"] == None
        assert (
            resp_obj["pagination"]["page_items"]
            == resp_obj["pagination"]["total_items"]
        )
        assert resp_obj["pagination"]["page"] == 1
        assert resp_obj["pagination"]["page"] == resp_obj["pagination"]["total_pages"]
