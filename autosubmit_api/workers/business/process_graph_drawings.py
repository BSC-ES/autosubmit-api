import time
import traceback
from autosubmit_api.common import utils as common_utils
from autosubmit_api.components.representations.graph.graph_drawing import ExperimentGraphDrawing
from autosubmit_api.builders.configuration_facade_builder import (
    ConfigurationFacadeDirector,
    AutosubmitConfigurationFacadeBuilder,
)
from autosubmit_api.builders.joblist_loader_builder import (
    JobListLoaderBuilder,
    JobListLoaderDirector,
)
from typing import List, Any, Optional

from autosubmit_api.repositories.experiment_status import create_experiment_status_repository


def process_active_graphs():
    """
    Process the list of active experiments to generate the positioning of their graphs
    """
    try:
        active_experiments = create_experiment_status_repository().get_only_running_expids()

        for expid in active_experiments:
            try:
                autosubmit_configuration_facade = ConfigurationFacadeDirector(
                    AutosubmitConfigurationFacadeBuilder(expid)
                ).build_autosubmit_configuration_facade()
                if common_utils.is_version_historical_ready(
                    autosubmit_configuration_facade.get_autosubmit_version()
                ):
                    _process_graph(expid, autosubmit_configuration_facade.chunk_size)
            except Exception:
                print((traceback.format_exc()))
                print(("Error while processing: {}".format(expid)))

    except Exception as exp:
        print((traceback.format_exc()))
        print(("Error while processing graph drawing: {}".format(exp)))


def _process_graph(expid: str, chunk_size: int) -> Optional[List[Any]]:
    result = None
    experimentGraphDrawing = ExperimentGraphDrawing(expid)
    locked = experimentGraphDrawing.locked
    # print("Start Processing {} with {} jobs".format(expid, job_count))
    if not locked:
        start_time = time.time()
        job_list_loader = JobListLoaderDirector(
            JobListLoaderBuilder(expid)
        ).build_loaded_joblist_loader()
        current_data = experimentGraphDrawing.get_validated_data(job_list_loader.jobs)
        if not current_data:
            print(("Must update {}".format(expid)))
            result = experimentGraphDrawing.calculate_drawing(
                job_list_loader.jobs,
                independent=False,
                num_chunks=chunk_size,
                job_dictionary=job_list_loader.job_dictionary,
            )
            print(
                (
                    "Time Spent in {}: {} seconds.".format(
                        expid, int(time.time() - start_time)
                    )
                )
            )
    else:
        print(("{} Locked".format(expid)))

    return result
