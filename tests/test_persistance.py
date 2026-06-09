import pytest

from autosubmit_api.persistance.job_package_reader import JobPackageReader
from autosubmit_api.repositories.jobs import create_jobs_repository


class TestPklReader:
    @pytest.mark.parametrize(
        "expid, size",
        [("a003", 8), ("a007", 8), ("a3tb", 55), ("a1ve", 8), ("a1vj", 8)],
    )
    def test_reader(self, fixture_mock_basic_config, expid, size):
        job_list_repo = create_jobs_repository(expid)
        content = job_list_repo.get_all()
        assert len(content) == size
        for item in content:
            assert item.name.startswith(expid)


class TestPackageReader:
    @pytest.mark.parametrize(
        "expid, size",
        [("a6zj", 4), ("a003", 0), ("aa6f", 8)],
    )
    def test_reader(self, fixture_mock_basic_config, expid: str, size: int):
        reader = JobPackageReader(expid).read()
        content = reader._content
        assert len(content) == size
        for item in content:
            job_name = item.get("job_name")
            assert isinstance(job_name, str)
            assert job_name.startswith(expid)
