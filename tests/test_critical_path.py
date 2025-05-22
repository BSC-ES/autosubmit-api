from typing import Dict, List
import pytest

from autosubmit_api.performance.utils import find_critical_path

@pytest.mark.parametrize(
    "input, expected",
    [
        # No jobs in the dictionary
        (
            {}, []
        ),

        # Simple chain of jobs
        (
            {
                "A": {"run_time": 5, "queue_time": 1, "children_names": {"B"}, "section": "SIM"},
                "B": {"run_time": 10, "queue_time": 2, "children_names": {"C"}, "section": "SIM"},
                "C": {"run_time": 15, "queue_time": 3, "children_names": set(), "section": "SIM"},
            },
            [
                {"name": "A", "run_time": 5, "queue_time": 1, "section": "SIM"},
                {"name": "B", "run_time": 10, "queue_time": 2, "section": "SIM"},
                {"name": "C", "run_time": 15, "queue_time": 3, "section": "SIM"},
            ]
        ),
        # Branching jobs
        (
            {
                "A": {"run_time": 5, "queue_time": 0, "children_names": {"B", "C"}, "section": "SIM"},
                "B": {"run_time": 5, "queue_time": 0, "children_names": {"D"}, "section": "SIM"},
                "C": {"run_time": 10, "queue_time": 0, "children_names": set(), "section": "SIM"},
                "D": {"run_time": 20, "queue_time": 0, "children_names": set(), "section": "SIM"},
            },
            [
                {"name": "A", "run_time": 5, "queue_time": 0, "section": "SIM"},
                {"name": "B", "run_time": 5, "queue_time": 0, "section": "SIM"},
                {"name": "D", "run_time": 20, "queue_time": 0, "section": "SIM"},
            ]
        ),
        # Merging jobs
        (
            {
                "A": {"run_time": 5, "queue_time": 0, "children_names": {"B" , "C"}, "section": "SIM"},
                "B": {"run_time": 10, "queue_time": 0, "children_names": {"D" , "E"}, "section": "SIM"},
                "C": {"run_time": 15, "queue_time": 0, "children_names": {"D"}, "section": "SIM"},
                "D": {"run_time": 20, "queue_time": 0, "children_names": set(), "section": "SIM"},
                "E": {"run_time": 20, "queue_time": 0, "children_names": set(), "section": "SIM"},
            },
            [
                {"name": "A", "run_time": 5, "queue_time": 0, "section": "SIM"},
                {"name": "C", "run_time": 15, "queue_time": 0, "section": "SIM"},
                {"name": "D", "run_time": 20, "queue_time": 0, "section": "SIM"},
            ]
        ),
        # Jobs with zero run time
        (
            {
                "X": {"run_time": 0, "queue_time": 0, "children_names": {"Y"}, "section": "SIM"},
                "Y": {"run_time": 0, "queue_time": 0, "children_names": set(), "section": "SIM"},
            },
            [
                {"name": "X", "run_time": 0, "queue_time": 0, "section": "SIM"},
                {"name": "Y", "run_time": 0, "queue_time": 0, "section": "SIM"},
            ]
        ),
        #Jobs with negative run time
        (
            {
                "X": {"run_time": -5, "queue_time": 0, "children_names": {"Y"}, "section": "SIM"},
                "Y": {"run_time": -10, "queue_time": 0, "children_names": set(), "section": "SIM"},
            },
            [
                {"name": "X", "run_time": -5, "queue_time": 0, "section": "SIM"},
                {"name": "Y", "run_time": -10, "queue_time": 0, "section": "SIM"},
            ]
        ),
        # Jobs with queue time 
        (
            {
                "A": {"run_time": 5, "queue_time": 0, "children_names": {"B", "C"}, "section": "SIM"},
                "B": {"run_time": 5, "queue_time": 0, "children_names": {"D"}, "section": "SIM"},
                "C": {"run_time": 10, "queue_time": 1000, "children_names": set(), "section": "SIM"},
                "D": {"run_time": 20, "queue_time": 20, "children_names": set(), "section": "SIM"},
            },
            [
                {"name": "A", "run_time": 5, "queue_time": 0, "section": "SIM"},
                {"name": "B", "run_time": 5, "queue_time": 0, "section": "SIM"},
                {"name": "D", "run_time": 20, "queue_time": 20, "section": "SIM"},
            ]

        ),

    ]
)

def test_critical_path(input: Dict[str, dict], expected: List[dict]):
    result = find_critical_path(input)
    assert expected == result