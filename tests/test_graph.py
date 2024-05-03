import os

from sqlalchemy import create_engine
from autosubmit_api.builders.configuration_facade_builder import (
    AutosubmitConfigurationFacadeBuilder,
    ConfigurationFacadeDirector,
)
from autosubmit_api.builders.joblist_loader_builder import (
    JobListLoaderBuilder,
    JobListLoaderDirector,
)
from autosubmit_api.database import tables
from autosubmit_api.components.experiment.graph_drawer import ExperimentGraphDrawing
from autosubmit_api.monitor.monitor import Monitor
from autosubmit_api.persistance.experiment import ExperimentPaths


class TestPopulateDB:

    def test_monitor_dot(self, fixture_mock_basic_config):
        expid = "a003"
        job_list_loader = JobListLoaderDirector(
            JobListLoaderBuilder(expid)
        ).build_loaded_joblist_loader()

        monitor = Monitor()
        graph = monitor.create_tree_list(
            expid,
            job_list_loader.jobs,
            None,
            dict(),
            False,
            job_list_loader.job_dictionary,
        )
        assert graph

        result = graph.create("dot", format="plain")
        assert result and len(result) > 0

    def test_process_graph(self, fixture_mock_basic_config):
        expid = "a003"
        experimentGraphDrawing = ExperimentGraphDrawing(expid)
        job_list_loader = JobListLoaderDirector(
            JobListLoaderBuilder(expid)
        ).build_loaded_joblist_loader()

        autosubmit_configuration_facade = ConfigurationFacadeDirector(
            AutosubmitConfigurationFacadeBuilder(expid)
        ).build_autosubmit_configuration_facade()

        exp_paths = ExperimentPaths(expid)
        with create_engine(
            f"sqlite:///{ os.path.abspath(exp_paths.graph_data_db)}"
        ).connect() as conn:
            conn.execute(tables.graph_data_table.delete())
            conn.commit()

            experimentGraphDrawing.calculate_drawing(
                allJobs=job_list_loader.jobs,
                independent=False,
                num_chunks=autosubmit_configuration_facade.chunk_size,
                job_dictionary=job_list_loader.job_dictionary,
            )

            assert (
                experimentGraphDrawing.coordinates
                and len(experimentGraphDrawing.coordinates) == 8
            )

            rows = conn.execute(tables.graph_data_table.select()).all()

            assert len(rows) == 8
            for job in rows:
                job_name: str = job.job_name
                assert job_name.startswith(expid)
