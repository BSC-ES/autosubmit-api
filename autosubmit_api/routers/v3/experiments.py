from multiprocessing import Lock, Manager
import os
from typing import Literal, Optional
from fastapi import APIRouter, Depends, Path, Query
from autosubmit_api.builders.joblist_helper_builder import (
    JobListHelperBuilder,
    JobListHelperDirector,
)
from autosubmit_api.logger import logger
from autosubmit_api.auth import auth_token_dependency
from autosubmit_api.database.db_common import (
    get_current_running_exp,
    search_experiment_by_id,
)
from autosubmit_api.experiment import common_requests as CommonRequests
from autosubmit_api.performance.performance_metrics import PerformanceMetrics


router = APIRouter()

# Multiprocessing setup
D = Manager().dict()
lock = Lock()


@router.get("/cconfig/{expid}", name="Get Experiment Configuration")
async def get_current_configuration(
    expid: str, user_id: Optional[str] = Depends(auth_token_dependency())
) -> dict:
    """
    Get the current configuration of the experiment
    """
    result = CommonRequests.get_current_configuration_by_expid(expid, user_id)
    return result


@router.get("/expinfo/{expid}", name="Get Experiment Information")
async def get_exp_info(
    expid: str, user_id: Optional[str] = Depends(auth_token_dependency())
) -> dict:
    """
    Get the information of the experiment
    """
    result = CommonRequests.get_experiment_data(expid)
    return result


@router.get("/expcount/{expid}", name="Get Experiment Counters")
async def get_exp_counters(
    expid: str, user_id: Optional[str] = Depends(auth_token_dependency())
) -> dict:
    """
    Get the job status counters of the experiment
    """
    result = CommonRequests.get_experiment_counters(expid)
    return result


@router.get("/searchowner/{owner}", name="Search Owner")
async def search_owner(
    owner: str, user_id: Optional[str] = Depends(auth_token_dependency())
) -> dict:
    """
    Search for experiments by owner
    """
    result = search_experiment_by_id(
        query=None, owner=owner, exp_type=None, only_active=None
    )
    return result


@router.get("/search/{expid}", name="Search Experiment by expid")
async def search_expid(
    expid: str,
    user_id: Optional[str] = Depends(auth_token_dependency()),
) -> dict:
    """
    Search for experiments by expid
    """
    result = search_experiment_by_id(
        query=expid, owner=None, exp_type=None, only_active=None
    )
    return result


@router.get(
    "/search/{expid}/{exptype}/{onlyactive}",
    name="Search Experiment by expid, type and active status",
)
async def search_expid_plus(
    expid: str,
    exptype: str,
    onlyactive: str,
    user_id: Optional[str] = Depends(auth_token_dependency()),
) -> dict:
    """
    Search for experiments by expid, type and active status
    """
    result = search_experiment_by_id(
        query=expid, owner=None, exp_type=exptype, only_active=onlyactive
    )
    return result


@router.get("/running/", name="Search Running Experiments")
async def search_running(
    user_id: Optional[str] = Depends(auth_token_dependency()),
) -> dict:
    """
    Returns the list of all experiments that are currently running.
    """
    result = get_current_running_exp()
    return result


@router.get("/runs/{expid}", name="Get Experiment Runs")
async def get_runs(
    expid: str, user_id: Optional[str] = Depends(auth_token_dependency())
) -> dict:
    """
    Get list of runs of the same experiment from the historical db
    """
    result = CommonRequests.get_experiment_runs(expid)
    return result


@router.get("/ifrun/{expid}", name="Check if Experiment is Running")
async def get_if_running(
    expid: str, user_id: Optional[str] = Depends(auth_token_dependency())
) -> dict:
    """
    Quick check if the experiment is currently running.
    """
    result = CommonRequests.quick_test_run(expid)
    return result


@router.get("/logrun/{expid}", name="Get Experiment running status and log path")
async def get_running_detail(
    expid: str, user_id: Optional[str] = Depends(auth_token_dependency())
) -> dict:
    """
    Get Experiment running status and log path.
    """
    result = CommonRequests.get_current_status_log_plus(expid)
    return result


@router.get("/summary/{expid}", name="Get Experiment Summary")
async def get_exp_summary(
    expid: str,
    loggedUser: str = Query("null"),
    user_id: Optional[str] = Depends(auth_token_dependency()),
) -> dict:
    """
    Get Experiment Summary
    """
    if loggedUser != "null":
        lock.acquire()
        D[os.getpid()] = [loggedUser, "summary", True]
        lock.release()
    result = CommonRequests.get_experiment_summary(expid, logger)
    logger.info("Process: " + str(os.getpid()) + " workers: " + str(D))
    if loggedUser != "null":
        lock.acquire()
        D[os.getpid()] = [loggedUser, "summary", False]
        lock.release()
    if loggedUser != "null":
        lock.acquire()
        D.pop(os.getpid(), None)
        lock.release()
    return result


@router.get("/shutdown/{route}", name="Shutdown Experiment processes")
async def shutdown(
    route: str,
    loggedUser: str = Query("null"),
    expid: str = Query("null"),
    user_id: Optional[str] = Depends(auth_token_dependency()),
):
    """
    This function is invoked from the frontend (AS-GUI) to kill workers that are no longer needed.
    This call is common in heavy parts of the GUI such as the Tree and Graph generation or Summaries fetching.
    """
    if loggedUser != "null":
        logger.info(
            "SHUTDOWN|DETAILS|route: "
            + route
            + " user: "
            + loggedUser
            + " expid: "
            + expid
        )
        try:
            # logger.info("user: " + user)
            # logger.info("expid: " + expid)
            logger.info("Workers before: " + str(D))
            lock.acquire()
            for k, v in list(D.items()):
                if v[0] == loggedUser and v[1] == route and v[-1] is True:
                    if v[2] == expid:
                        D[k] = [loggedUser, route, expid, False]
                    else:
                        D[k] = [loggedUser, route, False]
                    D.pop(k, None)
                    # reboot the worker
                    os.system("kill -HUP " + str(k))
                    logger.info("killed worker " + str(k))
            lock.release()
            logger.info("Workers now: " + str(D))
        except Exception:
            logger.info(
                "[CRITICAL] Could not shutdown process "
                + expid
                + ' by user "'
                + loggedUser
                + '"'
            )
    return ""


@router.get("/performance/{expid}", name="Get Experiment Performance")
async def get_exp_performance(
    expid: str, user_id: Optional[str] = Depends(auth_token_dependency())
) -> dict:
    """
    Get Experiment Performance
    """
    result = {}
    try:
        result = PerformanceMetrics(
            expid,
            JobListHelperDirector(JobListHelperBuilder(expid)).build_job_list_helper(),
        ).to_json()
    except Exception as exc:
        result = {
            "SYPD": None,
            "PSYPD": None,
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


@router.get("/graph/{expid}/{layout}/{grouped}", name="Get Experiment Graph")
async def get_graph_format(
    expid: str,
    layout: Literal["standard", "laplacian"],
    grouped: Literal["none", "status", "date-member"],
    loggedUser: str = Query("null"),
    user_id: Optional[str] = Depends(auth_token_dependency()),
) -> dict:
    """
    Get Experiment Graph
    """
    if loggedUser != "null":
        lock.acquire()
        D[os.getpid()] = [loggedUser, "graph", expid, True]
        lock.release()
    result = CommonRequests.get_experiment_graph(expid, logger, layout, grouped)
    logger.info("Process: " + str(os.getpid()) + " graph workers: " + str(D))
    if loggedUser != "null":
        lock.acquire()
        D[os.getpid()] = [loggedUser, "graph", expid, False]
        lock.release()
    if loggedUser != "null":
        lock.acquire()
        D.pop(os.getpid(), None)
        lock.release()
    return result


@router.get("/tree/{expid}", name="Get Experiment Tree")
async def get_exp_tree(
    expid: str,
    loggedUser: str = Query("null"),
    user_id: Optional[str] = Depends(auth_token_dependency()),
) -> dict:
    """
    Get Experiment Tree
    """
    if loggedUser != "null":
        lock.acquire()
        D[os.getpid()] = [loggedUser, "tree", expid, True]
        lock.release()
    result = CommonRequests.get_experiment_tree_structured(expid, logger)
    logger.info("Process: " + str(os.getpid()) + " tree workers: " + str(D))
    if loggedUser != "null":
        lock.acquire()
        D[os.getpid()] = [loggedUser, "tree", expid, False]
        lock.release()
    if loggedUser != "null":
        lock.acquire()
        D.pop(os.getpid(), None)
        lock.release()
    return result


@router.get("/quick/{expid}", name="Get Quick View Data")
async def get_quick_view_data(
    expid: str, user_id: Optional[str] = Depends(auth_token_dependency())
) -> dict:
    """
    Get Quick View Data
    """
    result = CommonRequests.get_quick_view(expid)
    return result


@router.get("/exprun/{expid}", name="Get Experiment Run Log")
async def get_experiment_run_log(
    expid: str, user_id: Optional[str] = Depends(auth_token_dependency())
) -> dict:
    """
    Finds log and gets the last 150 lines
    """
    result = CommonRequests.get_experiment_log_last_lines(expid)
    return result


@router.get("/joblog/{logfile}", name="Get Job Log from Path")
async def get_job_log_from_path(
    logfile: str, user_id: Optional[str] = Depends(auth_token_dependency())
) -> dict:
    """
    Get Job Log from Path
    """
    expid = logfile.split("_") if logfile is not None else ""
    expid = expid[0] if len(expid) > 0 else ""
    result = CommonRequests.get_job_log(expid, logfile)
    return result


@router.get(
    "/pklinfo/{expid}/{timeStamp}", name="Get Experiment Pickle Info for Graph View"
)
async def get_experiment_pklinfo(
    expid: str,
    timeStamp: str = Path(description="Unused path parameter", example="0"),
    user_id: Optional[str] = Depends(auth_token_dependency()),
) -> dict:
    """
    Get Experiment Pickle Info for Graph View
    """
    result = CommonRequests.get_experiment_pkl(expid)
    return result


@router.get(
    "/pkltreeinfo/{expid}/{timeStamp}", name="Get Experiment Pickle Info for Tree View"
)
async def get_experiment_tree_pklinfo(
    expid: str,
    timeStamp: str = Path(description="Unused path parameter", example="0"),
    user_id: Optional[str] = Depends(auth_token_dependency()),
) -> dict:
    """
    Get Experiment Pickle Info for Tree View
    """
    result = CommonRequests.get_experiment_tree_pkl(expid)
    return result


@router.get(
    "/stats/{expid}/{filter_period}/{filter_type}", name="Get Experiment Statistics"
)
async def get_experiment_statistics(
    expid: str,
    filter_period: str,
    filter_type: str = Path(
        example="Any", description="Job Section filter, use 'Any' for all"
    ),
    user_id: Optional[str] = Depends(auth_token_dependency()),
) -> dict:
    """
    Get Experiment Statistics
    """
    result = CommonRequests.get_experiment_stats(expid, filter_period, filter_type)
    return result


@router.get("/history/{expid}/{jobname}", name="Get Experiment Job History")
async def get_exp_job_history(
    expid: str,
    jobname: str,
    user_id: Optional[str] = Depends(auth_token_dependency()),
) -> dict:
    """
    Get Experiment Job History
    """
    result = CommonRequests.get_job_history(expid, jobname)
    return result


@router.get("/rundetail/{expid}/{runid}", name="Get Experiment Run Job Detail")
async def get_experiment_run_job_detail(
    expid: str,
    runid: str,
    user_id: Optional[str] = Depends(auth_token_dependency()),
) -> dict:
    """
    Get Experiment Run Job Detail
    """
    result = CommonRequests.get_experiment_tree_rundetail(expid, runid)
    return result


@router.get("/filestatus", name="[UNSUPPORTED] Get File Status", deprecated=True)
async def get_file_status() -> dict:
    """
    This endpoint is not supported in this version of the API.
    Will be removed in future versions.
    """
    return {
        "status": False,
        "error": False,
        "error_message": (
            "This endpoint is not supported in this version of the API."
            "Will be removed in future versions."
        ),
        "avg_latency": None,
        "avg_bandwidth": None,
        "current_latency": None,
        "current_bandwidth": None,
        "reponse_time": None,
        "datetime": None,
        "latency_warning": None,
        "bandwidth_warning": None,
        "response_warning": None,
    }
