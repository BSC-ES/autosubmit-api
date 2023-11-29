from autosubmit_api.logger import with_log_run_times, logger
from autosubmit_api import __version__ as APIVersion
from http import HTTPStatus
from werkzeug.exceptions import HTTPException


def handle_HTTP_exception(e: HTTPException):
    """Return JSON instead of HTML for HTTP errors."""
    return {"error": True, "error_message": e.name}, e.code


@with_log_run_times(logger, "HOME")
def home():
    return {"name": "Autosubmit API", "version": APIVersion}, HTTPStatus.OK
