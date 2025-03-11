from autosubmit_api.persistance.pkl_reader import PklReader
import pytest


class TestPklReader:
    @pytest.mark.parametrize(
        "expid, size", [("a003", 8), ("a007", 8), ("a3tb", 55), ("a1ve", 8), ("a1vj", 8)]
    )
    def test_reader(self, fixture_mock_basic_config, expid, size):
        content = PklReader(expid).parse_job_list()
        assert len(content) == size
        for item in content:
            assert item.name.startswith(expid)
