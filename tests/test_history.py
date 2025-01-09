import pytest
from typing import Any, Dict, Tuple
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.history.database_managers.experiment_history_db_manager import (
    ExperimentHistoryDbManager,
)


@pytest.mark.parametrize(
    "expid, expected_last_run, expected_number_of_runs",
    [
        (
            "a003",
            {
                "run_id": 3,
                "created": "2024-01-12-16:37:15",
                "modified": "2024-01-12-16:39:06",
                "start": 1705073835,
                "finish": 1705073946,
                "chunk_unit": "month",
                "chunk_size": 4,
                "submitted": 0,
                "queuing": 0,
                "running": 0,
                "completed": 8,
                "failed": 0,
                "total": 8,
                "suspended": 0,
            },
            3,
        ),
        (
            "a1ve",
            {
                "run_id": 1,
                "created": "2024-12-12-15:14:44",
                "modified": "2024-12-12-15:16:29",
                "start": 1734012884,
                "finish": 1734012989,
                "chunk_unit": "month",
                "chunk_size": 4,
                "submitted": 0,
                "queuing": 0,
                "running": 0,
                "completed": 8,
                "failed": 0,
                "total": 8,
                "suspended": 0,
            },
            1,
        ),
        (
            "a3tb",
            {
                "run_id": 51,
                "created": "2022-03-15-13:33:39",
                "modified": "2022-03-15-16:12:50",
                "start": 1647347619,
                "finish": 1647352313,
                "chunk_unit": "month",
                "chunk_size": 1,
                "submitted": 0,
                "queuing": 1,
                "running": 0,
                "completed": 28,
                "failed": 0,
                "total": 55,
                "suspended": 2,
            },
            51,
        ),
        (
            "a6zj",
            {
                "run_id": 1,
                "created": "2024-04-11-16:53:56",
                "modified": "2024-04-11-16:53:56",
                "start": 1712847236,
                "finish": 0,
                "chunk_unit": "month",
                "chunk_size": 4,
                "submitted": 0,
                "queuing": 0,
                "running": 0,
                "completed": 0,
                "failed": 0,
                "total": 10,
                "suspended": 0,
            },
            1,
        ),
    ],
)
def test_runs_retrievals(
    fixture_mock_basic_config: APIBasicConfig,
    expid: str,
    expected_last_run: Dict[str, Any],
    expected_number_of_runs: int,
):
    history_db_manager = ExperimentHistoryDbManager(expid, fixture_mock_basic_config)

    # Get the last run and the selected run
    last_run = history_db_manager.get_experiment_run_dc_with_max_id()
    selected_run = history_db_manager.get_experiment_run_by_id(last_run.run_id)

    # Check if the last run and the selected run are the same as the expected run
    assert last_run.run_id == expected_last_run["run_id"] == selected_run.run_id
    assert last_run.created == expected_last_run["created"] == selected_run.created
    assert last_run.modified == expected_last_run["modified"] == selected_run.modified
    assert last_run.start == expected_last_run["start"] == selected_run.start
    assert last_run.finish == expected_last_run["finish"] == selected_run.finish
    assert (
        last_run.chunk_unit
        == expected_last_run["chunk_unit"]
        == selected_run.chunk_unit
    )
    assert (
        last_run.chunk_size
        == expected_last_run["chunk_size"]
        == selected_run.chunk_size
    )
    assert (
        last_run.submitted == expected_last_run["submitted"] == selected_run.submitted
    )
    assert last_run.queuing == expected_last_run["queuing"] == selected_run.queuing
    assert last_run.running == expected_last_run["running"] == selected_run.running
    assert (
        last_run.completed == expected_last_run["completed"] == selected_run.completed
    )
    assert last_run.failed == expected_last_run["failed"] == selected_run.failed
    assert last_run.total == expected_last_run["total"] == selected_run.total
    assert (
        last_run.suspended == expected_last_run["suspended"] == selected_run.suspended
    )

    # Get all runs
    runs = history_db_manager.get_experiment_runs_dcs()

    # Check if the last run is in the list of runs
    assert last_run.run_id in [run.run_id for run in runs]

    # Check size of the list of runs
    assert len(runs) == expected_number_of_runs


@pytest.mark.parametrize(
    "expid, expected_number_job_rows, expected_number_last_job_rows, expected_completed_per_wrapper, expected_completed_per_section, expected_number_job_rows_by_job_name",
    [
        (
            "a003",
            16,
            8,
            {},
            {"LOCAL_SETUP": 2, "SIM": 4},
            {"a003_REMOTE_SETUP": 2, "a003_20220401_fc0_1_SIM": 2},
        ),
        (
            "a1ve",
            16,
            8,
            {},
            {"INI": 1, "SIM": 1},
            {"a1ve_SIM": 2, "a1ve_1_ASIM": 2, "a1ve_2_ASIM": 2},
        ),
        (
            "a3tb",
            284,
            162,
            {(3, 3): 0},
            {"LOCAL_SETUP": 20, "SIM": 30},
            {"a3tb_LOCAL_SETUP": 20, "a3tb_20000101_fc01_1_SIM": 1},
        ),
        ("a6zj", 0, 0, {}, {}, {}),
    ],
)
def test_jobs_retrievals(
    fixture_mock_basic_config: APIBasicConfig,
    expid: str,
    expected_number_job_rows: int,
    expected_completed_per_wrapper: Dict[Tuple[int, int], int],
    expected_completed_per_section: Dict[str, int],
    expected_number_last_job_rows: int,
    expected_number_job_rows_by_job_name: Dict[str, int],
):
    history_db_manager = ExperimentHistoryDbManager(expid, fixture_mock_basic_config)

    # Get all jobs
    all_jobs = history_db_manager.get_job_data_dcs_all()

    # Check size of the list of jobs
    assert len(all_jobs) == expected_number_job_rows

    # Get all completed jobs per wrapper run id
    for (
        package_code,
        run_id,
    ), expected_completed in expected_completed_per_wrapper.items():
        assert package_code > 2
        completed_jobs_per_wrapper = (
            history_db_manager.get_job_data_dc_COMPLETED_by_wrapper_run_id(
                package_code, run_id
            )
        )

        # Check size of the list of completed jobs per wrapper run id
        assert len(completed_jobs_per_wrapper) == expected_completed

    # Get all completed jobs per section
    for section, expected_completed in expected_completed_per_section.items():
        completed_jobs_per_section = (
            history_db_manager.get_job_data_dcs_COMPLETED_by_section(section)
        )

        # Check size of the list of completed jobs per section
        assert len(completed_jobs_per_section) == expected_completed

    # Get all last jobs
    last_jobs = history_db_manager.get_all_last_job_data_dcs()

    # Check size of the list of last jobs
    assert len(last_jobs) == expected_number_last_job_rows

    # Get all job rows by job name
    for (
        job_name,
        expected_number_job_rows,
    ) in expected_number_job_rows_by_job_name.items():
        job_rows = history_db_manager.get_job_data_dcs_by_name(job_name)

        # Check size of the list of job rows by job name
        assert len(job_rows) == expected_number_job_rows
