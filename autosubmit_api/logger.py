from functools import wraps
import logging
import time
import traceback


def with_log_run_times(
    _logger: logging.Logger, _tag: str = "", catch_exc: bool = False
):
    """
    Function decorator to log runtimes
    :param _logger: logger to use
    :param _tag: tag for the logs
    :param catch_exc: if True, will catch any Exception and not raise it
    """

    def decorator(func):
        @wraps(func)
        def inner_wrapper(*args, **kwargs):
            start_time = time.time()
            _logger.info("\033[94m{}|RECEIVED\033[0m".format(_tag))
            response = None
            try:
                response = func(*args, **kwargs)
            except Exception as exc:
                _logger.error("\033[91m{}|ERROR|Exception msg: {}\033[0m".format(_tag, exc))
                if catch_exc:
                    _logger.error(traceback.format_exc())
                else:
                    raise exc
            _logger.info("\033[92m{}|RTIME|{:.3f}\033[0m".format(_tag, (time.time() - start_time)))
            return response

        return inner_wrapper

    return decorator


def get_app_logger() -> logging.Logger:
    """
    Returns app logger
    """
    _logger = logging.getLogger("gunicorn.error")
    return _logger


# Logger instance for reutilization
logger = get_app_logger()
