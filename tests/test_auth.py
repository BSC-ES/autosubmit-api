import pytest
from autosubmit_api.auth import AuthorizationLevels, with_auth_token
from autosubmit_api import auth
from tests.custom_utils import custom_return_value


def dummy_response(*args, **kwargs):
    return "Hello World!", 200


class TestCommonAuth:

    def test_levels_enum(self):
        assert AuthorizationLevels.ALL > AuthorizationLevels.WRITEONLY
        assert AuthorizationLevels.WRITEONLY > AuthorizationLevels.NONE

    def test_decorator(self, monkeypatch: pytest.MonkeyPatch):
        """
        Test different authorization levels. 
        Setting an AUTHORIZATION_LEVEL=ALL will protect all routes no matter it's protection level.
        If a route is set with level = NONE, will be always protected.
        """

        # Test on AuthorizationLevels.ALL
        monkeypatch.setattr(auth, "_parse_authorization_level_env",
                            custom_return_value(AuthorizationLevels.ALL))

        _, code = with_auth_token(
            level=AuthorizationLevels.ALL)(dummy_response)()
        assert code == 401

        _, code = with_auth_token(
            level=AuthorizationLevels.WRITEONLY)(dummy_response)()
        assert code == 401

        _, code = with_auth_token(
            level=AuthorizationLevels.NONE)(dummy_response)()
        assert code == 401

        # Test on AuthorizationLevels.WRITEONLY
        monkeypatch.setattr(auth, "_parse_authorization_level_env",
                            custom_return_value(AuthorizationLevels.WRITEONLY))

        _, code = with_auth_token(
            level=AuthorizationLevels.ALL)(dummy_response)()
        assert code == 200

        _, code = with_auth_token(
            level=AuthorizationLevels.WRITEONLY)(dummy_response)()
        assert code == 401

        _, code = with_auth_token(
            level=AuthorizationLevels.NONE)(dummy_response)()
        assert code == 401

        # Test on AuthorizationLevels.NONE
        monkeypatch.setattr(auth, "_parse_authorization_level_env",
                            custom_return_value(AuthorizationLevels.NONE))

        _, code = with_auth_token(
            level=AuthorizationLevels.ALL)(dummy_response)()
        assert code == 200

        _, code = with_auth_token(
            level=AuthorizationLevels.WRITEONLY)(dummy_response)()
        assert code == 200

        _, code = with_auth_token(
            level=AuthorizationLevels.NONE)(dummy_response)()
        assert code == 401
