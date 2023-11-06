from functools import wraps
import logging
import time

from flask import request


def with_log_run_times(_logger: logging.Logger, _tag: str = ""):
    """
    Function decorator to log runtimes of the endpoints
    """
    def decorator(func):
        @wraps(func)
        def inner_wrapper(*args, **kwargs):
            start_time = time.time()
            path = ""
            try:
                path = request.path
            except:
                pass
            _logger.info('{}|RECEIVED|{}'.format(_tag, path))
            response = func(*args, **kwargs)
            _logger.info('{}|RTIME|{}|{:.3f}'.format(
                _tag, path, (time.time() - start_time)))
            return response

        return inner_wrapper
    return decorator


def get_app_logger() -> logging.Logger:
    """
    Returns app logger
    """
    _logger = logging.getLogger('gunicorn.error')
    return _logger


# Logger instance for reutilization
logger = get_app_logger()
