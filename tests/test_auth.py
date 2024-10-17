import os
from uuid import uuid4
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
import pytest
from autosubmit_api.auth import ProtectionLevels, auth_token_dependency
from autosubmit_api import auth
from autosubmit_api.auth.utils import validate_client
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
