from functools import wraps
from flask import request
from jwt.jwt import JWT
from autosubmit_api.logger import logger
from autosubmit_api.config import AUTHORIZATION_LEVEL, JWT_ALGORITHM, JWT_SECRET
from enum import IntEnum


class AuthorizationLevels(IntEnum):
    ALL = 100
    WRITEONLY = 20
    NONE = 0


class AppAuthError(ValueError):
    code = 401


def _parse_authorization_level_env(_var):
    if _var == "NONE":
        return AuthorizationLevels.NONE
    elif _var == "WRITEONLY":
        return AuthorizationLevels.WRITEONLY

    return AuthorizationLevels.ALL


def with_auth_token(level=AuthorizationLevels.ALL, response_on_fail=True, raise_on_fail=False):
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
                jwt_token = JWT.decode(
                    current_token, JWT_SECRET, JWT_ALGORITHM)
            except Exception as exc:
                auth_level = _parse_authorization_level_env(AUTHORIZATION_LEVEL)
                if level <= auth_level and raise_on_fail:
                    raise AppAuthError("User not authenticated")
                if level <= auth_level and response_on_fail:
                    return {"error": True, "message": "Unauthorized"}, 401
                jwt_token = {"user_id": None}

            user_id = jwt_token.get("user_id", None)
            logger.debug("decorator user_id: " + str(user_id))
            kwargs["user_id"] = user_id

            return func(*args, **kwargs)

        return inner_wrapper
    return decorator
