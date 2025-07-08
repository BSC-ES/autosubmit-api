from unittest.mock import patch

from fastapi.testclient import TestClient
from mock import AsyncMock, MagicMock


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
