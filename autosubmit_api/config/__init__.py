import os
from dotenv import load_dotenv

load_dotenv()

# Auth
PROTECTION_LEVEL = os.environ.get("PROTECTION_LEVEL")
# WARNING: Always provide a SECRET_KEY for production
JWT_SECRET = os.environ.get(
    "SECRET_KEY", "M87;Z$,o5?MSC(/@#-LbzgE3PH-5ki.ZvS}N.s09v>I#v8I'00THrA-:ykh3HX?"
)
JWT_ALGORITHM = "HS256"
JWT_EXP_DELTA_SECONDS = 84000 * 5  # 5 days

# CAS Stuff
CAS_SERVER_URL = os.environ.get("CAS_SERVER_URL")
# e.g: 'https://cas.bsc.es/cas/login'
CAS_LOGIN_URL = os.environ.get(
    "CAS_LOGIN_URL", (CAS_SERVER_URL + "login") if CAS_SERVER_URL else ""
)
# e.g: 'https://cas.bsc.es/cas/serviceValidate'
CAS_VERIFY_URL = os.environ.get(
    "CAS_VERIFY_URL", (CAS_SERVER_URL + "serviceValidate") if CAS_SERVER_URL else ""
)

# GitHub Oauth App

GITHUB_OAUTH_CLIENT_ID = os.environ.get("GITHUB_OAUTH_CLIENT_ID")
GITHUB_OAUTH_CLIENT_SECRET = os.environ.get("GITHUB_OAUTH_CLIENT_SECRET")
GITHUB_OAUTH_WHITELIST_ORGANIZATION = os.environ.get(
    "GITHUB_OAUTH_WHITELIST_ORGANIZATION"
)
GITHUB_OAUTH_WHITELIST_TEAM = os.environ.get("GITHUB_OAUTH_WHITELIST_TEAM")

# OpenID Connect

OIDC_TOKEN_URL = os.environ.get("OIDC_TOKEN_URL")
OIDC_CLIENT_ID = os.environ.get("OIDC_CLIENT_ID")
OIDC_CLIENT_SECRET = os.environ.get("OIDC_CLIENT_SECRET")

OIDC_USERNAME_SOURCE = os.environ.get("OIDC_USERNAME_SOURCE")
OIDC_USERNAME_CLAIM = os.environ.get("OIDC_USERNAME_CLAIM")
OIDC_USERINFO_URL = os.environ.get("OIDC_USERINFO_URL")


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
