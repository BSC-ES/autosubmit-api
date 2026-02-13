from datetime import datetime, timedelta, timezone
from http import HTTPStatus
import random
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4
from fastapi.testclient import TestClient
import jwt
import pytest
from autosubmit_api import config
from autosubmit_api.models.requests import PAGINATION_LIMIT_DEFAULT
from autosubmit_api.repositories.runner_processes import RunnerProcessesDataModel
from tests.utils import custom_return_value


class TestCASV2Login:
    endpoint = "/v4/auth/cas/v2/login"

    def test_redirect(
        self, fixture_fastapi_client: TestClient, monkeypatch: pytest.MonkeyPatch
    ):
        random_url = f"https://${str(uuid4())}/"
        monkeypatch.setattr(config, "CAS_SERVER_URL", random_url)
        assert random_url == config.CAS_SERVER_URL

        response = fixture_fastapi_client.get(self.endpoint, follow_redirects=False)

        assert response.status_code in [HTTPStatus.FOUND, HTTPStatus.TEMPORARY_REDIRECT]
        assert response.has_redirect_location
        assert config.CAS_SERVER_URL in response.headers["Location"]

    def test_invalid_client(
        self, fixture_fastapi_client: TestClient, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(
            "autosubmit_api.auth.utils.validate_client", custom_return_value(False)
        )
        response = fixture_fastapi_client.get(self.endpoint, params={"service": "asd"})
        assert response.status_code == HTTPStatus.UNAUTHORIZED


class TestOIDCLogin:
    endpoint = "/v4/auth/oidc/login"

    def test_no_code(self, fixture_fastapi_client: TestClient):
        resp_obj = fixture_fastapi_client.get(
            self.endpoint, params={"redirect_uri": "foo"}
        ).json()
        assert resp_obj.get("authenticated") is False
        assert resp_obj.get("user") is None
        assert resp_obj.get("token") is None

    def test_valid(
        self, fixture_fastapi_client: TestClient, monkeypatch: pytest.MonkeyPatch
    ):
        username = str(uuid4())
        monkeypatch.setattr(
            "autosubmit_api.auth.oidc.oidc_token_exchange",
            custom_return_value(
                {
                    "access_token": "access",
                    "id_token": "id",
                }
            ),
        )
        monkeypatch.setattr(
            "autosubmit_api.auth.oidc.oidc_resolve_username",
            custom_return_value(username),
        )

        response = fixture_fastapi_client.get(
            self.endpoint,
            params={"code": "123", "redirect_uri": "foo"},
            follow_redirects=False,
        )
        resp_obj: dict = response.json()

        assert response.status_code == HTTPStatus.OK
        assert resp_obj.get("authenticated") is True
        assert resp_obj.get("user") == username
        assert resp_obj.get("token") is not None

    def test_no_username(
        self, fixture_fastapi_client: TestClient, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(
            "autosubmit_api.auth.oidc.oidc_token_exchange",
            custom_return_value(
                {
                    "access_token": "access",
                    "id_token": "id",
                }
            ),
        )
        monkeypatch.setattr(
            "autosubmit_api.auth.oidc.oidc_resolve_username", custom_return_value(None)
        )

        response = fixture_fastapi_client.get(
            self.endpoint,
            params={"code": "123", "redirect_uri": "foo"},
            follow_redirects=False,
        )
        resp_obj: dict = response.json()

        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert resp_obj.get("authenticated") is False
        assert resp_obj.get("user") is None
        assert resp_obj.get("token") is None


class TestJWTVerify:
    endpoint = "/v4/auth/verify-token"

    def test_unauthorized_no_token(self, fixture_fastapi_client: TestClient):
        response = fixture_fastapi_client.get(self.endpoint)
        resp_obj: dict = response.json()

        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert resp_obj.get("authenticated") is False
        assert resp_obj.get("user") is None

    def test_unauthorized_random_token(self, fixture_fastapi_client: TestClient):
        random_token = str(uuid4())
        response = fixture_fastapi_client.get(
            self.endpoint, headers={"Authorization": random_token}
        )
        resp_obj: dict = response.json()

        assert response.status_code == HTTPStatus.UNAUTHORIZED
        assert resp_obj.get("authenticated") is False
        assert resp_obj.get("user") is None

    def test_authorized(self, fixture_fastapi_client: TestClient):
        random_user = str(uuid4())
        payload = {
            "user_id": random_user,
            "sub": random_user,
            "iat": int(datetime.now().timestamp()),
            "exp": (
                datetime.now(timezone.utc)
                + timedelta(seconds=config.JWT_EXP_DELTA_SECONDS)
            ),
        }
        jwt_token = jwt.encode(payload, config.JWT_SECRET, config.JWT_ALGORITHM)

        response = fixture_fastapi_client.get(
            self.endpoint, headers={"Authorization": "Bearer " + jwt_token}
        )
        resp_obj: dict = response.json()

        assert response.status_code == HTTPStatus.OK
        assert resp_obj.get("authenticated") is True
        assert resp_obj.get("user") == random_user


class TestExperimentList:
    endpoint = "/v4/experiments"

    def test_page_size(self, fixture_fastapi_client: TestClient):
        # Default page size
        response = fixture_fastapi_client.get(self.endpoint)
        resp_obj: dict = response.json()
        assert resp_obj["pagination"]["page_size"] == PAGINATION_LIMIT_DEFAULT

        # Any page size
        page_size = random.randint(2, 100)
        response = fixture_fastapi_client.get(
            self.endpoint, params={"page_size": page_size}
        )
        resp_obj: dict = response.json()
        assert resp_obj["pagination"]["page_size"] == page_size

        # Unbounded page size
        response = fixture_fastapi_client.get(self.endpoint, params={"page_size": -1})
        resp_obj: dict = response.json()
        assert resp_obj["pagination"]["page_size"] is None
        assert (
            resp_obj["pagination"]["page_items"]
            == resp_obj["pagination"]["total_items"]
        )
        assert resp_obj["pagination"]["page"] == 1
        assert resp_obj["pagination"]["page"] == resp_obj["pagination"]["total_pages"]


class TestExperimentDetail:
    endpoint = "/v4/experiments/{expid}"

    def test_detail(self, fixture_fastapi_client: TestClient):
        expid = "a003"
        response = fixture_fastapi_client.get(self.endpoint.format(expid=expid))
        resp_obj: dict = response.json()

        assert resp_obj["id"] == 1
        assert resp_obj["name"] == expid
        assert (
            isinstance(resp_obj["description"], str)
            and len(resp_obj["description"]) > 0
        )
        assert (
            isinstance(resp_obj["autosubmit_version"], str)
            and len(resp_obj["autosubmit_version"]) > 0
        )


class TestExperimentJobs:
    endpoint = "/v4/experiments/{expid}/jobs"

    def test_quick(self, fixture_fastapi_client: TestClient):
        expid = "a003"
        response = fixture_fastapi_client.get(
            self.endpoint.format(expid=expid),
            params={"view": "quick"},
        )
        resp_obj: dict = response.json()

        assert len(resp_obj["jobs"]) == 8

        for job in resp_obj["jobs"]:
            assert isinstance(job, dict) and len(job.keys()) == 2
            assert isinstance(job["name"], str) and job["name"].startswith(expid)
            assert isinstance(job["status"], str)

    def test_base(self, fixture_fastapi_client: TestClient):
        expid = "a003"
        response = fixture_fastapi_client.get(
            self.endpoint.format(expid=expid),
            params={"view": "base"},
        )
        resp_obj: dict = response.json()

        assert len(resp_obj["jobs"]) == 8

        for job in resp_obj["jobs"]:
            assert isinstance(job, dict) and len(job.keys()) > 2
            assert isinstance(job["name"], str) and job["name"].startswith(expid)
            assert isinstance(job["status"], str)


class TestExperimentWrappers:
    endpoint = "/v4/experiments/{expid}/wrappers"

    def test_wrappers(self, fixture_fastapi_client: TestClient):
        expid = "a6zj"
        response = fixture_fastapi_client.get(self.endpoint.format(expid=expid))
        resp_obj: dict = response.json()

        assert isinstance(resp_obj, dict)
        assert isinstance(resp_obj["wrappers"], list)
        assert len(resp_obj["wrappers"]) == 1

        for wrapper in resp_obj["wrappers"]:
            assert isinstance(wrapper, dict)
            assert isinstance(wrapper["job_names"], list)
            assert isinstance(wrapper["wrapper_name"], str) and wrapper[
                "wrapper_name"
            ].startswith(expid)


class TestExperimentFSConfig:
    endpoint = "/v4/experiments/{expid}/filesystem-config"

    def test_fs_config(self, fixture_fastapi_client: TestClient):
        expid = "a6zj"
        response = fixture_fastapi_client.get(self.endpoint.format(expid=expid))
        resp_obj: dict = response.json()

        assert isinstance(resp_obj, dict)
        assert isinstance(resp_obj["config"], dict)
        assert (
            isinstance(resp_obj["config"]["contains_nones"], bool)
            and not resp_obj["config"]["contains_nones"]
        )
        assert isinstance(resp_obj["config"]["JOBS"], dict)
        assert isinstance(resp_obj["config"]["WRAPPERS"], dict)
        assert isinstance(resp_obj["config"]["WRAPPERS"]["WRAPPER_V"], dict)

    def test_fs_config_v3_retro(self, fixture_fastapi_client: TestClient):
        expid = "a3tb"
        response = fixture_fastapi_client.get(self.endpoint.format(expid=expid))
        resp_obj: dict = response.json()

        assert isinstance(resp_obj, dict)
        assert isinstance(resp_obj["config"], dict)

        ALLOWED_CONFIG_KEYS = ["conf", "exp", "jobs", "platforms", "proj"]
        assert len(resp_obj["config"].keys()) == len(ALLOWED_CONFIG_KEYS) + 1
        assert (
            isinstance(resp_obj["config"]["contains_nones"], bool)
            and not resp_obj["config"]["contains_nones"]
        )
        for key in ALLOWED_CONFIG_KEYS:
            assert key in resp_obj["config"]
            assert isinstance(resp_obj["config"][key], dict)


class TestExperimentRuns:
    endpoint = "/v4/experiments/{expid}/runs"

    @pytest.mark.parametrize("expid, num_runs", [("a6zj", 1), ("a3tb", 51)])
    def test_runs(self, expid: str, num_runs: int, fixture_fastapi_client: TestClient):
        response = fixture_fastapi_client.get(self.endpoint.format(expid=expid))
        resp_obj: dict = response.json()

        assert isinstance(resp_obj, dict)
        assert isinstance(resp_obj["runs"], list)
        assert len(resp_obj["runs"]) == num_runs

        for run in resp_obj["runs"]:
            assert isinstance(run, dict)
            assert isinstance(run["run_id"], int)
            assert isinstance(run["start"], str) or run["start"] is None
            assert isinstance(run["finish"], str) or run["finish"] is None


class TestExperimentRunConfig:
    endpoint = "/v4/experiments/{expid}/runs/{run_id}/config"

    def test_run_config(self, fixture_fastapi_client: TestClient):
        expid = "a6zj"
        run_id = 1
        response = fixture_fastapi_client.get(
            self.endpoint.format(expid=expid, run_id=run_id)
        )
        resp_obj: dict = response.json()

        assert isinstance(resp_obj, dict)
        assert isinstance(resp_obj["config"], dict)
        assert (
            isinstance(resp_obj["config"]["contains_nones"], bool)
            and not resp_obj["config"]["contains_nones"]
        )
        assert isinstance(resp_obj["config"]["JOBS"], dict)
        assert isinstance(resp_obj["config"]["WRAPPERS"], dict)
        assert isinstance(resp_obj["config"]["WRAPPERS"]["WRAPPER_V"], dict)

    @pytest.mark.parametrize("run_id", [51, 48, 31])
    def test_run_config_v3_retro(self, run_id: int, fixture_fastapi_client: TestClient):
        expid = "a3tb"
        response = fixture_fastapi_client.get(
            self.endpoint.format(expid=expid, run_id=run_id)
        )
        resp_obj: dict = response.json()

        assert isinstance(resp_obj, dict)
        assert isinstance(resp_obj["config"], dict)

        ALLOWED_CONFIG_KEYS = ["conf", "exp", "jobs", "platforms", "proj"]
        assert len(resp_obj["config"].keys()) == len(ALLOWED_CONFIG_KEYS) + 1
        assert (
            isinstance(resp_obj["config"]["contains_nones"], bool)
            and not resp_obj["config"]["contains_nones"]
        )
        for key in ALLOWED_CONFIG_KEYS:
            assert key in resp_obj["config"]
            assert isinstance(resp_obj["config"][key], dict)


class TestUserMetrics:
    endpoint = "/v4/experiments/{expid}/runs/{run_id}/user-metrics"

    @pytest.mark.parametrize(
        "expid, run_id, metrics_len, first_metric",
        [
            (
                "a6zj",
                1,
                1,
                {
                    "job_name": "a6zj_LOCAL_SETUP",
                    "metric_name": "metric1",
                    "metric_value": "123.45",
                },
            ),
            (
                "a6zj",
                3,
                2,
                {
                    "job_name": "a6zj_LOCAL_SETUP",
                    "metric_name": "metric1",
                    "metric_value": "234.56",
                },
            ),
        ],
    )
    def test_user_metrics(
        self,
        fixture_fastapi_client: TestClient,
        expid: str,
        run_id: int,
        metrics_len: int,
        first_metric: dict[str, Any],
    ):
        response = fixture_fastapi_client.get(
            self.endpoint.format(expid=expid, run_id=run_id)
        )
        resp_obj: dict = response.json()

        assert isinstance(resp_obj, dict)
        assert resp_obj["run_id"] == run_id

        assert isinstance(resp_obj["metrics"], list)
        assert len(resp_obj["metrics"]) == metrics_len
        assert isinstance(resp_obj["metrics"][0], dict)
        assert resp_obj["metrics"][0]["job_name"] == first_metric["job_name"]
        assert resp_obj["metrics"][0]["metric_name"] == first_metric["metric_name"]
        assert resp_obj["metrics"][0]["metric_value"] == first_metric["metric_value"]


class TestUserMetricsRuns:
    endpoint = "/v4/experiments/{expid}/user-metrics-runs"

    def test_user_metrics_runs(self, fixture_fastapi_client: TestClient):
        expid = "a6zj"
        response = fixture_fastapi_client.get(
            self.endpoint.format(expid=expid),
        )
        resp_obj: dict = response.json()

        assert isinstance(resp_obj, dict)
        assert isinstance(resp_obj["runs"], list)
        assert len(resp_obj["runs"]) == 2
        assert [obj["run_id"] for obj in resp_obj["runs"]] == [3, 1]


class TestUserPreferences:
    register_endpoint = "/v4/user-settings/preferred-username"
    get_endpoint = "/v4/user-settings/preferred-username"

    def _create_jwt_token(self, user_id: str) -> str:
        """Helper method to create a valid JWT token for testing"""
        payload = {
            "user_id": user_id,
            "sub": user_id,
            "iat": int(datetime.now().timestamp()),
            "exp": (
                datetime.now(timezone.utc)
                + timedelta(seconds=config.JWT_EXP_DELTA_SECONDS)
            ),
        }
        return jwt.encode(payload, config.JWT_SECRET, config.JWT_ALGORITHM)

    def test_register_preferred_username_unauthorized(
        self, fixture_fastapi_client: TestClient
    ):
        """Test that registering a username without authentication fails"""
        response = fixture_fastapi_client.post(
            self.register_endpoint,
            json={"preferred_username": "test_user"},
        )

        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_register_preferred_username_invalid_token(
        self, fixture_fastapi_client: TestClient
    ):
        """Test that registering with an invalid token fails"""
        response = fixture_fastapi_client.post(
            self.register_endpoint,
            json={"preferred_username": "test_user"},
            headers={"Authorization": "Bearer invalid_token"},
        )

        assert response.status_code == HTTPStatus.UNAUTHORIZED

    def test_register_preferred_username_success(
        self, fixture_fastapi_client: TestClient
    ):
        """Test successfully registering a preferred username"""
        user_id = str(uuid4())
        preferred_username = f"linux_user_{uuid4().hex[:8]}"
        jwt_token = self._create_jwt_token(user_id)

        # Test registration
        response = fixture_fastapi_client.post(
            self.register_endpoint,
            json={"preferred_username": preferred_username},
            headers={"Authorization": f"Bearer {jwt_token}"},
        )

        assert response.status_code == HTTPStatus.OK
        resp_obj: dict = response.json()

        assert resp_obj["user_id"] == user_id
        assert resp_obj["preferred_username"] == preferred_username
        assert isinstance(resp_obj["created"], str)
        assert isinstance(resp_obj["modified"], str)

        # Test retrieval
        get_response = fixture_fastapi_client.get(
            self.get_endpoint,
            headers={"Authorization": f"Bearer {jwt_token}"},
        )
        assert get_response.status_code == HTTPStatus.OK
        get_resp_obj: dict = get_response.json()
        assert get_resp_obj["user_id"] == user_id
        assert get_resp_obj["preferred_username"] == preferred_username
        assert isinstance(get_resp_obj["created"], str)
        assert isinstance(get_resp_obj["modified"], str)


class TestRunnerSetJobStatus:
    endpoint = "/v4/runners/command/set-job-status"

    def test_invalid_profile(self, fixture_fastapi_client: TestClient):
        response = fixture_fastapi_client.post(
            self.endpoint,
            json={
                "expid": "test_expid",
                "profile_name": "NON_EXISTENT_PROFILE",
                "command_params": {"final_status": "COMPLETED"},
            },
        )

        assert response.status_code != 200

    def test_valid_ssh_request(self, fixture_fastapi_client: TestClient):
        # Mock read_config_file to include SSH_AUTOSUBMIT_DEV profile
        # and get_runner to return a mock runner
        with (
            patch(
                "autosubmit_api.runners.runner_config.read_config_file"
            ) as mock_read_config,
            patch("autosubmit_api.routers.v4.runners.get_runner") as mock_get_runner,
        ):
            mock_read_config.return_value = {
                "RUNNER_CONFIGURATION": {
                    "PROFILES": {
                        "SSH_AUTOSUBMIT_DEV": {
                            "RUNNER_TYPE": "SSH",
                            "MODULE_LOADER_TYPE": "CONDA",
                            "MODULES": ["autosubmit"],
                            "SSH": {
                                "HOST": "bscesautosubmit03.bsc.es",
                                "PORT": 22,
                            },
                        }
                    }
                }
            }

            mock_runner = MagicMock()
            mock_runner.set_job_status = AsyncMock(return_value="None")
            mock_get_runner.return_value = mock_runner

            response = fixture_fastapi_client.post(
                self.endpoint,
                json={
                    "expid": "test_expid",
                    "profile_name": "SSH_AUTOSUBMIT_DEV",
                    "profile_params": {
                        "SSH": {
                            "USERNAME": "test_user",
                        }
                    },
                    "command_params": {
                        "final_status": "COMPLETED",
                        "job_names_list": ["JOB1", "JOB2"],
                    },
                },
            )

            assert response.status_code == 200


class TestRunnerRunExperiment:
    endpoint = "/v4/runners/command/run-experiment"

    def test_valid_ssh_request(self, fixture_fastapi_client: TestClient):
        with (
            patch(
                "autosubmit_api.runners.runner_config.read_config_file"
            ) as mock_read_config,
            patch("autosubmit_api.routers.v4.runners.get_runner") as mock_get_runner,
        ):
            mock_read_config.return_value = {
                "RUNNER_CONFIGURATION": {
                    "PROFILES": {
                        "SSH_AUTOSUBMIT_DEV": {
                            "RUNNER_TYPE": "SSH",
                            "MODULE_LOADER_TYPE": "CONDA",
                            "MODULES": ["autosubmit"],
                            "SSH": {
                                "HOST": "bscesautosubmit03.bsc.es",
                                "PORT": 22,
                            },
                        }
                    }
                }
            }

            mock_runner = MagicMock()
            mock_runner.run = AsyncMock(return_value="None")
            mock_get_runner.return_value = mock_runner

            response = fixture_fastapi_client.post(
                self.endpoint,
                json={
                    "expid": "test_expid",
                    "profile_name": "SSH_AUTOSUBMIT_DEV",
                    "profile_params": {
                        "SSH": {
                            "USERNAME": "test_user",
                        }
                    },
                },
            )
            assert response.status_code == 200


class TestRunnerGetRunnerRunStatus:
    endpoint = "/v4/runners/command/get-runner-run-status"

    def test_valid_request(self, fixture_fastapi_client: TestClient):
        with patch(
            "autosubmit_api.routers.v4.runners.create_runner_processes_repository"
        ) as mock_create_repo:
            mock_repo = MagicMock()
            mock_process = RunnerProcessesDataModel(
                id=1,
                expid="test_expid",
                pid=12345,
                status="RUNNING",
                runner="SSH",
                module_loader="CONDA",
                modules="autosubmit",
                created="2026-02-09T10:00:00",
                modified="2026-02-09T10:05:00",
            )

            mock_repo.get_last_process_by_expid.return_value = mock_process
            mock_create_repo.return_value = mock_repo

            response = fixture_fastapi_client.post(
                self.endpoint,
                json={"expid": "test_expid"},
            )

            assert response.status_code == 200
            resp_obj: dict = response.json()

            assert resp_obj["expid"] == mock_process.expid
            assert resp_obj["runner_id"] == mock_process.id
            assert resp_obj["runner"] == mock_process.runner
            assert resp_obj["module_loader"] == mock_process.module_loader
            assert resp_obj["modules"] == mock_process.modules
            assert resp_obj["status"] == mock_process.status
            assert resp_obj["pid"] == mock_process.pid
            assert resp_obj["created"] == mock_process.created
            assert resp_obj["modified"] == mock_process.modified

    def test_no_process_found(self, fixture_fastapi_client: TestClient):
        with patch(
            "autosubmit_api.routers.v4.runners.create_runner_processes_repository"
        ) as mock_create_repo:
            mock_repo = MagicMock()
            mock_repo.get_last_process_by_expid.return_value = None
            mock_create_repo.return_value = mock_repo

            response = fixture_fastapi_client.post(
                self.endpoint,
                json={"expid": "test_expid"},
            )

            assert response.status_code == 500


class TestRunnerStopExperiment:
    endpoint = "/v4/runners/command/stop-experiment"

    def test_valid_ssh_request(self, fixture_fastapi_client: TestClient):
        with patch(
            "autosubmit_api.routers.v4.runners.get_runner_from_expid"
        ) as mock_get_runner_from_expid:
            mock_runner = MagicMock()
            mock_runner.stop = AsyncMock(return_value="None")
            mock_get_runner_from_expid.return_value = mock_runner

            response = fixture_fastapi_client.post(
                self.endpoint,
                json={"expid": "test_expid"},
            )

            assert response.status_code == 200
            resp_obj: dict = response.json()
            assert resp_obj["message"] == "Experiment test_expid stopped successfully."

    def test_stop_failure(self, fixture_fastapi_client: TestClient):
        with patch(
            "autosubmit_api.routers.v4.runners.get_runner_from_expid"
        ) as mock_get_runner_from_expid:
            mock_get_runner_from_expid.side_effect = Exception("Runner not found")

            response = fixture_fastapi_client.post(
                self.endpoint,
                json={"expid": "test_expid"},
            )

            assert response.status_code == 500
