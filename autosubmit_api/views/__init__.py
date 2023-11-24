from autosubmit_api.logger import with_log_run_times, logger
from autosubmit_api import __version__ as APIVersion


@with_log_run_times(logger, "HOME")
def home():
    return {"name": "Autosubmit API", "version": APIVersion}
