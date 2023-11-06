from functools import wraps
from flask import request
from jwt.jwt import JWT
from autosubmit_api.logger import logger
from autosubmit_api.config import AUTHORIZATION, JWT_ALGORITHM, JWT_SECRET


class AppAuthError(ValueError):
    code = 401


def with_auth_token(response_on_fail=False, raise_on_fail=False):
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
            current_token = request.headers.get("Authorization")

            try:
                jwt_token = JWT.decode(
                    current_token, JWT_SECRET, JWT_ALGORITHM)
            except Exception as exp:
                if AUTHORIZATION and raise_on_fail:
                    raise AppAuthError("User not authenticated")
                if AUTHORIZATION and response_on_fail:
                    return {"error": True, "message": "Unauthorized"}, 401
                jwt_token = {"user_id": None}

            user_id = jwt_token.get("user_id", None)
            logger.debug("decorator user_id: " + str(user_id))
            kwargs["user_id"] = user_id

            return func(*args, **kwargs)

        return inner_wrapper
    return decorator
