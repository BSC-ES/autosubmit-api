from unittest.mock import patch
from fastapi.testclient import TestClient
from mock import MagicMock, AsyncMock
import pytest


class TestCASV2Login:
    endpoint = "/v4alpha/experiments/{expid}/create-job-list"

    def test_disabled_runner(self, fixture_fastapi_client: TestClient):
        RANDOM_EXPID = "foobar1234567890"

        with patch(
            "autosubmit_api.routers.v4alpha.check_runner_permissions"
        ) as mock_check_permissions:
            mock_check_permissions.return_value = False
            response = fixture_fastapi_client.post(
                self.endpoint.format(expid=RANDOM_EXPID),
                json={
                    "runner": "local",
                    "module_loader": "no_module",
                    "modules": None,
                },
            )

        assert response.status_code == 403

    def test_fail_create_job_list(self, fixture_fastapi_client: TestClient):
        RANDOM_EXPID = "foobar1234567890"

        with (
            patch(
                "autosubmit_api.routers.v4alpha.check_runner_permissions"
            ) as mock_check_permissions,
            patch("autosubmit_api.routers.v4alpha.get_runner") as mock_get_runner,
        ):
            mock_check_permissions.return_value = True
            mock_create_job_list = AsyncMock()
            mock_create_job_list.side_effect = Exception("Failed to create job list")
            mock_runner = MagicMock()
            mock_runner.create_job_list = mock_create_job_list
            mock_get_runner.return_value = mock_runner

            response = fixture_fastapi_client.post(
                self.endpoint.format(expid=RANDOM_EXPID),
                json={
                    "runner": "local",
                    "module_loader": "no_module",
                    "modules": None,
                },
            )

            assert response.status_code == 500

    @pytest.mark.parametrize(
        "check_wrapper",
        [True, False],
    )
    def test_enabled_runner(
        self, fixture_fastapi_client: TestClient, check_wrapper: bool
    ):
        RANDOM_EXPID = "foobar1234567890"

        with (
            patch(
                "autosubmit_api.routers.v4alpha.check_runner_permissions"
            ) as mock_check_permissions,
            patch("autosubmit_api.routers.v4alpha.get_runner") as mock_get_runner,
        ):
            mock_check_permissions.return_value = True

            mock_create_job_list = AsyncMock()
            mock_runner = MagicMock()
            mock_runner.create_job_list = mock_create_job_list
            mock_get_runner.return_value = mock_runner

            response = fixture_fastapi_client.post(
                self.endpoint.format(expid=RANDOM_EXPID),
                json={
                    "runner": "local",
                    "module_loader": "no_module",
                    "modules": None,
                    "check_wrapper": check_wrapper,
                },
            )

            assert response.status_code == 200

            mock_create_job_list.assert_awaited_once_with(RANDOM_EXPID, check_wrapper)
