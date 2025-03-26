import jwt
from autosubmit_api import config
from datetime import datetime, timedelta
from autosubmit_api.config.basicConfig import APIBasicConfig


def validate_client(client_name):
    APIBasicConfig.read()
    for allowed_client in APIBasicConfig.ALLOWED_CLIENTS:
        if (allowed_client == "*") or (allowed_client in client_name):
            return True
    return False


def generate_jwt_token(username: str) -> str:
    payload = {
        "user_id": username,
        "sub": username,
        "iat": int(datetime.now().timestamp()),
        "exp": (datetime.now() + timedelta(seconds=config.JWT_EXP_DELTA_SECONDS)),
    }
    jwt_token = jwt.encode(payload, config.JWT_SECRET, config.JWT_ALGORITHM)
    return jwt_token
