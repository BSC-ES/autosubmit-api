from typing import Any, Dict
import pytest

from autosubmit_api.builders.joblist_helper_builder import (
    JobListHelperBuilder,
    JobListHelperDirector,
)
from autosubmit_api.performance.performance_metrics import PerformanceMetrics


@pytest.mark.parametrize(
    "expid, expected, counters",
    [
        (
            "a003",
            {
                "total_sim_run_time": 0,
                "total_sim_queue_time": 0,
                "SYPD": 0,
                "ASYPD": 0,
                "CHSY": 0,
                "JPSY": 0,
                "RSYPD": 0,
                "processing_elements": 16,
                "sim_processors": 16,
                "post_jobs_total_time_average": 0.0,
            },
            {"considered_jobs_count": 0, "not_considered_jobs_count": 0},
        ),
        (
            "a3tb",
            {
                "ASYPD": 12.9109,
                "CHSY": 1167.36,
                "JPSY": 57300000.0,
                "RSYPD": 0,
                "SYPD": 15.7895,
                "post_jobs_total_time_average": 0.0,
                "processing_elements": 768,
                "sim_processors": 768,
                "total_sim_queue_time": 610,
                "total_sim_run_time": 2736,
            },
            {"considered_jobs_count": 6, "not_considered_jobs_count": 0},
        ),
        (
            "a007",
            {
                "ASYPD": 3840.0,
                "CHSY": 0.03,
                "JPSY": 0,
                "RSYPD": 1066.6667,
                "SYPD": 5760.0,
                "post_jobs_total_time_average": 5.0,
                "processing_elements": 8,
                "sim_processors": 8,
                "total_sim_queue_time": 0,
                "total_sim_run_time": 10,
            },
            {"considered_jobs_count": 2, "not_considered_jobs_count": 0},
        ),
    ],
)
def test_performance_metrics(
    fixture_mock_basic_config,
    expid: str,
    expected: Dict[str, Any],
    counters: Dict[str, Any],
):
    performance_metrics = PerformanceMetrics(
        expid,
        JobListHelperDirector(JobListHelperBuilder(expid)).build_job_list_helper(),
    )

    # Assert properties
    assert {
        "total_sim_run_time": performance_metrics.total_sim_run_time,
        "total_sim_queue_time": performance_metrics.total_sim_queue_time,
        "SYPD": performance_metrics.SYPD,
        "ASYPD": performance_metrics.ASYPD,
        "CHSY": performance_metrics.CHSY,
        "JPSY": performance_metrics.JPSY,
        "RSYPD": performance_metrics.RSYPD,
        "processing_elements": performance_metrics.processing_elements,
        "sim_processors": performance_metrics._sim_processors,
        "post_jobs_total_time_average": performance_metrics.post_jobs_total_time_average,
    } == expected

    # Assert considered jobs count
    assert len(performance_metrics._considered) == counters["considered_jobs_count"]
    assert (
        len(performance_metrics._not_considered)
        == counters["not_considered_jobs_count"]
    )
