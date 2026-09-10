import os
from typing import Optional
from dotenv import load_dotenv

from autosubmit_api.config.config_file import read_config_file

load_dotenv()


class AutosubmitAPIConfig:
    """
    A configuration class for the Autosubmit API. It supports
    reading configuration values from environment variables and a config file.
    Sensitive configuration might be only available in the env variables.
    """

    def __init__(self):
        self.read_config_file()

    def read_config_file(self):
        self._config_file_content = read_config_file()

    def _get_from_env(self, key: str, default=None):
        return os.environ.get(key, default)

    def _get_from_file(self, key: tuple[str], default=None):
        """
        Get a value from the config file content.

        :params key: Multi-level key to retrieve the value.
        :params default: Default value if the key is not found.
        """
        value = self._config_file_content
        for k in key:
            value = value.get(k, {})
        return value if value else default

    @property
    def PROTECTION_LEVEL(self) -> Optional[str]:
        value = self._get_from_env("PROTECTION_LEVEL")
        if value is None:
            value = self._get_from_file(("SECURITY", "PROTECTION_LEVEL"))
        return value

    @property
    def JWT_SECRET(self) -> str:
        """WARNING: Always provide a SECRET_KEY for production"""
        return self._get_from_env(
            "SECRET_KEY",
            "M87;Z$,o5?MSC(/@#-LbzgE3PH-5ki.ZvS}N.s09v>I#v8I'00THrA-:ykh3HX?",
        )

    @property
    def JWT_ALGORITHM(self) -> str:
        return self._get_from_env("JWT_ALGORITHM", "HS256")

    @property
    def JWT_EXP_DELTA_SECONDS(self) -> int:
        return self._get_from_env("JWT_EXP_DELTA_SECONDS", 84000 * 5)  # Default 5 days

    @property
    def CAS_SERVER_URL(self) -> str:
        return self._get_from_env("CAS_SERVER_URL", "")

    @property
    def CAS_LOGIN_URL(self) -> str:
        """e.g: https://cas.bsc.es/cas/login"""
        return self._get_from_env(
            "CAS_LOGIN_URL",
            (f"{self.CAS_SERVER_URL}login") if self.CAS_SERVER_URL else "",
        )

    @property
    def CAS_VERIFY_URL(self) -> str:
        """e.g: https://cas.bsc.es/cas/serviceValidate"""
        return self._get_from_env(
            "CAS_VERIFY_URL",
            (f"{self.CAS_SERVER_URL}serviceValidate") if self.CAS_SERVER_URL else "",
        )

    @property
    def GITHUB_OAUTH_CLIENT_ID(self) -> Optional[str]:
        return self._get_from_env("GITHUB_OAUTH_CLIENT_ID")

    @property
    def GITHUB_OAUTH_CLIENT_SECRET(self) -> Optional[str]:
        return self._get_from_env("GITHUB_OAUTH_CLIENT_SECRET")

    @property
    def GITHUB_OAUTH_WHITELIST_ORGANIZATION(self) -> Optional[str]:
        return self._get_from_env("GITHUB_OAUTH_WHITELIST_ORGANIZATION")

    @property
    def GITHUB_OAUTH_WHITELIST_TEAM(self) -> Optional[str]:
        return self._get_from_env("GITHUB_OAUTH_WHITELIST_TEAM")

    @property
    def OIDC_TOKEN_URL(self) -> Optional[str]:
        return self._get_from_env("OIDC_TOKEN_URL")

    @property
    def OIDC_CLIENT_ID(self) -> Optional[str]:
        return self._get_from_env("OIDC_CLIENT_ID")

    @property
    def OIDC_CLIENT_SECRET(self) -> Optional[str]:
        return self._get_from_env("OIDC_CLIENT_SECRET")

    @property
    def OIDC_USERNAME_SOURCE(self) -> Optional[str]:
        return self._get_from_env("OIDC_USERNAME_SOURCE")

    @property
    def OIDC_USERNAME_CLAIM(self) -> Optional[str]:
        return self._get_from_env("OIDC_USERNAME_CLAIM")

    @property
    def OIDC_USERINFO_URL(self) -> Optional[str]:
        return self._get_from_env("OIDC_USERINFO_URL")


as_api_config = AutosubmitAPIConfig()


# Auth
PROTECTION_LEVEL = as_api_config.PROTECTION_LEVEL
JWT_SECRET = as_api_config.JWT_SECRET
JWT_ALGORITHM = as_api_config.JWT_ALGORITHM
JWT_EXP_DELTA_SECONDS = as_api_config.JWT_EXP_DELTA_SECONDS

# CAS Stuff
CAS_SERVER_URL = as_api_config.CAS_SERVER_URL
CAS_LOGIN_URL = as_api_config.CAS_LOGIN_URL
CAS_VERIFY_URL = as_api_config.CAS_VERIFY_URL

# GitHub Oauth App
GITHUB_OAUTH_CLIENT_ID = as_api_config.GITHUB_OAUTH_CLIENT_ID
GITHUB_OAUTH_CLIENT_SECRET = as_api_config.GITHUB_OAUTH_CLIENT_SECRET
GITHUB_OAUTH_WHITELIST_ORGANIZATION = as_api_config.GITHUB_OAUTH_WHITELIST_ORGANIZATION
GITHUB_OAUTH_WHITELIST_TEAM = as_api_config.GITHUB_OAUTH_WHITELIST_TEAM

# OpenID Connect
OIDC_TOKEN_URL = as_api_config.OIDC_TOKEN_URL
OIDC_CLIENT_ID = as_api_config.OIDC_CLIENT_ID
OIDC_CLIENT_SECRET = as_api_config.OIDC_CLIENT_SECRET

OIDC_USERNAME_SOURCE = as_api_config.OIDC_USERNAME_SOURCE
OIDC_USERNAME_CLAIM = as_api_config.OIDC_USERNAME_CLAIM
OIDC_USERINFO_URL = as_api_config.OIDC_USERINFO_URL


# Startup options
def get_run_background_tasks_on_start():
    return os.environ.get("RUN_BACKGROUND_TASKS_ON_START") in [
        "True",
        "T",
        "true",
    ]  # Default false


def get_disable_background_tasks():
    return os.environ.get("DISABLE_BACKGROUND_TASKS") in [
        "True",
        "T",
        "true",
    ]  # Default false


AS_API_ROOT_PATH = os.environ.get("AS_API_ROOT_PATH", "")

AS_API_SECRET_TOKEN = os.environ.get("AS_API_SECRET_TOKEN", "")
