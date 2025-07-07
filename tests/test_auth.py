import os
from typing import Any, Dict, Optional
from uuid import uuid4
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
import jwt
import pytest
from unittest.mock import patch
from autosubmit_api.auth.oidc import oidc_token_exchange, oidc_resolve_username
from autosubmit_api.auth import ProtectionLevels, auth_token_dependency
from autosubmit_api import auth
from autosubmit_api.auth.utils import validate_client, generate_jwt_token
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api import config
from tests.utils import custom_return_value


class TestCommonAuth:
    def test_mock_env_protection_level(self):
        assert os.environ.get("PROTECTION_LEVEL") == "NONE"
        assert config.PROTECTION_LEVEL == "NONE"

    def test_levels_enum(self):
        assert ProtectionLevels.ALL > ProtectionLevels.WRITEONLY
        assert ProtectionLevels.WRITEONLY > ProtectionLevels.NONE

    @pytest.mark.asyncio
    async def test_dependency(self, monkeypatch: pytest.MonkeyPatch):
        """
        Test different authorization levels.
        Setting an AUTHORIZATION_LEVEL=ALL will protect all routes no matter it's protection level.
        If a route is set with level = NONE, will be always protected.
        """

        # Invalid credentials
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="invalid_token"
        )

        # Test on AuthorizationLevels.ALL
        monkeypatch.setattr(
            auth,
            "_parse_protection_level_env",
            custom_return_value(ProtectionLevels.ALL),
        )

        with pytest.raises(HTTPException):
            await auth_token_dependency(threshold=ProtectionLevels.ALL)(credentials)

        with pytest.raises(HTTPException):
            await auth_token_dependency(threshold=ProtectionLevels.WRITEONLY)(
                credentials
            )

        with pytest.raises(HTTPException):
            await auth_token_dependency(threshold=ProtectionLevels.NONE)(credentials)

        # Test on AuthorizationLevels.WRITEONLY
        monkeypatch.setattr(
            auth,
            "_parse_protection_level_env",
            custom_return_value(ProtectionLevels.WRITEONLY),
        )

        assert (
            await auth_token_dependency(threshold=ProtectionLevels.ALL)(credentials)
            is None
        )

        with pytest.raises(HTTPException):
            await auth_token_dependency(threshold=ProtectionLevels.WRITEONLY)(
                credentials
            )

        with pytest.raises(HTTPException):
            await auth_token_dependency(threshold=ProtectionLevels.NONE)(credentials)

        # Test on AuthorizationLevels.NONE
        monkeypatch.setattr(
            auth,
            "_parse_protection_level_env",
            custom_return_value(ProtectionLevels.NONE),
        )

        assert (
            await auth_token_dependency(threshold=ProtectionLevels.ALL)(credentials)
            is None
        )

        assert (
            await auth_token_dependency(threshold=ProtectionLevels.WRITEONLY)(
                credentials
            )
            is None
        )

        with pytest.raises(HTTPException):
            await auth_token_dependency(threshold=ProtectionLevels.NONE)(credentials)

    def test_validate_client(
        self, monkeypatch: pytest.MonkeyPatch, fixture_mock_basic_config
    ):
        # No ALLOWED_CLIENTS
        monkeypatch.setattr(APIBasicConfig, "ALLOWED_CLIENTS", [])
        assert validate_client(str(uuid4())) is False

        # Wildcard ALLOWED_CLIENTS
        monkeypatch.setattr(APIBasicConfig, "ALLOWED_CLIENTS", ["*"])
        assert validate_client(str(uuid4())) is True

        # Registered client. The received with longer path
        random_client = str(uuid4())
        monkeypatch.setattr(APIBasicConfig, "ALLOWED_CLIENTS", [random_client])
        assert validate_client(random_client + str(uuid4())) is True


def test_generate_jwt_token():
    token = generate_jwt_token("test_user")

    assert isinstance(token, str)
    assert len(token.split(".")) == 3

    token_content = jwt.decode(token, config.JWT_SECRET, config.JWT_ALGORITHM)
    assert token_content["user_id"] == "test_user"
    assert token_content["sub"] == "test_user"
    assert isinstance(token_content["iat"], int)
    assert isinstance(token_content["exp"], int)
    assert token_content["exp"] > token_content["iat"]


class TestOIDC:
    def test_oidc_token_exchange(self):
        code = "test_code"
        redirect_uri = "http://localhost/callback"

        expected_headers = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        with patch("autosubmit_api.auth.oidc.requests.post") as mock_post:
            mock_post.return_value.json.return_value = {"access_token": "test_token"}

            # Call the function
            response = oidc_token_exchange(code, redirect_uri)

            # Assert requests.post was called with the correct arguments
            mock_post.call_args[1]["headers"] = expected_headers

            called_data = mock_post.call_args[1]["data"]
            assert f"code={code}" in called_data
            assert f"redirect_uri={redirect_uri}" in called_data
            assert f"client_id={config.OIDC_CLIENT_ID}" in called_data
            assert f"client_secret={config.OIDC_CLIENT_SECRET}" in called_data
            assert "grant_type=authorization_code" in called_data

            # Assert the response is as expected
            assert response == {"access_token": "test_token"}

    @pytest.mark.parametrize(
        "id_token_content, oidc_username_claim, expected_username",
        [
            ({"sub": "test_user"}, None, "test_user"),
            ({"sub": "test_user2"}, "sub", "test_user2"),
            ({"email": "test_email"}, "email", "test_email"),
            ({"sub": "test_user"}, "invalid", None),
        ],
    )
    def test_oidc_resolve_username_from_id_token(
        self,
        id_token_content: Dict[str, Any],
        oidc_username_claim: Optional[str],
        expected_username: Optional[str],
    ):
        """
        Test where OIDC_USERNAME_SOURCE="id_token" and
        parametrized OIDC_USERNAME_CLAIM
        """

        id_token = jwt.encode(id_token_content, "test_secret", algorithm="HS256")

        with patch("autosubmit_api.auth.oidc.config") as mock_config:
            mock_config.OIDC_USERNAME_SOURCE = "id_token"
            mock_config.OIDC_USERNAME_CLAIM = oidc_username_claim

            username = oidc_resolve_username(id_token, "test_access_token")

            assert username == expected_username

    @pytest.mark.parametrize(
        "user_info, oidc_username_claim, expected_username",
        [
            ({"sub": "test_user"}, None, "test_user"),
            ({"sub": "test_user2"}, "sub", "test_user2"),
            ({"email": "test_email"}, "email", "test_email"),
            ({"sub": "test_user"}, "invalid", None),
        ],
    )
    def test_oidc_resolve_username_from_userinfo(
        self,
        user_info: Dict[str, Any],
        oidc_username_claim: Optional[str],
        expected_username: Optional[str],
    ):
        """
        Test where OIDC_USERNAME_SOURCE="userinfo" and
        parametrized OIDC_USERNAME_CLAIM
        """

        access_token = "test_token"

        with patch("autosubmit_api.auth.oidc.config") as mock_config:
            mock_config.OIDC_USERNAME_SOURCE = "userinfo"
            mock_config.OIDC_USERNAME_CLAIM = oidc_username_claim

            with patch("autosubmit_api.auth.oidc.requests.get") as mock_get:
                mock_get.return_value.json.return_value = user_info

                username = oidc_resolve_username("test_id_token", access_token)

                assert mock_get.call_args[1]["headers"] == {
                    "Authorization": f"Bearer {access_token}"
                }

                assert username == expected_username


@pytest.mark.parametrize(
    "secret_token, input_token, expected_result",
    [
        ("my_secret", "my_secret", True),
        ("my_secret", "wrong_secret", False),
        ("wrong_secret", "my_secret", False),
        ("", "", False),  # Empty secret_token
        (None, "my_secret", False),
        (12345, "my_secret", False),  # Non-string secret_token
        ("my_secret", None, False),  # None input_token
        ("my_secret", 12345, False),  # Non-string input_token
        (12345, 12345, False),  # Both non-string
    ],
)
def test_verify_secret_token(
    secret_token: Any,
    input_token: Any,
    expected_result: bool,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setattr("autosubmit_api.config.AS_API_SECRET_TOKEN", secret_token)
    assert auth.verify_secret_token(input_token) is expected_result
