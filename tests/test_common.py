from typing import List
import pytest
from autosubmit_api.common import utils
from autosubmit_api.components.jobs.job_factory import SimJob


@pytest.mark.parametrize(
    "valid_run_times, outlier_run_times, zeros",
    [
        ([2800, 3000, 2900], [4], 2),
        ([2900, 3000, 2950, 3100, 2930, 2890], [4, 5000], 0),
        ([2900, 3000, 2950, 3100, 2930, 2890], [4, 5000], 200),
        ([], [], 0),
        ([1], [], 0),
        ([1], [], 20),
    ],
)
def test_outlier_detection(
    valid_run_times: List[int], outlier_run_times: List[int], zeros: int
):
    """
    Test outlier detection method with different run times.

    :param valid_run_times: List of valid run times.
    :param outlier_run_times: List of outlier run times.
    :param zeros: Number of jobs with run time equal to 0.
    """

    zeros_run_times = [0] * zeros

    # Mock jobs with run times
    jobs = []
    for run_time in valid_run_times + outlier_run_times + zeros_run_times:
        aux_job = SimJob()
        aux_job._run_time = run_time
        jobs.append(aux_job)

    valid_jobs, outliers = utils.separate_job_outliers(jobs)

    assert len(valid_jobs) == len(valid_run_times)
    assert len(outliers) == (len(outlier_run_times) + zeros)
