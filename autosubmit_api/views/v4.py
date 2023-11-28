import os
import traceback
from typing import Optional
from flask import request
from autosubmit_api.builders.configuration_facade_builder import (
    AutosubmitConfigurationFacadeBuilder,
    ConfigurationFacadeDirector,
)
from autosubmit_api.builders.experiment_history_builder import (
    ExperimentHistoryBuilder,
    ExperimentHistoryDirector,
)
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.database.models import Experiment
from autosubmit_api.database.queries import query_listexp_extended
from autosubmit_api.logger import logger, with_log_run_times


PAGINATION_LIMIT_DEFAULT = 12


@with_log_run_times(logger, "SEARCH4")
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

    limit = int(request.args.get("limit", PAGINATION_LIMIT_DEFAULT))
    offset = int(request.args.get("offset", 0))

    # Query
    query_result = query_listexp_extended(
        query=query,
        only_active=only_active,
        owner=owner,
        exp_type=exp_type,
        limit=limit,
        offset=offset,
    )

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
        "limit": limit,
        "offset": offset,
        "experiments": experiments,
        "count": len(experiments),
    }
    return response
