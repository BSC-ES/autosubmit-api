from functools import wraps
from flask import request
import jwt
from autosubmit_api.logger import logger
from autosubmit_api.config import PROTECTION_LEVEL, JWT_ALGORITHM, JWT_SECRET
from enum import IntEnum


class ProtectionLevels(IntEnum):
    ALL = 100
    WRITEONLY = 20
    NONE = 0


class AppAuthError(ValueError):
    code = 401


def _parse_protection_level_env(_var):
    if _var == "NONE":
        return ProtectionLevels.NONE
    elif _var == "WRITEONLY":
        return ProtectionLevels.WRITEONLY

    return ProtectionLevels.ALL


def with_auth_token(threshold=ProtectionLevels.ALL, response_on_fail=True, raise_on_fail=False):
    """
    Decorator that validates the Authorization token in a request.

    It adds the `user_id` variable inside the arguments of the wrapped function.

    :param response_on_fail: if `True` will return a Flask response
    :param raise_on_fail: if `True` will raise an exception
    :raises AppAuthError: if raise_on_fail=True and decoding fails
    """
    def decorator(func):
        @wraps(func)
        def inner_wrapper(*args, **kwargs):
            try:
                current_token = request.headers.get("Authorization")
                jwt_token = jwt.decode(
                    current_token, JWT_SECRET, JWT_ALGORITHM)
            except Exception as exc:
                error_msg = "Unauthorized"
                if isinstance(exc, jwt.ExpiredSignatureError):
                    error_msg = "Expired token" 
                auth_level = _parse_protection_level_env(PROTECTION_LEVEL)
                if threshold <= auth_level and raise_on_fail:
                    raise AppAuthError(error_msg)
                if threshold <= auth_level and response_on_fail:
                    return {"error": True, "message": error_msg }, 401
                jwt_token = {"user_id": None}

            user_id = jwt_token.get("user_id", None)
            logger.debug("decorator user_id: " + str(user_id))
            kwargs["user_id"] = user_id

            return func(*args, **kwargs)

        return inner_wrapper
    return decorator
