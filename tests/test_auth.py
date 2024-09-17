import os
from uuid import uuid4
import pytest
from autosubmit_api.auth import ProtectionLevels, with_auth_token
from autosubmit_api import auth
from autosubmit_api.auth.utils import validate_client
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api import config
from tests.utils import custom_return_value, dummy_response


class TestCommonAuth:
    def test_mock_env_protection_level(self):
        assert os.environ.get("PROTECTION_LEVEL") == "NONE"
        assert config.PROTECTION_LEVEL == "NONE"

    def test_levels_enum(self):
        assert ProtectionLevels.ALL > ProtectionLevels.WRITEONLY
        assert ProtectionLevels.WRITEONLY > ProtectionLevels.NONE

    def test_decorator(self, monkeypatch: pytest.MonkeyPatch):
        """
        Test different authorization levels.
        Setting an AUTHORIZATION_LEVEL=ALL will protect all routes no matter it's protection level.
        If a route is set with level = NONE, will be always protected.
        """

        # Test on AuthorizationLevels.ALL
        monkeypatch.setattr(
            auth,
            "_parse_protection_level_env",
            custom_return_value(ProtectionLevels.ALL),
        )

        _, code = with_auth_token(threshold=ProtectionLevels.ALL)(dummy_response)()
        assert code == 401

        _, code = with_auth_token(threshold=ProtectionLevels.WRITEONLY)(
            dummy_response
        )()
        assert code == 401

        _, code = with_auth_token(threshold=ProtectionLevels.NONE)(dummy_response)()
        assert code == 401

        # Test on AuthorizationLevels.WRITEONLY
        monkeypatch.setattr(
            auth,
            "_parse_protection_level_env",
            custom_return_value(ProtectionLevels.WRITEONLY),
        )

        _, code = with_auth_token(threshold=ProtectionLevels.ALL)(dummy_response)()
        assert code == 200

        _, code = with_auth_token(threshold=ProtectionLevels.WRITEONLY)(
            dummy_response
        )()
        assert code == 401

        _, code = with_auth_token(threshold=ProtectionLevels.NONE)(dummy_response)()
        assert code == 401

        # Test on AuthorizationLevels.NONE
        monkeypatch.setattr(
            auth,
            "_parse_protection_level_env",
            custom_return_value(ProtectionLevels.NONE),
        )

        _, code = with_auth_token(threshold=ProtectionLevels.ALL)(dummy_response)()
        assert code == 200

        _, code = with_auth_token(threshold=ProtectionLevels.WRITEONLY)(
            dummy_response
        )()
        assert code == 200

        _, code = with_auth_token(threshold=ProtectionLevels.NONE)(dummy_response)()
        assert code == 401

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
