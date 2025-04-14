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
                "WSYPD": 0,
                "IWSYPD": 0,
                "processing_elements": 16,
                "sim_processors": 16,
                "post_jobs_total_time_average": 0.0,
                "total_energy": 0.0,
                "total_footprint": 0.0,
                "sim_jobs_platform": 'MN4',
                "sim_jobs_platform_PUE": 1.35,
                "sim_jobs_platform_CF": 357000,
                "total_core_hours": 0.0,
                "ideal_critical_path": [],
                "phases": {'pre_sim_run_time': 0.0, 'sim_run_time': 0.0, 'post_sim_run_time': 0.0, 'total_run_time': 0.0, 'total_run_queue_time': 0.0},
                
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
                "WSYPD": 18.7826,
                "IWSYPD": 18.8399,
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
                "ideal_critical_path": [{'name': 'a3tb_REMOTE_SETUP', 'run_time': 2293, 'queue_time': 7, 'section': 'REMOTE_SETUP'}],
                "phases": {'pre_sim_run_time': 0.0, 'sim_run_time': 0.0, 'post_sim_run_time': 2293.0, 'total_run_time': 2293.0, 'total_run_queue_time': 2300.0},
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
                "WSYPD": 1440,
                "IWSYPD": 1440.0,
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
                "ideal_critical_path": 
                                [
                                    {'name': 'a007_LOCAL_SETUP', 'run_time': 5, 'queue_time': 0, 'section': 'LOCAL_SETUP'}, 
                                    {'name': 'a007_REMOTE_SETUP', 'run_time': 5, 'queue_time': 0, 'section': 'REMOTE_SETUP'}, 
                                    {'name': 'a007_20000101_fc0_INI', 'run_time': 5, 'queue_time': 0, 'section': 'INI'}, 
                                    {'name': 'a007_20000101_fc0_1_SIM', 'run_time': 5, 'queue_time': 0, 'section': 'SIM'}, 
                                    {'name': 'a007_20000101_fc0_2_SIM', 'run_time': 5, 'queue_time': 0, 'section': 'SIM'}, 
                                    {'name': 'a007_POST', 'run_time': 5, 'queue_time': 0, 'section': 'POST'}, 
                                    {'name': 'a007_CLEAN', 'run_time': 5, 'queue_time': 0, 'section': 'CLEAN'}, 
                                    {'name': 'a007_20000101_fc0_TRANSFER', 'run_time': 5, 'queue_time': 0, 'section': 'TRANSFER'}
                                ],
                "phases": {'pre_sim_run_time': 15.0, 'sim_run_time': 10.0, 'post_sim_run_time': 15.0, 'total_run_time': 40.0, 'total_run_queue_time': 40.0},
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
                "WSYPD": 0.5086,
                "IWSYPD": 0.5505,
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
                "ideal_critical_path": 
                            [
                                {'name': 'a8qc_LOCAL_SETUP', 'run_time': 0, 'queue_time': 0, 'section': 'LOCAL_SETUP'}, 
                                {'name': 'a8qc_LOCAL_SEND_SOURCE', 'run_time': 241, 'queue_time': 0, 'section': 'LOCAL_SEND_SOURCE'}, 
                                {'name': 'a8qc_REMOTE_COMPILE', 'run_time': 998, 'queue_time': 173, 'section': 'REMOTE_COMPILE'}, 
                                {'name': 'a8qc_PREPROCFIX', 'run_time': 390, 'queue_time': 40, 'section': 'PREPROCFIX'}, 
                                {'name': 'a8qc_20220630_HERMES_GR_PREPROC', 'run_time': 26, 'queue_time': 5, 'section': 'HERMES_GR_PREPROC'}, 
                                {'name': 'a8qc_20220630_1_HERMES_GR', 'run_time': 220, 'queue_time': 12, 'section': 'HERMES_GR'}, 
                                {'name': 'a8qc_20220630_003_1_PERTURB_HERMES', 'run_time': 43, 'queue_time': 0, 'section': 'PERTURB_HERMES'}, 
                                {'name': 'a8qc_20220630_003_1_SIM', 'run_time': 655, 'queue_time': 17, 'section': 'SIM'}, 
                                {'name': 'a8qc_20220630_003_1_DA_PREPROC', 'run_time': 314, 'queue_time': 1, 'section': 'DA_PREPROC'}, 
                                {'name': 'a8qc_20220630_003_1_ARCHIVE', 'run_time': 121, 'queue_time': 0, 'section': 'ARCHIVE'}, 
                                {'name': 'a8qc_20220630_003_1_CLEAN', 'run_time': 2, 'queue_time': 0, 'section': 'CLEAN'}
                            ],
                "phases": {'pre_sim_run_time': 1918.0, 'sim_run_time': 655.0, 'post_sim_run_time': 437.0, 'total_run_time': 3010.0, 'total_run_queue_time': 3258.0},
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
        "WSYPD": performance_metrics.WSYPD,
        "IWSYPD": performance_metrics.IWSYPD,
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
        "ideal_critical_path": performance_metrics.ideal_critical_path,
        "phases": performance_metrics.phases,
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


from autosubmit_api.persistance.pkl_reader import PklReader #Avoid errors with Pklreader when using dummy

_original_parse_job_list = PklReader.parse_job_list
def _patched_parse_job_list(self):
    if self.expid == "dummy":
        return []  # return empty list for dummy expid
    return _original_parse_job_list(self)
PklReader.parse_job_list = _patched_parse_job_list

def test_performance_metrics_find_ideal_critical_path_gen_empty():
    from autosubmit_api.components.experiment.pkl_organizer import PklOrganizer
    organizer = PklOrganizer("dummy")
    result = organizer.find_ideal_critical_path_gen({})
    assert result == []

def test_performance_metrics_find_ideal_critical_path_gen_simple_chain():
    from autosubmit_api.components.experiment.pkl_organizer import PklOrganizer
    organizer = PklOrganizer("dummy")
    jobs_dict = {
        "A": {"run_time": 5, "queue_time": 1, "children_names": {"B"}, "section": "SIM"},
        "B": {"run_time": 10, "queue_time": 2, "children_names": {"C"}, "section": "SIM"},
        "C": {"run_time": 15, "queue_time": 3, "children_names": set(), "section": "SIM"},
    }
    result = organizer.find_ideal_critical_path_gen(jobs_dict)
    expected = [
        {"name": "A", "run_time": 5, "queue_time": 1, "section": "SIM"},
        {"name": "B", "run_time": 10, "queue_time": 2, "section": "SIM"},
        {"name": "C", "run_time": 15, "queue_time": 3, "section": "SIM"},
    ]
    assert result == expected

def test_performance_metrics_find_ideal_critical_path_gen_branching():
    from autosubmit_api.components.experiment.pkl_organizer import PklOrganizer
    organizer = PklOrganizer("dummy")
    jobs_dict = {
        "A": {"run_time": 5, "queue_time": 0, "children_names": {"B", "C"}, "section": "SIM"},
        "B": {"run_time": 5, "queue_time": 0, "children_names": {"D"}, "section": "SIM"},
        "C": {"run_time": 10, "queue_time": 0, "children_names": set(), "section": "SIM"},
        "D": {"run_time": 20, "queue_time": 0, "children_names": set(), "section": "SIM"},
    }
    result = organizer.find_ideal_critical_path_gen(jobs_dict)
    expected = [
        {"name": "A", "run_time": 5, "queue_time": 0, "section": "SIM"},
        {"name": "B", "run_time": 5, "queue_time": 0, "section": "SIM"},
        {"name": "D", "run_time": 20, "queue_time": 0, "section": "SIM"},
    ]
    assert result == expected

def test_performance_metrics_find_ideal_critical_path_gen_zero_run_time():
    from autosubmit_api.components.experiment.pkl_organizer import PklOrganizer
    organizer = PklOrganizer("dummy")
    jobs_dict = {
        "X": {"run_time": 0, "queue_time": 0, "children_names": {"Y"}, "section": "SIM"},
        "Y": {"run_time": 0, "queue_time": 0, "children_names": set(), "section": "SIM"},
    }
    result = organizer.find_ideal_critical_path_gen(jobs_dict)
    expected = [
        {"name": "X", "run_time": 0, "queue_time": 0, "section": "SIM"},
        {"name": "Y", "run_time": 0, "queue_time": 0, "section": "SIM"},
    ]
    assert result == expected
