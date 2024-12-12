import traceback
from typing import Tuple
from autosubmit_api.logger import logger
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.repositories.experiment_status import create_experiment_status_repository


# SELECTS

def get_specific_experiment_status(expid: str) -> Tuple[str, str]:
    """
    Gets the current status from database.\n
    :param expid: Experiment name
    :type expid: str
    :return: name of experiment and status
    :rtype: 2-tuple (name, status)
    """
    try:
        APIBasicConfig.read()
        row = create_experiment_status_repository().get_by_expid(expid)
        return (row.name, row.status)
    except Exception as exc:
        logger.error(f"Exception while reading experiment_status for {expid}: {exc}")
        logger.error(traceback.format_exc())

    return (expid, "NOT RUNNING")
