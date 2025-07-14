from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from mock import AsyncMock, MagicMock


class TestCreateJobList:
    """Test suite for the create job list endpoint in v4alpha."""

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
        "params",
        [
            {"check_wrapper": True},
            {"check_wrapper": False, "update_version": True},
            {"check_wrapper": False, "force": True},
        ],
    )
    def test_enabled_runner(self, fixture_fastapi_client: TestClient, params: dict):
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
                    **params,
                },
            )

            assert response.status_code == 200

            mock_create_job_list.assert_awaited_once_with(
                RANDOM_EXPID,
                check_wrapper=params.get("check_wrapper"),
                update_version=params.get("update_version"),
                force=params.get("force"),
            )


class TestRunnerCreateExperiment:
    endpoint = "/v4alpha/runner-create-experiment"

    def test_disabled_runner(self, fixture_fastapi_client: TestClient):
        with patch(
            "autosubmit_api.routers.v4alpha.check_runner_permissions"
        ) as mock_check_permissions:
            mock_check_permissions.return_value = False
            response = fixture_fastapi_client.post(
                self.endpoint,
                json={
                    "runner": "local",
                    "module_loader": "no_module",
                    "modules": None,
                    "description": "Test experiment",
                },
            )

        assert response.status_code == 403

    def test_fail_create_job_list(self, fixture_fastapi_client: TestClient):
        with (
            patch(
                "autosubmit_api.routers.v4alpha.check_runner_permissions"
            ) as mock_check_permissions,
            patch("autosubmit_api.routers.v4alpha.get_runner") as mock_get_runner,
        ):
            mock_check_permissions.return_value = True
            mock_create_experiment = AsyncMock()
            mock_create_experiment.side_effect = Exception(
                "Failed to create experiment"
            )
            mock_runner = MagicMock()
            mock_runner.create_experiment = mock_create_experiment
            mock_get_runner.return_value = mock_runner

            response = fixture_fastapi_client.post(
                self.endpoint,
                json={
                    "runner": "local",
                    "module_loader": "no_module",
                    "modules": None,
                    "description": "Test experiment",
                },
            )

            assert response.status_code == 500

    def test_enabled_runner(self, fixture_fastapi_client: TestClient):
        with (
            patch(
                "autosubmit_api.routers.v4alpha.check_runner_permissions"
            ) as mock_check_permissions,
            patch("autosubmit_api.routers.v4alpha.get_runner") as mock_get_runner,
        ):
            mock_check_permissions.return_value = True

            mock_create_experiment = AsyncMock()
            mock_create_experiment.return_value = "test_expid"
            mock_runner = MagicMock()
            mock_runner.create_experiment = mock_create_experiment
            mock_get_runner.return_value = mock_runner

            response = fixture_fastapi_client.post(
                self.endpoint,
                json={
                    "runner": "local",
                    "module_loader": "no_module",
                    "modules": None,
                    "description": "Test experiment",
                },
            )
            resp_obj = response.json()

            assert response.status_code == 200

            mock_create_experiment.assert_awaited_once()

            assert resp_obj["expid"] == "test_expid"
