from functools import wraps
import logging
import time
import traceback

from flask import request


def with_log_run_times(_logger: logging.Logger, _tag: str = "", catch_exc:bool=False):
    """
    Function decorator to log runtimes of the endpoints
    :param _logger: logger to use
    :param _tag: tag for the logs
    :param catch_exc: if True, will catch any Exception and not raise it
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
            response = None
            try:
                response = func(*args, **kwargs)
            except Exception as exc:
                _logger.error('{}|ERROR|{}|Exception msg: {}'.format(_tag, path, exc))
                if catch_exc:
                    _logger.error(traceback.format_exc())
                else:
                    raise exc
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
