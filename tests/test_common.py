from typing import List, Union
from unittest.mock import patch
import pytest
from autosubmit_api.common import utils
from autosubmit_api.components.jobs.job_factory import SimJob
from autosubmit_api.common.utils import timestamp_to_datetime_format
from zoneinfo import ZoneInfo


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


@pytest.mark.parametrize(
    "timestamp, expected, timezone",
    [
        (1633072800, "2021-10-01T07:20:00+00:00", "UTC"),  # Valid timestamp
        (0, None, "UTC"),  # Invalid timestamp (0)
        (-1, None, "UTC"),  # Invalid timestamp (negative)
        (None, None, "UTC"),  # None timestamp
        (1633072800.0, "2021-10-01T07:20:00+00:00", "UTC"),  # Valid timestamp as float
        (1736208000, "2025-01-07T00:00:00+00:00", "UTC"),
        (1633072800, "2021-10-01T02:20:00-05:00", "America/Lima"),  # Other timezone
        (1633072800, "2021-10-01T05:20:00-02:00", "Etc/GMT+2"),
    ],
)
def test_timestamp_to_datetime_format(
    timestamp: int, expected: Union[str, None], timezone: str
):
    mock_tzinfo = ZoneInfo(timezone)
    with patch("autosubmit_api.common.utils.get_local_tz", return_value=mock_tzinfo):
        assert timestamp_to_datetime_format(timestamp) == expected
