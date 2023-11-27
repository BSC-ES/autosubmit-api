from autosubmit_api.logger import with_log_run_times, logger
from autosubmit_api import __version__ as APIVersion
from http import HTTPStatus


def not_implemented_handler(*args, **kwargs):
    return {
        "error": True,
        "error_message": "Not Implemented",
    }, HTTPStatus.NOT_IMPLEMENTED


@with_log_run_times(logger, "HOME")
def home():
    return {"name": "Autosubmit API", "version": APIVersion}, HTTPStatus.OK
