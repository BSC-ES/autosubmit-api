from typing import Optional

from autosubmit_api.common.utils import Status

from autosubmit_api.components.eta.strategies import (
    _get_status_code,
)


class MockJob:
    """Mock job object with the attributes needed for testing the ETA."""

    def __init__(
        self,
        chunk: Optional[int] = None,
        status: int = Status.UNKNOWN,
        start: int = 0,
        finish: int = 0,
        section: str = "SIM",
    ):
        self.chunk = chunk
        self.status = status
        self.start = start
        self.finish = finish
        self.section = section


# Helpers from strategies.py

class TestGetStatusCode:
    def test_int_status_completed(self):
        """Test that an integer status is returned as-is."""
        job = MockJob(status=Status.COMPLETED)
        assert _get_status_code(job) == Status.COMPLETED

    def test_str_status_conversion(self):
        """Test that a string status is converted to the correct integer code."""
        job = MockJob()
        job.status_code = Status.RUNNING
        job.status = "RUNNING"
        assert _get_status_code(job) == Status.RUNNING
    
    def test_unk_str_defaults(self):
        """Test that an unknown string status defaults to Status.UNKNOWN."""
        job = MockJob()
        job.status_code = Status.UNKNOWN
        job.status = "UNKNOWN_STATUS"
        assert _get_status_code(job) == Status.UNKNOWN
