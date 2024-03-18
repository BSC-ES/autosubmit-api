from autosubmit_api.persistance.pkl_reader import PklReader


class TestPklReader:

    def test_reader(self, fixture_mock_basic_config):
        test_cases = [
            {"expid": "a003", "size": 8},
            {"expid": "a007", "size": 8},
            {"expid": "a3tb", "size": 55},
        ]

        for exp in test_cases:
            content = PklReader(exp["expid"]).parse_job_list()
            assert len(content) == exp["size"]
            for item in content:
                assert item.name.startswith(exp["expid"])
