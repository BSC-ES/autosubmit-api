import pytest
from autosubmit_api.auth import ProtectionLevels, with_auth_token
from autosubmit_api import auth
from tests.custom_utils import custom_return_value, dummy_response


class TestCommonAuth:
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
