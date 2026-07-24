from typing import Optional

from autosubmit_api.common.utils import Status

from autosubmit_api.estimation.eta import (
    _compute_chunk_runtime_seconds,
    calculate_eta,
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
    
    def test_unknown_str_not_completed(self):
        """Test that an unknown string status is not completed."""
        job = MockJob()
        job.status_code = Status.UNKNOWN
        job.status = "UNKNOWN_STATUS"
        assert is_job_completed(job) is False
    
    def test_running_str_not_completed(self):
        """Test that a running string status is not completed."""
        job = MockJob()
        job.status_code = Status.RUNNING
        job.status = "RUNNING"
        assert is_job_completed(job) is False


class TestComputeChunkRuntimeSeconds:
    def test_single_job(self):
        """Test that a single job returns the diff between finish and start."""
        jobs = [MockJob(chunk=1,start=1000, finish=2000)]
        assert _compute_chunk_runtime_seconds(jobs) == 1000.0
    
    def test_multiple_jobs(self):
        """Test that multiple jobs return the correct runtime for the chunk."""
        jobs = [
            MockJob(chunk=1, start=1000, finish=2000),
            MockJob(chunk=1, start=1500, finish=2500),
            MockJob(chunk=1, start=1200, finish=2200),
        ]
        assert _compute_chunk_runtime_seconds(jobs) == 1500.0
    

    def test_missing_start(self):
        """Test that jobs with missing start or finish return None."""
        jobs = [
            MockJob(chunk=1, start=None, finish=2000),
        ]
        assert _compute_chunk_runtime_seconds(jobs) is None
    
    def test_missing_finish(self):
        """Test that jobs with missing start or finish return None."""
        jobs = [
            MockJob(chunk=1, start=1000, finish=None),
        ]
        assert _compute_chunk_runtime_seconds(jobs) is None
    
    def test_finish_before_start(self):
        """Test that jobs with finish before start return None."""
        jobs = [
            MockJob(chunk=1, start=2000, finish=1000),
        ]
        assert _compute_chunk_runtime_seconds(jobs) is None
    
    def test_all_missing(self):
        """Test that jobs with all missing timestamps return None."""
        jobs = [
            MockJob(chunk=1, start=None, finish=None),
        ]
        assert _compute_chunk_runtime_seconds(jobs) is None
    
    def test_empty_list(self):
        """Test that an empty job list returns None."""
        assert _compute_chunk_runtime_seconds([]) is None
    
    def test_finish_equals_start(self):
        """Test that finish == start returns 0."""
        jobs = [
            MockJob(chunk=1, start=1000, finish=1000),
        ]
        assert _compute_chunk_runtime_seconds(jobs) == 0.0


class TestCalculateEta:
    def test_calculate_eta_all_completed(self):
        """Test that eta_seconds is 0 when all chunks completed."""
        jobs = [
            MockJob(chunk=1, start=1000, finish=2000, status=Status.COMPLETED),
            MockJob(chunk=2, start=2000, finish=3000, status=Status.COMPLETED),
        ]
        eta_dict = calculate_eta(jobs)
        assert eta_dict["eta_seconds"] == 0.0
        assert eta_dict["chunks_total"] == 2
        assert eta_dict["chunks_remaining"] == 0
        assert eta_dict["avg_runtime_per_chunk_seconds"] == 1000.0
    
    def test_calculate_eta_some_remaining(self):
        """Test that eta_seconds calculated correctly when some chunks not completed."""
        jobs = [
            MockJob(chunk=1, start=1000, finish=2000, status=Status.COMPLETED),
            MockJob(chunk=2, start=2000, finish=None, status=Status.RUNNING),
            MockJob(chunk=3, start=None, finish=None, status=Status.WAITING),
        ]
        eta_dict = calculate_eta(jobs)
        assert eta_dict["eta_seconds"] == 2000.0
        assert eta_dict["chunks_total"] == 3
        assert eta_dict["chunks_remaining"] == 2
        assert eta_dict["avg_runtime_per_chunk_seconds"] == 1000.0
    
    def test_calculate_eta_no_completed_chunks(self):
        """Test that eta_seconds is None when no chunks completed."""
        jobs = [
            MockJob(chunk=1, start=None, finish=None, status=Status.RUNNING),
            MockJob(chunk=2, start=None, finish=None, status=Status.WAITING),
        ]
        eta_dict = calculate_eta(jobs)
        assert eta_dict["eta_seconds"] is None
        assert eta_dict["chunks_total"] == 2
        assert eta_dict["chunks_remaining"] == 2
        assert eta_dict["avg_runtime_per_chunk_seconds"] is None
    
    def test_calculate_eta_empty_input(self):
        """Test that empty input returns empty response."""
        eta_dict = calculate_eta([])
        assert eta_dict["eta_seconds"] is None
        assert eta_dict["chunks_total"] is None
        assert eta_dict["chunks_remaining"] is None
        assert eta_dict["avg_runtime_per_chunk_seconds"] is None
    
    def test_calculate_eta_all_no_chunk(self):
        """Test that jobs without chunks return empty response."""
        jobs = [
            MockJob(chunk=None, status=Status.COMPLETED),
            MockJob(chunk=None, status=Status.RUNNING),
        ]
        eta_dict = calculate_eta(jobs)
        assert eta_dict["eta_seconds"] is None
        assert eta_dict["chunks_total"] is None
        assert eta_dict["chunks_remaining"] is None
        assert eta_dict["avg_runtime_per_chunk_seconds"] is None
    
    def test_calculate_eta_single_chunk_completed(self):
        """Test that a single completed chunk returns eta=0."""
        jobs = [
            MockJob(chunk=1, start=1000, finish=2000, status=Status.COMPLETED),
        ]
        eta_dict = calculate_eta(jobs)
        assert eta_dict["eta_seconds"] == 0.0
        assert eta_dict["chunks_total"] == 1
        assert eta_dict["chunks_remaining"] == 0
        assert eta_dict["avg_runtime_per_chunk_seconds"] == 1000.0
