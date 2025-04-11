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
                "SY": 0,
                "SYPD": 0,
                "PSYPD": 0,
                "QSYPD": 0,
                "CHSY": 0,
                "JPSY": 0,
                "RSYPD": 0,
                "processing_elements": 16,
                "sim_processors": 16,
                "post_jobs_total_time_average": 0.0,
                "total_energy": 0.0,
                "total_footprint": 0.0,
                "sim_jobs_platform": 'MN4',
                "sim_jobs_platform_PUE": 1.35,
                "sim_jobs_platform_CF": 357000,
                "total_core_hours": 0.0,
            },
            {"considered_jobs_count": 0, "not_considered_jobs_count": 0},
        ),
        (
            "a3tb",
            {
                "SY": 0.49999999999999994,
                "SYPD": 15.7895,
                "PSYPD": 12.9109,
                "QSYPD": 12.9109,
                "CHSY": 1167.36,
                "JPSY": 57300000.0,
                "RSYPD": 0,
                "post_jobs_total_time_average": 0.0,
                "processing_elements": 768,
                "sim_processors": 768,
                "total_sim_queue_time": 610,
                "total_sim_run_time": 2736,
                "total_energy": 28650000,
                "total_footprint": 0.0,
                "sim_jobs_platform": '',
                "sim_jobs_platform_PUE": 0.0,
                "sim_jobs_platform_CF": 0.0,
                "total_core_hours": 583.68,
            },
            {"considered_jobs_count": 6, "not_considered_jobs_count": 0},
        ),
        (
            "a007",
            {
                "SY": 0.6666666666666666,
                "SYPD": 5760.0,
                "PSYPD": 3840.0,
                "QSYPD": 5760.0,
                "CHSY": 0.03,
                "JPSY": 0,
                "RSYPD": 1066.6667,
                "post_jobs_total_time_average": 5.0,
                "processing_elements": 8,
                "sim_processors": 8,
                "total_sim_queue_time": 0,
                "total_sim_run_time": 10,
                "total_energy": 0.0,
                "total_footprint": 0.0,
                "sim_jobs_platform": 'LOCAL',
                "sim_jobs_platform_PUE": 0.0,
                "sim_jobs_platform_CF": 0.0,
                "total_core_hours": 0.02,
            },
            {"considered_jobs_count": 2, "not_considered_jobs_count": 0},
        ),
        (
            "a8qc",
            {
                "SY": 0.01917808219178082,
                "SYPD": 0.3623,
                "PSYPD": 0.3538,
                "QSYPD": 0.3538,
                "CHSY": 19075.9429,
                "JPSY": 574614285.7143,
                "RSYPD": 0.9134,
                "post_jobs_total_time_average": 0.0,
                "processing_elements": 288,
                "sim_processors": 288,
                "total_sim_queue_time": 111,
                "total_sim_run_time": 4573,
                "total_energy": 11020000,
                "total_footprint": 1180.242,
                "sim_jobs_platform": 'MARENOSTRUM5',
                "sim_jobs_platform_PUE": 1.08,
                "sim_jobs_platform_CF": 357000,
                "total_core_hours": 365.84,
            },
            {"considered_jobs_count": 7, "not_considered_jobs_count": 0},
        )
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

    metrics = {
        "SY": performance_metrics.valid_sim_yps_sum,
        "SYPD": performance_metrics.SYPD,
        "PSYPD": performance_metrics.PSYPD,
        "QSYPD": performance_metrics.QSYPD,
        "CHSY": performance_metrics.CHSY,
        "JPSY": performance_metrics.JPSY,
        "RSYPD": performance_metrics.RSYPD,
        "processing_elements": performance_metrics.processing_elements,
        "sim_processors": performance_metrics._sim_processors,
        "post_jobs_total_time_average": performance_metrics.post_jobs_total_time_average,
        "total_sim_run_time": performance_metrics.total_sim_run_time,
        "total_sim_queue_time": performance_metrics.total_sim_queue_time,
        "total_energy": performance_metrics.valid_sim_energy_sum,
        "total_footprint": performance_metrics.valid_sim_footprint_sum,
        "sim_jobs_platform": performance_metrics.sim_jobs_platform,
        "sim_jobs_platform_PUE": performance_metrics.sim_platform_PUE,
        "sim_jobs_platform_CF": performance_metrics.sim_platform_CF,
        "total_core_hours": performance_metrics.valid_sim_core_hours_sum,
    }

    #Assert properties
    for key, expected_value in expected.items():
        actual_value = metrics[key]
        if isinstance(expected_value, float):
            assert actual_value == pytest.approx(expected_value, rel=1e-2), \
                f"Assertion failed for key '{key}': expected {expected_value}, but got {actual_value}"
        else:
            assert actual_value == expected_value, \
                f"Assertion failed for key '{key}': expected {expected_value}, but got {actual_value}"

    # Assert considered jobs count
    assert len(performance_metrics._considered) == counters["considered_jobs_count"]
    assert (
        len(performance_metrics._not_considered)
        == counters["not_considered_jobs_count"]
    )
