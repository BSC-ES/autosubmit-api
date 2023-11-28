import os
from datetime import datetime, timedelta
from typing import Optional
import requests
from flask_cors import cross_origin
from flask import request, session, redirect
from autosubmit_api.auth import ProtectionLevels, with_auth_token
from autosubmit_api.database.db_common import (
    get_current_running_exp,
    update_experiment_description_owner,
)
from autosubmit_api.experiment import common_requests as CommonRequests
from autosubmit_api.experiment import utils as Utiles
from autosubmit_api.logger import logger, with_log_run_times
from autosubmit_api.performance.performance_metrics import PerformanceMetrics
from autosubmit_api.database.db_common import search_experiment_by_id
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.builders.joblist_helper_builder import (
    JobListHelperBuilder,
    JobListHelperDirector,
)
from multiprocessing import Manager, Lock
import jwt
from autosubmit_api.config import (
    JWT_SECRET,
    JWT_ALGORITHM,
    JWT_EXP_DELTA_SECONDS,
    CAS_LOGIN_URL,
    CAS_VERIFY_URL,
)


# Multiprocessing setup
D = Manager().dict()
lock = Lock()


@with_log_run_times(logger, "LOGIN")
def login():
    APIBasicConfig.read()
    ticket = request.args.get("ticket")
    environment = request.args.get("env")
    referrer = request.referrer
    is_allowed = False
    for allowed_client in APIBasicConfig.ALLOWED_CLIENTS:
        if referrer and referrer.find(allowed_client) >= 0:
            referrer = allowed_client
            is_allowed = True
    if is_allowed == False:
        return {
            "authenticated": False,
            "user": None,
            "token": None,
            "message": "Your client is not authorized for this operation. The API admin needs to add your URL to the list of allowed clients.",
        }, 401

    target_service = "{}{}/login".format(referrer, environment)
    if not ticket:
        route_to_request_ticket = "{}?service={}".format(CAS_LOGIN_URL, target_service)
        logger.info("Redirected to: " + str(route_to_request_ticket))
        return redirect(route_to_request_ticket)
    # can be used to target the test environment
    # environment = environment if environment is not None else "autosubmitapp"
    cas_verify_ticket_route = (
        CAS_VERIFY_URL + "?service=" + target_service + "&ticket=" + ticket
    )
    response = requests.get(cas_verify_ticket_route)
    user = None
    if response:
        user = Utiles.get_cas_user_from_xml(response.content)
    logger.info("CAS verify ticket response: user %s", user)
    if not user:
        return {
            "authenticated": False,
            "user": None,
            "token": None,
            "message": "Can't verify user.",
        }, 401
    else:  # Login successful
        payload = {
            "user_id": user,
            "exp": datetime.utcnow() + timedelta(seconds=JWT_EXP_DELTA_SECONDS),
        }
        jwt_token = jwt.encode(payload, JWT_SECRET, JWT_ALGORITHM)
        return {
            "authenticated": True,
            "user": user,
            "token": jwt_token,
            "message": "Token generated.",
        }


@cross_origin(expose_headers="Authorization")
@with_log_run_times(logger, "TTEST")
@with_auth_token(threshold=ProtectionLevels.NONE, response_on_fail=False)
def test_token(user_id: Optional[str] = None):
    """
    Tests if a token is still valid
    """
    return {
        "isValid": True if user_id else False,
        "message": "Unauthorized" if not user_id else None,
    }, 200 if user_id else 401


@cross_origin(expose_headers="Authorization")
@with_log_run_times(logger, "UDESC")
@with_auth_token(threshold=ProtectionLevels.WRITEONLY)
def update_description(user_id: Optional[str] = None):
    """
    Updates the description of an experiment. Requires authenticated user.
    """
    expid = None
    new_description = None
    if request.is_json:
        body_data = request.json
        expid = body_data.get("expid", None)
        new_description = body_data.get("description", None)
    return (
        update_experiment_description_owner(expid, new_description, user_id),
        200 if user_id else 401,
    )


@cross_origin(expose_headers="Authorization")
@with_log_run_times(logger, "CCONFIG")
@with_auth_token()
def get_current_configuration(expid: str, user_id: Optional[str] = None):
    result = CommonRequests.get_current_configuration_by_expid(expid, user_id)
    return result


@with_log_run_times(logger, "EXPINFO")
@with_auth_token()
def exp_info(expid: str, user_id: Optional[str] = None):
    result = CommonRequests.get_experiment_data(expid)
    return result


@with_log_run_times(logger, "EXPCOUNT")
@with_auth_token()
def exp_counters(expid: str, user_id: Optional[str] = None):
    result = CommonRequests.get_experiment_counters(expid)
    return result


@with_log_run_times(logger, "SOWNER")
@with_auth_token()
def search_owner(owner, exptype=None, onlyactive=None, user_id: Optional[str] = None):
    """
    Same output format as search_expid
    """
    result = search_experiment_by_id(
        query=None, owner=owner, exp_type=exptype, only_active=onlyactive
    )
    return result


@with_log_run_times(logger, "SEARCH")
@with_auth_token()
def search_expid(expid, exptype=None, onlyactive=None, user_id: Optional[str] = None):
    result = search_experiment_by_id(
        query=expid, owner=None, exp_type=exptype, only_active=onlyactive
    )
    return result


@with_log_run_times(logger, "RUN")
@with_auth_token()
def search_running(user_id: Optional[str] = None):
    """
    Returns the list of all experiments that are currently running.
    """
    if "username" in session:
        logger.debug(("USER {}".format(session["username"])))
    logger.debug("Active proceses: " + str(D))
    # logger.info("Received Currently Running query ")
    result = get_current_running_exp()
    return result


@with_log_run_times(logger, "ERUNS")
@with_auth_token()
def get_runs(expid, user_id: Optional[str] = None):
    """
    Get list of runs of the same experiment from the historical db
    """
    result = CommonRequests.get_experiment_runs(expid)
    return result


@with_log_run_times(logger, "IFRUN")
@with_auth_token()
def get_if_running(expid, user_id: Optional[str] = None):
    result = CommonRequests.quick_test_run(expid)
    return result


@with_log_run_times(logger, "RUNDET")
@with_auth_token()
def get_running_detail(expid, user_id: Optional[str] = None):
    result = CommonRequests.get_current_status_log_plus(expid)
    return result


@with_log_run_times(logger, "SUMMARY")
@with_auth_token()
def get_expsummary(expid, user_id: Optional[str] = None):
    user = request.args.get("loggedUser", default="null", type=str)
    if user != "null":
        lock.acquire()
        D[os.getpid()] = [user, "summary", True]
        lock.release()
    result = CommonRequests.get_experiment_summary(expid, logger)
    logger.info("Process: " + str(os.getpid()) + " workers: " + str(D))
    if user != "null":
        lock.acquire()
        D[os.getpid()] = [user, "summary", False]
        lock.release()
    if user != "null":
        lock.acquire()
        D.pop(os.getpid(), None)
        lock.release()
    return result


@with_log_run_times(logger, "SHUTDOWN")
@with_auth_token()
def shutdown(route, user_id: Optional[str] = None):
    """
    This function is invoked from the frontend (AS-GUI) to kill workers that are no longer needed.
    This call is common in heavy parts of the GUI such as the Tree and Graph generation or Summaries fetching.
    """
    try:
        user = request.args.get("loggedUser", default="null", type=str)
        expid = request.args.get("expid", default="null", type=str)
    except Exception as exp:
        logger.info("Bad parameters for user and expid in route.")

    if user != "null":
        logger.info(
            "SHUTDOWN|DETAILS|route: " + route + " user: " + user + " expid: " + expid
        )
        try:
            # logger.info("user: " + user)
            # logger.info("expid: " + expid)
            logger.info("Workers before: " + str(D))
            lock.acquire()
            for k, v in list(D.items()):
                if v[0] == user and v[1] == route and v[-1] == True:
                    if v[2] == expid:
                        D[k] = [user, route, expid, False]
                    else:
                        D[k] = [user, route, False]
                    D.pop(k, None)
                    # reboot the worker
                    os.system("kill -HUP " + str(k))
                    logger.info("killed worker " + str(k))
            lock.release()
            logger.info("Workers now: " + str(D))
        except Exception as exp:
            logger.info(
                "[CRITICAL] Could not shutdown process "
                + expid
                + ' by user "'
                + user
                + '"'
            )
    return ""


@with_log_run_times(logger, "PRF")
@with_auth_token()
def get_exp_performance(expid, user_id: Optional[str] = None):
    result = {}
    try:
        result = PerformanceMetrics(
            expid,
            JobListHelperDirector(JobListHelperBuilder(expid)).build_job_list_helper(),
        ).to_json()
    except Exception as exc:
        result = {
            "SYPD": None,
            "ASYPD": None,
            "RSYPD": None,
            "CHSY": None,
            "JPSY": None,
            "Parallelization": None,
            "PE": None,
            "considered": [],
            "error": True,
            "error_message": str(exc),
            "warnings_job_data": [],
        }
    return result


@with_log_run_times(logger, "GRAPH")
@with_auth_token()
def get_graph_format(
    expid, layout="standard", grouped="none", user_id: Optional[str] = None
):
    user = request.args.get("loggedUser", default="null", type=str)
    # logger.info("user: " + user)
    # logger.info("expid: " + expid)
    if user != "null":
        lock.acquire()
        D[os.getpid()] = [user, "graph", expid, True]
        lock.release()
    result = CommonRequests.get_experiment_graph(expid, logger, layout, grouped)
    logger.info("Process: " + str(os.getpid()) + " graph workers: " + str(D))
    if user != "null":
        lock.acquire()
        D[os.getpid()] = [user, "graph", expid, False]
        lock.release()
    if user != "null":
        lock.acquire()
        D.pop(os.getpid(), None)
        lock.release()
    return result


@with_log_run_times(logger, "TREE")
@with_auth_token()
def get_exp_tree(expid, user_id: Optional[str] = None):
    user = request.args.get("loggedUser", default="null", type=str)
    # logger.info("user: " + user)
    # logger.info("expid: " + expid)
    if user != "null":
        lock.acquire()
        D[os.getpid()] = [user, "tree", expid, True]
        lock.release()
    result = CommonRequests.get_experiment_tree_structured(expid, logger)
    logger.info("Process: " + str(os.getpid()) + " tree workers: " + str(D))
    if user != "null":
        lock.acquire()
        D[os.getpid()] = [user, "tree", expid, False]
        lock.release()
    if user != "null":
        lock.acquire()
        D.pop(os.getpid(), None)
        lock.release()
    return result


@with_log_run_times(logger, "QUICK")
@with_auth_token(response_on_fail=True)
def get_quick_view_data(expid, user_id=None):
    result = CommonRequests.get_quick_view(expid)
    return result


@with_log_run_times(logger, "LOG")
@with_auth_token()
def get_experiment_run_log(expid, user_id: Optional[str] = None):
    """
    Finds log and gets the last 150 lines
    """
    result = CommonRequests.get_experiment_log_last_lines(expid)
    return result


@with_log_run_times(logger, "JOBLOG")
@with_auth_token()
def get_job_log_from_path(logfile, user_id: Optional[str] = None):
    """
    Get log from path
    """
    expid = logfile.split("_") if logfile is not None else ""
    expid = expid[0] if len(expid) > 0 else ""
    result = CommonRequests.get_job_log(expid, logfile)
    return result


@with_log_run_times(logger, "GPKL")
@with_auth_token()
def get_experiment_pklinfo(expid, timeStamp, user_id: Optional[str] = None):
    result = CommonRequests.get_experiment_pkl(expid)
    return result


@with_log_run_times(logger, "TPKL")
@with_auth_token()
def get_experiment_tree_pklinfo(expid, timeStamp, user_id: Optional[str] = None):
    result = CommonRequests.get_experiment_tree_pkl(expid)
    return result


@with_log_run_times(logger, "STAT")
@with_auth_token()
def get_experiment_statistics(
    expid, filter_period, filter_type, user_id: Optional[str] = None
):
    result = CommonRequests.get_experiment_stats(expid, filter_period, filter_type)
    return result


@with_log_run_times(logger, "HISTORY")
@with_auth_token()
def get_exp_job_history(expid, jobname, user_id: Optional[str] = None):
    result = CommonRequests.get_job_history(expid, jobname)
    return result


@with_log_run_times(logger, "RUNDETAIL")
@with_auth_token()
def get_experiment_run_job_detail(expid, runid, user_id: Optional[str] = None):
    result = CommonRequests.get_experiment_tree_rundetail(expid, runid)
    return result


@with_log_run_times(logger, "FSTATUS")
def get_file_status():
    result = CommonRequests.get_last_test_archive_status()
    return result
