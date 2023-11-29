from http import HTTPStatus
import math
import os
import traceback
from typing import Optional
from flask import request
from autosubmit_api.auth import with_auth_token
from autosubmit_api.builders.configuration_facade_builder import (
    AutosubmitConfigurationFacadeBuilder,
    ConfigurationFacadeDirector,
)
from autosubmit_api.builders.experiment_history_builder import (
    ExperimentHistoryBuilder,
    ExperimentHistoryDirector,
)
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.database.common import (
    create_main_db_conn,
    execute_with_limit_offset,
)
from autosubmit_api.database.db_common import update_experiment_description_owner
from autosubmit_api.database.models import Experiment
from autosubmit_api.database.queries import generate_query_listexp_extended
from autosubmit_api.logger import logger, with_log_run_times
from autosubmit_api.views import v3


PAGINATION_LIMIT_DEFAULT = 12


@with_log_run_times(logger, "EXPDESC")
@with_auth_token()
def experiment_description_view(expid, user_id: Optional[str] = None):
    """
    Replace the description of the experiment.
    """
    new_description = None
    if request.is_json:
        body_data = request.json
        new_description = body_data.get("description", None)
    return (
        update_experiment_description_owner(expid, new_description, user_id),
        HTTPStatus.OK if user_id else HTTPStatus.UNAUTHORIZED,
    )


@with_log_run_times(logger, "SEARCH4")
@with_auth_token()
def search_experiments_view(user_id: Optional[str] = None):
    """
    Search experiments view targeted to handle args
    """
    # Parse args
    logger.debug("Search args: " + str(request.args))

    query = request.args.get("query")
    only_active = request.args.get("only_active") == "true"
    owner = request.args.get("owner")
    exp_type = request.args.get("exp_type")

    try:
        page = max(request.args.get("page", default=1, type=int), 1)
        page_size = request.args.get(
            "page_size", default=PAGINATION_LIMIT_DEFAULT, type=int
        )
        if page_size > 0:
            offset = (page - 1) * page_size
        else:
            page_size = None
            offset = None
    except:
        return {
            "error": True,
            "error_message": "Bad Request: invalid params",
        }, HTTPStatus.BAD_REQUEST

    # Query
    conn = create_main_db_conn()
    statement = generate_query_listexp_extended(
        query=query,
        only_active=only_active,
        owner=owner,
        exp_type=exp_type,
    )
    query_result, total_rows = execute_with_limit_offset(
        statement=statement,
        conn=conn,
        limit=page_size,
        offset=offset,
    )
    conn.close()

    # Process experiments
    experiments = []
    for raw_exp in query_result:
        exp = Experiment.model_validate(raw_exp._mapping)

        # Get user
        user = exp.user
        if not user:
            # Retrieve user from path
            path = APIBasicConfig.LOCAL_ROOT_DIR + "/" + exp.name
            if os.path.exists(path):
                main_folder = os.stat(path)
                user = (
                    os.popen("id -nu {0}".format(str(main_folder.st_uid)))
                    .read()
                    .strip()
                )

        # Get additional data from config files
        version = "Unknown"
        wrapper = None
        last_modified_pkl_datetime = None
        hpc = exp.hpc
        try:
            autosubmit_config_facade = ConfigurationFacadeDirector(
                AutosubmitConfigurationFacadeBuilder(exp.name)
            ).build_autosubmit_configuration_facade()
            version = autosubmit_config_facade.get_autosubmit_version()
            wrapper = autosubmit_config_facade.get_wrapper_type()
            last_modified_pkl_datetime = (
                autosubmit_config_facade.get_pkl_last_modified_time_as_datetime()
            )
            hpc = autosubmit_config_facade.get_main_platform()
        except Exception as exc:
            logger.warning(f"Config files params were unable to get on search: {exc}")
            logger.warning(traceback.format_exc())

        # Get current run data from history
        last_modified_timestamp = exp.created
        completed = exp.completed_jobs if exp.completed_jobs else 0
        total = exp.total_jobs if exp.total_jobs else 0
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
            if (
                current_run
                and current_run.total > 0
                and (
                    current_run.total == total
                    or current_run.modified_timestamp > last_modified_timestamp
                )
            ):
                completed = current_run.completed
                total = current_run.total
                submitted = current_run.submitted
                queuing = current_run.queuing
                running = current_run.running
                failed = current_run.failed
                suspended = current_run.suspended
                last_modified_timestamp = current_run.modified_timestamp
        except Exception as exc:
            logger.warning((f"Exception getting the current run on search: {exc}"))
            logger.warning(traceback.format_exc())

        # Format data
        experiments.append(
            {
                "id": exp.id,
                "name": exp.name,
                "user": user,
                "description": exp.description,
                "hpc": hpc,
                "status": exp.status if exp.status else "NOT RUNNING",
                "completed": completed,
                "total": total,
                "version": version,
                "wrapper": wrapper,
                "submitted": submitted,
                "queuing": queuing,
                "running": running,
                "failed": failed,
                "suspended": suspended,
                "modified": last_modified_pkl_datetime,
            }
        )

    # Response
    response = {
        "experiments": experiments,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_pages": math.ceil(total_rows / page_size) if page_size else 1,
            "page_items": len(experiments),
            "total_items": total_rows,
        },
    }
    return response


@with_log_run_times(logger, "GRAPH4")
@with_auth_token()
def exp_graph_view(expid: str, user_id: Optional[str] = None):
    layout = request.args.get("layout", default="standard")
    grouped = request.args.get("grouped", default="none")
    return v3.get_graph_format(expid, layout, grouped)


@with_log_run_times(logger, "STAT4")
@with_auth_token()
def exp_stats_view(expid: str, user_id: Optional[str] = None):
    filter_period = request.args.get("filter_period", type=int)
    filter_type = request.args.get("filter_type", default="Any")
    return v3.get_experiment_statistics(expid, filter_period, filter_type)
