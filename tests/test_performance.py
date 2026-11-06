from types import SimpleNamespace
from typing import Any, Dict

import pytest

from autosubmit_api.builders.joblist_helper_builder import (
    JobListHelperBuilder,
    JobListHelperDirector,
)
from autosubmit_api.common.utils import Status
from autosubmit_api.components.jobs.job_factory import SimJob, StandardJob
from autosubmit_api.performance.performance_metrics import PerformanceMetrics
from autosubmit_api.performance.utils import (
    calculate_ASYPD_perjob,
    calculate_SYPD_perjob,
)


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
                "ASYPD": 0,
                "CHSY": 0,
                "JPSY": 0,
                "RSYPD": 0,
                "processing_elements": 16,
                "sim_processors": 1,
                "post_jobs_total_time_average": 0.0,
                "total_energy": 0.0,
                "total_footprint": 0.0,
                "sim_jobs_platform": "MN4",
                "sim_jobs_platform_PUE": 1.35,
                "sim_jobs_platform_CF": 357000,
            },
            {"considered_jobs_count": 0, "not_considered_jobs_count": 0},
        ),
        (
            "a3tb",
            {
                "SY": 0.49999999999999994,
                "SYPD": 15.7895,
                "ASYPD": 12.9109,
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
                "sim_jobs_platform": "",
                "sim_jobs_platform_PUE": 0.0,
                "sim_jobs_platform_CF": 0.0,
            },
            {"considered_jobs_count": 6, "not_considered_jobs_count": 0},
        ),
        (
            "a007",
            {
                "SY": 0.6666666666666666,
                "SYPD": 5760.0,
                "ASYPD": 3840.0,
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
                "sim_jobs_platform": "LOCAL",
                "sim_jobs_platform_PUE": 0.0,
                "sim_jobs_platform_CF": 0.0,
            },
            {"considered_jobs_count": 2, "not_considered_jobs_count": 0},
        ),
        (
            "a8qc",
            {
                "SY": 0.01917808219178082,
                "SYPD": 0.3623,
                "ASYPD": 0.3538,
                "CHSY": 19075.9429,
                "JPSY": 574614285.7143,
                "RSYPD": 0.3581,
                "post_jobs_total_time_average": 0.0,
                "processing_elements": 288,
                "sim_processors": 288,
                "total_sim_queue_time": 111,
                "total_sim_run_time": 4573,
                "total_energy": 11020000,
                "total_footprint": 1180.242,
                "sim_jobs_platform": "MARENOSTRUM5",
                "sim_jobs_platform_PUE": 1.08,
                "sim_jobs_platform_CF": 357000,
            },
            {"considered_jobs_count": 7, "not_considered_jobs_count": 0},
        ),
        (
            "aa6f",
            {
                "SY": 0.6666666666666666,
                "SYPD": 1440.0,
                "ASYPD": 49.827,
                "CHSY": 0.0,
                "JPSY": 121770.0,
                "RSYPD": 0.0,
                "post_jobs_total_time_average": 5.0,
                "processing_elements": 1,
                "sim_processors": 1,
                "total_sim_queue_time": 1111,
                "total_sim_run_time": 40,
                "total_energy": 81180,
                "total_footprint": 0.0,
                "sim_jobs_platform": "MN5",
                "sim_jobs_platform_PUE": 0.0,
                "sim_jobs_platform_CF": 0.0,
            },
            {"considered_jobs_count": 8, "not_considered_jobs_count": 0},
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

    metrics = {
        "SY": performance_metrics.valid_sim_yps_sum,
        "SYPD": performance_metrics.SYPD,
        "ASYPD": performance_metrics.ASYPD,
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
    }

    # Assert properties
    for key, expected_value in expected.items():
        actual_value = metrics[key]
        if isinstance(expected_value, float):
            assert actual_value == pytest.approx(expected_value, rel=1e-2), (
                f"Expected {key} to be approximately {expected_value}, but got {actual_value}"
            )
        else:
            assert actual_value == expected_value, (
                f"Expected {key} to be {expected_value}, but got {actual_value}"
            )

    # Assert considered jobs count
    assert len(performance_metrics._considered) == counters["considered_jobs_count"]
    assert (
        len(performance_metrics._not_considered)
        == counters["not_considered_jobs_count"]
    )
    response = performance_metrics.to_json()
    assert {
        "SYPD",
        "ASYPD",
        "RSYPD",
        "mean_sypd_per_chunk",
        "mean_qsypd_per_chunk",
        "experiment_throughput",
        "mean_csypd_per_chunk",
        "mean_cqsypd_per_chunk",
    }.issubset(response)


def _build_sim_job(
    name: str,
    chunk: int,
    submit: int,
    start: int,
    finish: int,
    years_per_sim: float = 1 / 12,
    splits: int = None,
) -> SimJob:
    job = SimJob()
    job.name = name
    job.status = Status.COMPLETED
    job.member = "fc0"
    job.chunk = chunk
    job.splits = splits
    job._submit = submit
    job._start = start
    job._finish = finish
    job.set_years_per_sim(years_per_sim)
    return job


def _build_opa_job(name: str, chunk: int, start: int, finish: int) -> StandardJob:
    job = StandardJob()
    job.name = name
    job.status = Status.COMPLETED
    job.section = "OPA"
    job.member = "fc0"
    job.chunk = chunk
    job._submit = start
    job._start = start
    job._finish = finish
    return job


def _build_metrics_without_sources(sim_jobs, opa_jobs=None) -> PerformanceMetrics:
    metrics = PerformanceMetrics.__new__(PerformanceMetrics)
    metrics.warnings = []
    metrics.pkl_organizer = SimpleNamespace(
        opa_jobs=opa_jobs or [],
        get_completed_section_jobs=lambda _: sim_jobs,
    )
    return metrics


class TestDescriptiveThroughputMetrics:
    def test_mean_throughput_keeps_splits_in_the_same_chunk(self):
        sim_jobs = [
            _build_sim_job("sim_1", 1, submit=5, start=10, finish=40),
            _build_sim_job("sim_2_1", 2, submit=15, start=20, finish=40, splits=2),
            _build_sim_job("sim_2_2", 2, submit=15, start=25, finish=50, splits=2),
        ]
        metrics = _build_metrics_without_sources(sim_jobs)

        metrics._calculate_descriptive_throughput_metrics()

        assert metrics.mean_sypd_per_chunk == pytest.approx(240.0)
        assert metrics.mean_qsypd_per_chunk == pytest.approx(205.7143)
        assert metrics.experiment_throughput == pytest.approx(320.0)

    def test_opa_metrics_use_the_last_opa_job_and_one_simulated_day(self):
        sim_jobs = [_build_sim_job("sim_1", 1, submit=5, start=10, finish=40)]
        opa_jobs = [
            _build_opa_job("opa_1", 1, start=45, finish=60),
            _build_opa_job("opa_2", 1, start=60, finish=80),
        ]
        metrics = _build_metrics_without_sources(sim_jobs, opa_jobs)

        metrics._calculate_descriptive_throughput_metrics()

        opa_throughput = round((1 / 365.25) * 86400 / 20, 4)
        assert metrics.mean_csypd_per_chunk == pytest.approx(opa_throughput)
        assert metrics.mean_cqsypd_per_chunk == pytest.approx(96.0)
        assert metrics.warnings == []

    def test_opa_metrics_ignore_chunks_without_a_matching_opa_job(self):
        sim_jobs = [
            _build_sim_job("sim_1", 1, submit=5, start=10, finish=40),
            _build_sim_job("sim_2", 2, submit=5, start=10, finish=40),
        ]
        opa_jobs = [_build_opa_job("opa_1", 1, start=40, finish=60)]
        metrics = _build_metrics_without_sources(sim_jobs, opa_jobs)

        metrics._calculate_descriptive_throughput_metrics()

        assert metrics.mean_csypd_per_chunk > 0
        assert len(metrics.warnings) == 1
        assert "not considered" in metrics.warnings[0]

    def test_opa_metrics_are_zero_when_there_are_no_opa_jobs(self):
        sim_jobs = [_build_sim_job("sim_1", 1, submit=5, start=10, finish=40)]
        metrics = _build_metrics_without_sources(sim_jobs)

        metrics._calculate_descriptive_throughput_metrics()

        assert metrics.mean_csypd_per_chunk == 0
        assert metrics.mean_cqsypd_per_chunk == 0
        assert metrics.warnings == []

    def test_chunks_without_years_per_sim_are_ignored(self):
        sim_jobs = [
            _build_sim_job("sim_1", 1, submit=5, start=10, finish=40, years_per_sim=0)
        ]
        metrics = _build_metrics_without_sources(sim_jobs)

        metrics._calculate_descriptive_throughput_metrics()

        assert metrics.mean_sypd_per_chunk == 0
        assert metrics.mean_qsypd_per_chunk == 0
        assert metrics.experiment_throughput == 0

    def test_opa_jobs_that_are_not_completed_or_not_timed_are_ignored(self):
        sim_jobs = [_build_sim_job("sim_1", 1, submit=5, start=10, finish=40)]
        failed_opa_job = _build_opa_job("opa_failed", 1, start=45, finish=60)
        failed_opa_job.status = Status.FAILED
        untimed_opa_job = _build_opa_job("opa_untimed", 1, start=45, finish=60)
        untimed_opa_job._finish = 0
        metrics = _build_metrics_without_sources(
            sim_jobs, [failed_opa_job, untimed_opa_job]
        )

        metrics._calculate_descriptive_throughput_metrics()

        assert metrics.mean_csypd_per_chunk == 0
        assert metrics.mean_cqsypd_per_chunk == 0

    def test_opa_metrics_are_zero_when_no_chunk_can_be_coupled(self):
        sim_jobs = [
            _build_sim_job("sim_1", 1, submit=5, start=10, finish=40, years_per_sim=0)
        ]
        opa_jobs = [_build_opa_job("opa_1", 1, start=45, finish=60)]
        metrics = _build_metrics_without_sources(sim_jobs, opa_jobs)

        metrics._calculate_descriptive_throughput_metrics()

        assert metrics.mean_csypd_per_chunk == 0
        assert metrics.mean_cqsypd_per_chunk == 0
        assert len(metrics.warnings) == 1

    def test_opa_finishing_before_the_sim_submit_only_reports_the_bottleneck(self):
        sim_jobs = [_build_sim_job("sim_1", 1, submit=100, start=110, finish=120)]
        opa_jobs = [_build_opa_job("opa_1", 1, start=50, finish=60)]
        metrics = _build_metrics_without_sources(sim_jobs, opa_jobs)

        metrics._calculate_descriptive_throughput_metrics()

        assert metrics.mean_csypd_per_chunk == pytest.approx(
            round((1 / 365.25) * 86400 / 10, 4)
        )
        assert metrics.mean_cqsypd_per_chunk == 0
        assert metrics.warnings == []


class TestMetricsInternals:
    def test_init_error_sets_error_state(self):
        metrics = PerformanceMetrics("unknown", SimpleNamespace())

        assert metrics.error is True
        assert metrics.error_message.startswith("Error while preparing data sources")
        assert metrics.to_json()["error"] is True

    def test_invalid_cf_and_pue_numbers_add_warnings(self):
        metrics = PerformanceMetrics.__new__(PerformanceMetrics)
        metrics.warnings = []
        metrics.sim_jobs_platform = ""
        metrics.sim_platform_CF = 0.0
        metrics.sim_platform_PUE = 0.0
        metrics.configuration_facade = SimpleNamespace(
            get_platorm_conf_footprint=lambda _: {
                "CF": "not-a-number",
                "PUE": "not-a-number",
            }
        )

        metrics._update_sim_jobs_platform("MN5")

        assert metrics.sim_jobs_platform == "MN5"
        assert len(metrics.warnings) == 2

    def test_outlier_jobs_add_a_warning(self):
        job = _build_sim_job("sim_1", 1, submit=5, start=10, finish=40)
        metrics = PerformanceMetrics.__new__(PerformanceMetrics)
        metrics.sim_jobs_valid = []
        metrics.warnings = []
        metrics.pkl_organizer = SimpleNamespace(
            get_completed_section_jobs=lambda _: [job]
        )
        metrics.joblist_helper = SimpleNamespace(job_to_package={})

        metrics._identify_outlier_jobs()

        assert len(metrics.warnings) == 1
        assert "runtime outlier" in metrics.warnings[0]

    def test_not_considered_jobs_are_serialized(self):
        metrics = PerformanceMetrics.__new__(PerformanceMetrics)
        metrics._considered = []
        metrics._not_considered = []
        metrics.sim_platform_CF = 0.0
        metrics.sim_platform_PUE = 0.0
        metrics.sim_jobs_valid = [_build_sim_job("sim_1", 1, 5, 10, 40)]
        metrics.sim_jobs_invalid = [_build_sim_job("sim_2", 2, 5, 10, 40)]

        metrics._populate_considered_jobs()

        assert len(metrics._considered) == 1
        assert len(metrics._not_considered) == 1


class TestRSYPDDivisor:
    def test_uses_earliest_start_and_latest_finish_regardless_of_order(self):
        metrics = PerformanceMetrics.__new__(PerformanceMetrics)
        metrics.sim_jobs_valid = [
            SimpleNamespace(start_ts=200),
            SimpleNamespace(start_ts=100),
        ]
        metrics.pkl_organizer = SimpleNamespace(
            get_completed_section_jobs=lambda _: [
                SimpleNamespace(finish_ts=400),
                SimpleNamespace(finish_ts=300),
            ]
        )

        assert metrics._get_RSYPD_divisor() == 300


class TestCalculateSYPDPerjob:
    CHUNK_UNIT = "month"
    CHUNK_SIZE = 4

    def test_no_splits_matches_baseline(self):
        result_no_split = calculate_SYPD_perjob(
            run_time=100,
            chunk_unit=self.CHUNK_UNIT,
            chunk_size=self.CHUNK_SIZE,
            job_chunk=1,
        )
        result_split_1 = calculate_SYPD_perjob(
            run_time=100,
            chunk_unit=self.CHUNK_UNIT,
            chunk_size=self.CHUNK_SIZE,
            job_chunk=1,
            splits=1,
        )
        assert result_no_split == result_split_1

    def test_splits_2_halves_sypd(self):
        base = calculate_SYPD_perjob(
            run_time=100,
            chunk_unit=self.CHUNK_UNIT,
            chunk_size=self.CHUNK_SIZE,
            job_chunk=1,
            splits=1,
        )
        split = calculate_SYPD_perjob(
            run_time=100,
            chunk_unit=self.CHUNK_UNIT,
            chunk_size=self.CHUNK_SIZE,
            job_chunk=1,
            splits=2,
        )
        assert split == pytest.approx(base / 2)

    @pytest.mark.parametrize("bad_splits", [0, -1, None, "abc", 0.5])
    def test_invalid_splits_falls_back_to_1(self, bad_splits):
        base = calculate_SYPD_perjob(
            run_time=100,
            chunk_unit=self.CHUNK_UNIT,
            chunk_size=self.CHUNK_SIZE,
            job_chunk=1,
            splits=1,
        )
        fallback = calculate_SYPD_perjob(
            run_time=100,
            chunk_unit=self.CHUNK_UNIT,
            chunk_size=self.CHUNK_SIZE,
            job_chunk=1,
            splits=bad_splits,
        )
        assert fallback == pytest.approx(base)

    def test_returns_none_for_non_completed_status(self):
        result = calculate_SYPD_perjob(
            run_time=100,
            chunk_unit=self.CHUNK_UNIT,
            chunk_size=self.CHUNK_SIZE,
            job_chunk=1,
            status=Status.RUNNING,
            splits=3,
        )
        assert result is None

    def test_returns_none_for_zero_run_time(self):
        result = calculate_SYPD_perjob(
            run_time=0,
            chunk_unit=self.CHUNK_UNIT,
            chunk_size=self.CHUNK_SIZE,
            job_chunk=1,
            splits=3,
        )
        assert result is None

    def test_returns_none_for_zero_chunk(self):
        result = calculate_SYPD_perjob(
            run_time=100,
            chunk_unit=self.CHUNK_UNIT,
            chunk_size=self.CHUNK_SIZE,
            job_chunk=0,
            splits=3,
        )
        assert result is None


class TestCalculateASYPDPerjob:
    CHUNK_UNIT = "month"
    CHUNK_SIZE = 4

    def test_splits_2_halves_asypd(self):
        base = calculate_ASYPD_perjob(
            queue_run_time=100,
            average_post=10.0,
            chunk_unit=self.CHUNK_UNIT,
            chunk_size=self.CHUNK_SIZE,
            job_chunk=1,
            splits=1,
        )
        split = calculate_ASYPD_perjob(
            queue_run_time=100,
            average_post=10.0,
            chunk_unit=self.CHUNK_UNIT,
            chunk_size=self.CHUNK_SIZE,
            job_chunk=1,
            splits=2,
        )
        assert split == pytest.approx(base / 2)

    @pytest.mark.parametrize("bad_splits", [0, -1, None, "abc"])
    def test_invalid_splits_falls_back_to_1(self, bad_splits):
        base = calculate_ASYPD_perjob(
            queue_run_time=100,
            average_post=5.0,
            chunk_unit=self.CHUNK_UNIT,
            chunk_size=self.CHUNK_SIZE,
            job_chunk=1,
            splits=1,
        )
        fallback = calculate_ASYPD_perjob(
            queue_run_time=100,
            average_post=5.0,
            chunk_unit=self.CHUNK_UNIT,
            chunk_size=self.CHUNK_SIZE,
            job_chunk=1,
            splits=bad_splits,
        )
        assert fallback == pytest.approx(base)

    def test_returns_none_when_divisor_zero(self):
        result = calculate_ASYPD_perjob(
            queue_run_time=0,
            average_post=0.0,
            chunk_unit=self.CHUNK_UNIT,
            chunk_size=self.CHUNK_SIZE,
            job_chunk=1,
            splits=2,
        )
        assert result is None
