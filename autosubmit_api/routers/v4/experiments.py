import asyncio
import json
import math
import os
import re
import traceback
from collections import deque
from datetime import datetime, timezone
from http import HTTPStatus
from typing import Annotated, Any, Dict, List, Literal, Optional

from bscearth.utils.config_parser import ConfigParserFactory
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from autosubmit_api.auth import auth_token_dependency
from autosubmit_api.builders.experiment_builder import ExperimentBuilder
from autosubmit_api.builders.experiment_history_builder import (
    ExperimentHistoryBuilder,
    ExperimentHistoryDirector,
)
from autosubmit_api.common.utils import Status, timestamp_to_datetime_format
from autosubmit_api.components.jobs.job_detail import (
    JobDetailRetriever,
    JobNotFoundError,
)
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.config.confConfigStrategy import confConfigStrategy
from autosubmit_api.config.config_common import AutosubmitConfigResolver
from autosubmit_api.database import tables
from autosubmit_api.database.db_jobdata import JobDataStructure
from autosubmit_api.database.models import BaseExperimentModel
from autosubmit_api.logger import logger
from autosubmit_api.models.requests import (
    ExperimentsSearchRequest,
)
from autosubmit_api.models.responses import (
    ExperimentFSConfigResponse,
    ExperimentJobsResponse,
    ExperimentRunConfigResponse,
    ExperimentRunsResponse,
    ExperimentsSearchResponse,
    ExperimentWrappersResponse,
)
from autosubmit_api.persistance.experiment import ExperimentPaths
from autosubmit_api.persistance.job_package_reader import JobPackageReader
from autosubmit_api.repositories.experiment_structure import (
    create_experiment_structure_repository,
)
from autosubmit_api.repositories.jobs import create_jobs_repository
from autosubmit_api.repositories.join.experiment_join import (
    create_experiment_join_repository,
)
from autosubmit_api.repositories.user_metric import create_user_metric_repository

router = APIRouter()


@router.get("", name="Search experiments")
async def search_experiments(
    query_params: Annotated[ExperimentsSearchRequest, Query()],
    user_id: Optional[str] = Depends(auth_token_dependency()),
) -> ExperimentsSearchResponse:
    """
    Search experiments
    """
    logger.debug(f"Search args: {query_params}")

    if query_params.page_size > 0:
        offset = (query_params.page - 1) * query_params.page_size
    else:
        offset = None
        query_params.page_size = None

    # Query
    experiment_join_repo = create_experiment_join_repository()
    query_result, total_rows = experiment_join_repo.search(
        query=query_params.query,
        only_active=query_params.only_active,
        owner=query_params.owner,
        exp_type=query_params.exp_type,
        autosubmit_version=query_params.autosubmit_version,
        hpc=query_params.hpc,
        order_by=query_params.order_by,
        order_desc=query_params.order_desc,
        limit=query_params.page_size,
        offset=offset,
    )

    async def _get_experiment(raw_exp: Dict[str, Any]) -> Dict[str, Any]:
        exp_builder = ExperimentBuilder()
        exp_builder.produce_base_from_dict(raw_exp)
        exp_builder.produce_pkl_modified_time()
        exp = exp_builder.product

        # Get current run data from history
        # last_modified_timestamp = exp.created
        completed = 0
        total = 0
        submitted = 0
        queuing = 0
        running = 0
        failed = 0
        suspended = 0
        try:
            current_run = (
                ExperimentHistoryDirector(ExperimentHistoryBuilder(exp.name))
                .build_reader_experiment_history()
                .manager.get_experiment_run_dc_with_max_id()
            )
            if current_run and current_run.total > 0:
                completed = current_run.completed
                total = current_run.total
                submitted = current_run.submitted
                queuing = current_run.queuing
                running = current_run.running
                failed = current_run.failed
                suspended = current_run.suspended
                # last_modified_timestamp = current_run.modified_timestamp
        except Exception as exc:
            logger.warning((f"Exception getting the current run on search: {exc}"))
            logger.warning(traceback.format_exc())

        # Format data
        return {
            "id": exp.id,
            "name": exp.name,
            "user": exp.user,
            "description": exp.description,
            "hpc": exp.hpc,
            "version": exp.autosubmit_version,
            # "wrapper": exp.wrapper,
            "created": exp.created,
            "modified": exp.modified,
            "status": exp.status if exp.status else "NOT RUNNING",
            "completed": completed,
            "total": total,
            "submitted": submitted,
            "queuing": queuing,
            "running": running,
            "failed": failed,
            "suspended": suspended,
        }

    # Process experiments
    experiments = await asyncio.gather(
        *[_get_experiment(raw_exp) for raw_exp in query_result]
    )

    # Response
    response = {
        "experiments": experiments,
        "pagination": {
            "page": query_params.page,
            "page_size": query_params.page_size,
            "total_pages": math.ceil(total_rows / query_params.page_size)
            if query_params.page_size
            else 1,
            "page_items": len(experiments),
            "total_items": total_rows,
        },
    }
    return JSONResponse(response)  # TODO Use Validation. Not respond directly.


@router.get("/{expid}", name="Get experiment detail")
async def get_experiment_detail(
    expid: str, user_id: Optional[str] = Depends(auth_token_dependency())
) -> BaseExperimentModel:
    """
    Get details of an experiment
    """
    exp_builder = ExperimentBuilder()
    exp_builder.produce_base(expid)
    return exp_builder.product.model_dump(include=tables.ExperimentTable.c.keys())


@router.get("/{expid}/jobs", name="List experiment jobs")
async def get_experiment_jobs(
    expid: str,
    view: Annotated[Literal["quick", "base"], Query()] = "base",
    user_id: Optional[str] = Depends(auth_token_dependency()),
) -> ExperimentJobsResponse:
    """
    Get the experiment jobs from pickle file.
    BASE view returns base content of the pkl file.
    QUICK view returns a reduced payload with just the name and status of the jobs.
    """
    # Read the pkl
    try:
        job_list_repo = create_jobs_repository(expid)
        current_content = job_list_repo.get_all()
    except Exception as exc:
        error_message = "Error while reading the job list"
        logger.error(error_message + f": {exc}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=error_message
        )

    pkl_jobs = deque()
    for job_item in current_content:
        resp_job = {
            "name": job_item.name,
            "status": Status.VALUE_TO_KEY.get(job_item.status, Status.UNKNOWN),
        }

        if view == "base":
            resp_job = {
                **resp_job,
                "priority": job_item.priority,
                "section": job_item.section,
                "date": (
                    job_item.date.date().isoformat()
                    if isinstance(job_item.date, datetime)
                    else None
                ),
                "member": job_item.member,
                "chunk": job_item.chunk,
                "out_path_local": job_item.out_path_local,
                "err_path_local": job_item.err_path_local,
                "out_path_remote": job_item.out_path_remote,
                "err_path_remote": job_item.err_path_remote,
            }

        if job_item.status in [Status.COMPLETED, Status.WAITING, Status.READY]:
            pkl_jobs.append(resp_job)
        else:
            pkl_jobs.appendleft(resp_job)

    return JSONResponse(
        {"jobs": list(pkl_jobs)}
    )  # TODO Use Validation. Not respond directly.


@router.get("/{expid}/wrappers", name="Get experiment wrappers")
async def get_experiment_wrappers(
    expid: str, user_id: Optional[str] = Depends(auth_token_dependency())
) -> ExperimentWrappersResponse:
    """
    Get wrappers for an experiment
    """
    job_package_reader = JobPackageReader(expid)
    job_package_reader.read()

    wrappers_dict: Dict[str, List[str]] = job_package_reader.package_to_jobs

    wrappers = []
    for key, val in wrappers_dict.items():
        wrappers.append({"wrapper_name": key, "job_names": val})

    logger.debug(wrappers)
    return {"wrappers": wrappers}


def _format_config_response(
    config: Dict[str, Any], is_as3: bool = False
) -> Dict[str, Any]:
    """
    Format the config response, removing some keys if it's an AS3 config
    Also, add a key to indicate if the config is empty
    :param config: The config to format
    :param is_as3: If the config is an AS3 config
    """
    ALLOWED_CONFIG_KEYS = ["conf", "exp", "jobs", "platforms", "proj"]
    formatted_config = {
        key: config[key]
        for key in config
        if not is_as3 or (key.lower() in ALLOWED_CONFIG_KEYS)
    }
    formatted_config["contains_nones"] = not config or (None in list(config.values()))
    return formatted_config


@router.get(
    "/{expid}/filesystem-config", name="Get experiment current filesystem configuration"
)
async def get_experiment_fs_config(
    expid: str, user_id: Optional[str] = Depends(auth_token_dependency())
) -> ExperimentFSConfigResponse:
    """
    Get the filesystem config of an experiment
    """
    # Read the config
    APIBasicConfig.read()
    as_config = AutosubmitConfigResolver(expid, APIBasicConfig, ConfigParserFactory())
    is_as3 = isinstance(as_config._configWrapper, confConfigStrategy)
    as_config.reload()
    curr_fs_config: Dict[str, Any] = as_config.get_full_config_as_dict()

    # Format the response
    response = {"config": _format_config_response(curr_fs_config, is_as3)}
    return response


@router.get("/{expid}/runs", name="List experiment runs")
async def get_runs(
    expid: str, user_id: Optional[str] = Depends(auth_token_dependency())
) -> ExperimentRunsResponse:
    """
    Get runs for a given experiment
    """
    try:
        experiment_history = ExperimentHistoryDirector(
            ExperimentHistoryBuilder(expid)
        ).build_reader_experiment_history()
        exp_runs = experiment_history.get_experiment_runs()
    except Exception:
        logger.error("Error while getting experiment runs")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Error while getting experiment runs",
        )

    # Format the response
    response = {"runs": []}
    for run in exp_runs:
        response["runs"].append(
            {
                "run_id": run.run_id,
                "start": datetime.fromtimestamp(run.start, timezone.utc).isoformat(
                    timespec="seconds"
                )
                if run.start > 0
                else None,
                "finish": datetime.fromtimestamp(run.finish, timezone.utc).isoformat(
                    timespec="seconds"
                )
                if run.finish > 0
                else None,
            }
        )

    return response


@router.get("/{expid}/runs/{run_id}/config", name="Get experiment run configuration")
async def get_run_config(
    expid: str,
    run_id: str,
    user_id: Optional[str] = Depends(auth_token_dependency()),
) -> ExperimentRunConfigResponse:
    """
    Get the config of a specific run of an experiment
    """
    historical_db = JobDataStructure(expid, APIBasicConfig)
    experiment_run = historical_db.get_experiment_run_by_id(run_id=run_id)
    metadata = (
        json.loads(experiment_run.metadata)
        if experiment_run and experiment_run.metadata
        else {}
    )

    # Format the response
    response = {
        "run_id": experiment_run.run_id if experiment_run else None,
        "config": _format_config_response(metadata),
    }
    return response


@router.get(
    "/{expid}/runs/{run_id}/user-metrics", name="Get the user-defined metrics of a run"
)
async def get_run_user_metrics(
    expid: str,
    run_id: int,
    user_id: Optional[str] = Depends(auth_token_dependency()),
):
    """
    Get the user-defined metrics of a specific run of an experiment
    """
    user_metric_repo = create_user_metric_repository(expid)

    metrics = [
        {
            "job_name": metric.job_name,
            "metric_name": metric.metric_name,
            "metric_value": metric.metric_value,
            "modified": metric.modified,
        }
        for metric in user_metric_repo.get_by_run_id(run_id)
    ]

    return {"run_id": run_id, "metrics": metrics}


@router.get("/{expid}/user-metrics-runs", name="Get the runs with user-defined metrics")
async def get_runs_with_user_metrics(
    expid: str,
    user_id: Optional[str] = Depends(auth_token_dependency()),
):
    """
    Get the runs with user-defined metrics of an experiment
    """
    user_metric_repo = create_user_metric_repository(expid)

    try:
        run_ids = user_metric_repo.get_runs_with_user_metrics()
    except Exception:
        run_ids = []
        logger.error("Error while getting the runs with user-defined metrics")
        logger.error(traceback.format_exc())

    return {
        "runs": [
            {
                "run_id": run_id,
            }
            for run_id in run_ids
        ]
    }


class JobDetailResponse(BaseModel):
    # From pkl
    name: str
    status: str
    section: Optional[str] = None
    date: Optional[str] = None
    member: Optional[str] = None
    chunk: Optional[int] = None
    # split: Optional[str] = None
    out_path_local: Optional[str] = None
    err_path_local: Optional[str] = None
    # From config
    chunk_size: Optional[int] = None
    chunk_unit: Optional[str] = None
    platform: Optional[str] = None
    # From historical DB
    remote_id: Optional[int] = None
    qos: Optional[str] = None
    workflow_commit: Optional[str] = None
    processors: Optional[int] = None  # Requested ncpus
    submit: Optional[str] = None
    start: Optional[str] = None
    finish: Optional[str] = None
    wallclock: Optional[str] = None
    # Wrapper data
    last_wrapper: Optional[str] = None


@router.get("/{expid}/jobs/{job_name}", name="Get experiment job detail")
async def get_experiment_job_detail(
    expid: str,
    job_name: str,
    user_id: Optional[str] = Depends(auth_token_dependency()),
) -> JobDetailResponse:
    """
    Get the details of a specific job of an experiment
    """
    # Get the latest job details from the retriever
    try:
        job_detail_retriever = JobDetailRetriever(expid, job_name)
        job_detail_retriever.load_data()
    except JobNotFoundError:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Job with name '{job_name}' not found in experiment '{expid}'",
        )
    except Exception:
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail="Error while retrieving job details",
        )

    # Get the latest logs for the job, if it has finished
    exp_paths = ExperimentPaths(expid)
    job_logs_out = []
    job_logs_err = []
    try:
        if job_detail_retriever.status_code in [Status.COMPLETED, Status.FAILED]:
            for f in os.scandir(exp_paths.tmp_log_dir):
                if not f.is_file():
                    continue
                if re.match(
                    rf"^{re.escape(job_detail_retriever.name)}.*\.out(\.xz|\.gz)?$",
                    f.name,
                ):
                    job_logs_out.append(f.name)
                elif re.match(
                    rf"^{re.escape(job_detail_retriever.name)}.*\.err(\.xz|\.gz)?$",
                    f.name,
                ):
                    job_logs_err.append(f.name)

        # Sort logs by time in the name, assuming the format is <job_name>.<timestamp>.[out|err]
        job_logs_out.sort()
        job_logs_err.sort()
    except Exception:
        logger.warning("Error while retrieving job logs")
        logger.warning(traceback.format_exc())

    # Build the response
    response = JobDetailResponse(
        name=job_name,
        status=Status.VALUE_TO_KEY.get(
            job_detail_retriever.status_code, Status.UNKNOWN
        ),
    )

    response = response.model_copy(
        update={
            "section": job_detail_retriever.section,
            "date": job_detail_retriever.date.strftime("%Y%m%d")
            if job_detail_retriever.date
            else None,
            "member": job_detail_retriever.member,
            "chunk": job_detail_retriever.chunk,
            "out_path_local": os.path.join(exp_paths.tmp_log_dir, job_logs_out[-1])
            if job_logs_out
            else None,
            "err_path_local": os.path.join(exp_paths.tmp_log_dir, job_logs_err[-1])
            if job_logs_err
            else None,
            "chunk_size": job_detail_retriever.chunk_size,
            "chunk_unit": job_detail_retriever.chunk_unit,
            "platform": job_detail_retriever.platform,
            "remote_id": job_detail_retriever.remote_id,
            "qos": job_detail_retriever.qos,
            "processors": job_detail_retriever.processors,
            "wallclock": job_detail_retriever.wallclock,
            "workflow_commit": job_detail_retriever.workflow_commit,
            "submit": timestamp_to_datetime_format(job_detail_retriever.submit),
            "start": timestamp_to_datetime_format(job_detail_retriever.start),
            "finish": timestamp_to_datetime_format(job_detail_retriever.finish),
            "last_wrapper": job_detail_retriever.last_wrapper,
        }
    )

    return response


@router.get("/{expid}/jobs/{job_name}/parents", name="Get experiment job parents")
async def get_experiment_job_parents(
    expid: str,
    job_name: str,
    include_status: bool = False,
    user_id: Optional[str] = Depends(auth_token_dependency()),
) -> Dict:
    """
    Get the parents of a specific job of an experiment.
    Set include_status=true to also return the current status of each parent job.
    """
    try:
        structure_repo = create_experiment_structure_repository(expid)
        parents = structure_repo.get_parents(job_name)
    except Exception as exc:
        error_message = "Error while reading the experiment structure"
        logger.error(error_message + f": {exc}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=error_message
        )

    parent_items = [{"job_name": parent} for parent in parents]

    if include_status and parents:
        try:
            job_list_repo = create_jobs_repository(expid)
            jobs_data = job_list_repo.get_by_names(parents)
            status_map = {
                job.name: Status.VALUE_TO_KEY.get(job.status, Status.UNKNOWN)
                for job in jobs_data
            }
            for item in parent_items:
                item["status"] = status_map.get(item["job_name"])
        except Exception as exc:
            logger.warning(f"Error while fetching parent job statuses: {exc}")
            logger.warning(traceback.format_exc())

    return {"parents": parent_items}


@router.get("/{expid}/jobs/{job_name}/children", name="Get experiment job children")
async def get_experiment_job_children(
    expid: str,
    job_name: str,
    include_status: bool = False,
    user_id: Optional[str] = Depends(auth_token_dependency()),
) -> Dict:
    """
    Get the children of a specific job of an experiment
    Set include_status=true to also return the current status of each child job.
    """
    try:
        structure_repo = create_experiment_structure_repository(expid)
        children = structure_repo.get_children(job_name)
    except Exception as exc:
        error_message = "Error while reading the experiment structure"
        logger.error(error_message + f": {exc}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail=error_message
        )

    child_items = [{"job_name": child} for child in children]

    if include_status and children:
        try:
            job_list_repo = create_jobs_repository(expid)
            jobs_data = job_list_repo.get_by_names(children)
            status_map = {
                job.name: Status.VALUE_TO_KEY.get(job.status, Status.UNKNOWN)
                for job in jobs_data
            }
            for item in child_items:
                item["status"] = status_map.get(item["job_name"])
        except Exception as exc:
            logger.warning(f"Error while fetching child job statuses: {exc}")
            logger.warning(traceback.format_exc())

    return {"children": child_items}
