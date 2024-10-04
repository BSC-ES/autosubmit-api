from functools import wraps
from http import HTTPStatus
from typing import Annotated
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from flask import request
import jwt
from autosubmit_api.logger import logger
from autosubmit_api import config
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


def with_auth_token(
    threshold=ProtectionLevels.ALL, response_on_fail=True, raise_on_fail=False
):
    """
    Decorator that validates the Authorization token in a request.

    It adds the `user_id` variable inside the arguments of the wrapped function.

    :param threshold: The minimum PROTECTION_LEVEL that needs to be set to trigger a *_on_fail
    :param response_on_fail: if `True` will return a Flask response on fail
    :param raise_on_fail: if `True` will raise an exception on fail
    :raises AppAuthError: if raise_on_fail=True and decoding fails
    """

    def decorator(func):
        @wraps(func)
        def inner_wrapper(*args, **kwargs):
            try:
                current_token = request.headers.get("Authorization")
                # Remove the Bearer prefix if it exists
                if current_token.startswith("Bearer "):
                    current_token = current_token[7:]
                jwt_token = jwt.decode(
                    current_token, config.JWT_SECRET, config.JWT_ALGORITHM
                )
            except Exception as exc:
                error_msg = "Unauthorized"
                if isinstance(exc, jwt.ExpiredSignatureError):
                    error_msg = "Expired token"
                auth_level = _parse_protection_level_env(config.PROTECTION_LEVEL)
                if threshold <= auth_level:  # If True, will trigger *_on_fail
                    if raise_on_fail:
                        raise AppAuthError(error_msg)
                    if response_on_fail:
                        return {
                            "error": True,
                            "error_message": error_msg,
                        }, HTTPStatus.UNAUTHORIZED
                jwt_token = {"user_id": None}

            user_id = jwt_token.get("user_id", None)
            logger.debug("decorator user_id: " + str(user_id))
            kwargs["user_id"] = user_id

            return func(*args, **kwargs)

        return inner_wrapper

    return decorator


security = HTTPBearer(auto_error=False)


def auth_token_dependency(threshold=ProtectionLevels.ALL, raise_on_fail=True):
    """
    FastAPI Dependency that validates the Authorization token in a request.

    It adds the `user_id` variable inside the arguments of the wrapped function.

    :param threshold: The minimum PROTECTION_LEVEL that needs to be set to trigger a *_on_fail
    :param raise_on_fail: if `True` will raise an exception on fail
    """

    async def dependency(
        credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    ):
        try:
            current_token = credentials.credentials
            jwt_token = jwt.decode(
                current_token, config.JWT_SECRET, config.JWT_ALGORITHM
            )
        except Exception as exc:
            error_msg = "Unauthorized"
            if isinstance(exc, jwt.ExpiredSignatureError):
                error_msg = "Expired token"
            auth_level = _parse_protection_level_env(config.PROTECTION_LEVEL)
            if threshold <= auth_level:  # If True, will trigger *_on_fail
                if raise_on_fail:
                    raise HTTPException(
                        status_code=HTTPStatus.UNAUTHORIZED, detail=error_msg
                    )
            jwt_token = {"user_id": None}

        user_id = jwt_token.get("user_id", None)
        logger.debug("user_id: " + str(user_id))
        return user_id

    return dependency
