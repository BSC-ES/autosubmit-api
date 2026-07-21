from typing import Optional

from autosubmit_api.common.utils import Status

from autosubmit_api.components.eta.strategies import (
    _get_status_code,
    compute_chunk_runtime_seconds,
    group_jobs_by_chunk,
    is_job_completed,
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


# Helpers

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


class TestIsJobCompleted:
    def test_completed_int(self):
        """Test that a job with a completed integer status is completed."""
        assert is_job_completed(MockJob(status=Status.COMPLETED)) is True
    
    def test_running_int(self):
        """Test that a job with a running integer status is not completed."""
        assert is_job_completed(MockJob(status=Status.RUNNING)) is False
    
    def test_completed_str(self):
        """Test that a job with a completed string status is completed."""
        job = MockJob()
        job.status_code = Status.COMPLETED
        job.status = "COMPLETED"
        assert is_job_completed(job) is True


class TestGroupJobsByChunk:
    def test_excludes_none(self):
        """Test that jobs with None chunk are excluded from the grouping."""
        jobs = [
            MockJob(chunk=1),
            MockJob(chunk=2),
            MockJob(chunk=None),
            MockJob(chunk=1),
        ]
        grouped = group_jobs_by_chunk(jobs)
        assert list(grouped.keys()) == [1, 2]
    

    def test_groups_correctly(self):
        """Test that jobs are grouped correctly by their chunk."""
        jobs = [
            MockJob(chunk=1),
            MockJob(chunk=2),
            MockJob(chunk=1),
            MockJob(chunk=3),
            MockJob(chunk=2),
        ]
        grouped = group_jobs_by_chunk(jobs)
        assert len(grouped[1]) == 2
        assert len(grouped[2]) == 2
        assert len(grouped[3]) == 1
    
    def test_empty_list(self):
        """Test that an empty job list returns an empty grouping."""
        assert group_jobs_by_chunk([]) == {}


class TestComputeChunkRuntimeSeconds:
    def test_single_job(self):
        """Test that a single job returns the diff between finish and start."""
        jobs = [MockJob(chunk=1,start=1000, finish=2000)]
        assert compute_chunk_runtime_seconds(jobs) == 1000.0
    
    def test_multiple_jobs(self):
        """Test that multiple jobs return the correct runtime for the chunk."""
        jobs = [
            MockJob(chunk=1, start=1000, finish=2000),
            MockJob(chunk=1, start=1500, finish=2500),
            MockJob(chunk=1, start=1200, finish=2200),
        ]
        assert compute_chunk_runtime_seconds(jobs) == 1500.0
    

    def test_missing_start(self):
        """Test that jobs with missing start or finish return None."""
        jobs = [
            MockJob(chunk=1, start=None, finish=2000),
        ]
        assert compute_chunk_runtime_seconds(jobs) is None
    
    def test_missing_finish(self):
        """Test that jobs with missing start or finish return None."""
        jobs = [
            MockJob(chunk=1, start=1000, finish=None),
        ]
        assert compute_chunk_runtime_seconds(jobs) is None
    
    def test_finish_before_start(self):
        """Test that jobs with finish before start return None."""
        jobs = [
            MockJob(chunk=1, start=2000, finish=1000),
        ]
        assert compute_chunk_runtime_seconds(jobs) is None
    
    def test_all_missing(self):
        """Test that jobs with all missing timestamps return None."""
        jobs = [
            MockJob(chunk=1, start=None, finish=None),
        ]
        assert compute_chunk_runtime_seconds(jobs) is None
    
    def test_empty_list(self):
        """Test that an empty job list returns None."""
        assert compute_chunk_runtime_seconds([]) is None
     