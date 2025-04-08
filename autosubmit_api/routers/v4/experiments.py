import asyncio
from collections import deque
import csv
from datetime import datetime, timezone
from http import HTTPStatus
from io import StringIO
import json
import math
import traceback
from typing import Annotated, Any, Dict, List, Literal, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, StreamingResponse
from autosubmit_api.auth import auth_token_dependency
from autosubmit_api.builders.experiment_builder import ExperimentBuilder
from autosubmit_api.config.config_common import AutosubmitConfigResolver
from autosubmit_api.database import tables
from autosubmit_api.common.utils import Status
from autosubmit_api.database.db_jobdata import JobDataStructure
from autosubmit_api.database.models import BaseExperimentModel
from autosubmit_api.repositories.job_data import create_experiment_job_data_repository
from autosubmit_api.repositories.join.experiment_join import (
    create_experiment_join_repository,
)
from autosubmit_api.logger import logger
from autosubmit_api.builders.experiment_history_builder import (
    ExperimentHistoryBuilder,
    ExperimentHistoryDirector,
)
from autosubmit_api.models.requests import (
    ExperimentsSearchRequest,
)
from autosubmit_api.models.responses import (
    ExperimentFSConfigResponse,
    ExperimentJobsResponse,
    ExperimentRunConfigResponse,
    ExperimentRunsResponse,
    ExperimentWrappersResponse,
    ExperimentsSearchResponse,
)
from autosubmit_api.persistance.job_package_reader import JobPackageReader
from autosubmit_api.persistance.pkl_reader import PklReader
from bscearth.utils.config_parser import ConfigParserFactory
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.config.confConfigStrategy import confConfigStrategy

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
    return exp_builder.product.model_dump(include=tables.experiment_table.c.keys())


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
        current_content = PklReader(expid).parse_job_list()
    except Exception as exc:
        error_message = "Error while reading the job list"
        logger.error(error_message + f": {exc}")
        logger.error(traceback.print_exc())
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


@router.get("/{expid}/jobs-history", name="Get experiment jobs history")
async def get_jobs_history(
    expid: str,
    format: Annotated[Literal["json", "csv"], Query()] = "json",
    user_id: Optional[str] = Depends(auth_token_dependency()),
) -> Dict[str, Any]:
    """
    Get the jobs history of an experiment
    """

    def _generate_csv(expid: str):
        job_generator = create_experiment_job_data_repository(expid).get_all_generator()

        csv_file = StringIO()
        writer = csv.writer(csv_file)

        # Yield the header first
        header = [
            "job_name",
            "run_id",
            "section",
            "status",
            "submit",
            "start",
            "finish",
            "out",
            "err",
        ]
        writer.writerow(header)
        csv_file.seek(0)
        yield csv_file.read()
        csv_file.seek(0)
        csv_file.truncate(0)

        # Yield each job row
        for job in job_generator:
            writer.writerow(
                [
                    job.job_name,
                    job.run_id,
                    job.section,
                    job.status,
                    job.submit,
                    job.start,
                    job.finish,
                    job.out,
                    job.err,
                ]
            )
            csv_file.seek(0)
            yield csv_file.read()
            csv_file.seek(0)
            csv_file.truncate(0)

    if format == "csv":
        response = StreamingResponse(_generate_csv(expid), media_type="text/csv")
        response.headers["Content-Disposition"] = (
            f"attachment; filename=jobs_history_{expid}.csv"
        )
        return response

    raise HTTPException(
        status_code=HTTPStatus.NOT_IMPLEMENTED, detail="Only format=csv is supported"
    )
