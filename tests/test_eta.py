from typing import Optional

from autosubmit_api.common.utils import Status

from autosubmit_api.components.eta.calculator import (
    calculate_eta,
    get_chunks_info
)

from autosubmit_api.components.eta.strategies import (
    AvgByDirectTimeStrategy,
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
     

# Strategy

class TestAvgByDirectTimeStrategy:
    def test_calculate_avg_completed_chunks(self):
        """Test that the average runtime is averaged for completed chunks."""
        jobs = [
            MockJob(chunk=1, start=1000, finish=1010, status=Status.COMPLETED),
            MockJob(chunk=1, start=1500, finish=1505, status=Status.COMPLETED),
            MockJob(chunk=2, start=2000, finish=3000, status=Status.COMPLETED),
            MockJob(chunk=2, start=2500, finish=3500, status=Status.COMPLETED),
            MockJob(chunk=3, start=3000, finish=4000, status=Status.COMPLETED),
        ]
        strategy = AvgByDirectTimeStrategy()
        avg_runtime = strategy.calculate(jobs, chunk_unit="unit", chunk_size=1)
        assert avg_runtime == round(((4000-3000) + (3500-2000) + (1505 - 1000)) / 3, 4)
    
    def test_calculate_skips_incomplete_chunks(self):
        """Test that incomplete chunks are skipped in the average calculation."""
        jobs = [
            MockJob(chunk=1, start=1000, finish=1003, status=Status.COMPLETED),
            MockJob(chunk=1, start=1500, finish=2500, status=Status.COMPLETED),
            MockJob(chunk=2, start=2000, finish=None, status=Status.RUNNING),
            MockJob(chunk=2, start=2500, finish=None, status=Status.WAITING),
        ]
        strategy = AvgByDirectTimeStrategy()
        avg_runtime = strategy.calculate(jobs, chunk_unit="unit", chunk_size=1)
        assert avg_runtime == 1500.0  # Only chunk 1 is completed
    
    def test_calculate_no_completed_chunks(self):
        """Test that None is returned when there are no completed chunks."""
        jobs = [
            MockJob(chunk=1, start=1000, finish=None, status=Status.RUNNING),
            MockJob(chunk=2, start=2000, finish=None, status=Status.WAITING),
        ]
        strategy = AvgByDirectTimeStrategy()
        avg_runtime = strategy.calculate(jobs, chunk_unit="unit", chunk_size=1)
        assert avg_runtime is None
    
    def test_calculate_job_list_empty(self):
        """Test that None is returned when the job list is empty."""
        strategy = AvgByDirectTimeStrategy()
        avg_runtime = strategy.calculate([], chunk_unit="unit", chunk_size=1)
        assert avg_runtime is None
    
    def test_calculate_single_job(self):
        """Test that a single completed job returns its runtime."""
        jobs = [
            MockJob(chunk=1, start=1000, finish=1005, status=Status.COMPLETED),
        ]
        strategy = AvgByDirectTimeStrategy()
        avg_runtime = strategy.calculate(jobs, chunk_unit="unit", chunk_size=1)
        assert avg_runtime == 5.0
    

# calculator.py

class TestGetChunksInfo:
    def test_get_chunks_info_all(self):
        """Test that the total and completed chunk counts are correct."""
        jobs = [
            MockJob(chunk=1, status=Status.COMPLETED),
            MockJob(chunk=1, status=Status.COMPLETED),
            MockJob(chunk=2, status=Status.RUNNING),
            MockJob(chunk=2, status=Status.COMPLETED),
            MockJob(chunk=3, status=Status.WAITING),
            MockJob(chunk=4, status=Status.COMPLETED),
            MockJob(chunk=None, status=Status.COMPLETED),
        ]
        total_chunks, completed_chunks_count = get_chunks_info(jobs)
        assert total_chunks == 4
        assert completed_chunks_count == 2
    
    def test_empty(self):
        """Test that an empty job list returns None for both counts."""
        total_chunks, completed_chunks_count = get_chunks_info([])
        assert total_chunks is None
        assert completed_chunks_count is None
    
    def test_none(self):
        """Test that jobs with None chunk are ignored in the counts."""
        jobs = [
            MockJob(chunk=None, status=Status.COMPLETED),
            MockJob(chunk=None, status=Status.RUNNING),
        ]
        total_chunks, completed_chunks_count = get_chunks_info(jobs)
        assert total_chunks is None
        assert completed_chunks_count is None
    
    def test_string_status(self):
        """Test that string statuses are correctly interpreted."""
        jobs = [
            MockJob(chunk=1, status=Status.COMPLETED),
            MockJob(chunk=2, status=Status.RUNNING),
        ]
        jobs[0].status = "COMPLETED"
        jobs[0].status_code = Status.COMPLETED
        jobs[1].status = "RUNNING"
        jobs[1].status_code = Status.RUNNING
        total_chunks, completed_chunks_count = get_chunks_info(jobs)
        assert total_chunks == 2
        assert completed_chunks_count == 1


class TestCalculateEta:
    def test_calculate_eta_all_completed(self):
        """Test that eta_seconds is 0 when all chunks are completed."""
        jobs = [
            MockJob(chunk=1, start=1000, finish=2000, status=Status.COMPLETED),
            MockJob(chunk=2, start=2000, finish=3000, status=Status.COMPLETED),
        ]
        strategy = AvgByDirectTimeStrategy()
        eta_dict = calculate_eta(jobs, "unit", 1, strategy)
        assert eta_dict["eta_seconds"] == 0.0
        assert eta_dict["chunks_total"] == 2
        assert eta_dict["chunks_remaining"] == 0
        assert eta_dict["avg_runtime_per_chunk_seconds"] == 1000.0
    
    def test_calculate_eta_some_remaining(self):
        """Test that eta_seconds is calculated correctly when some chunks remain."""
        jobs = [
            MockJob(chunk=1, start=1000, finish=2000, status=Status.COMPLETED),
            MockJob(chunk=2, start=2000, finish=None, status=Status.RUNNING),
            MockJob(chunk=3, start=None, finish=None, status=Status.WAITING),
        ]
        strategy = AvgByDirectTimeStrategy()
        eta_dict = calculate_eta(jobs, "unit", 1, strategy)
        assert eta_dict["eta_seconds"] == 2000.0
        assert eta_dict["chunks_total"] == 3
        assert eta_dict["chunks_remaining"] == 2
        assert eta_dict["avg_runtime_per_chunk_seconds"] == 1000.0
    
    def test_calculate_eta_no_completed_chunks(self):
        """Test that eta_seconds is None when no chunks are completed."""
        jobs = [
            MockJob(chunk=1, start=None, finish=None, status=Status.RUNNING),
            MockJob(chunk=2, start=None, finish=None, status=Status.WAITING),
        ]
        strategy = AvgByDirectTimeStrategy()
        eta_dict = calculate_eta(jobs, "unit", 1, strategy)
        assert eta_dict["eta_seconds"] is None
        assert eta_dict["chunks_total"] == 2
        assert eta_dict["chunks_remaining"] == 2
        assert eta_dict["avg_runtime_per_chunk_seconds"] is None

