import os


class TestSQLiteFixtures:
    def test_fixture_temp_dir_copy(self, fixture_temp_dir_copy: str):
        """
        Test if all the files are copied from FAKEDIR to the temporary directory
        """
        FILES_SHOULD_EXIST = [
            "a003/conf/minimal.yml",
            "metadata/data/job_data_a007.db",
        ]
        for file in FILES_SHOULD_EXIST:
            assert os.path.exists(os.path.join(fixture_temp_dir_copy, file))

    def test_fixture_gen_rc_sqlite(self, fixture_gen_rc_sqlite: str):
        """
        Test if the .autosubmitrc file is generated and the environment variable is set
        """
        rc_file = os.path.join(fixture_gen_rc_sqlite, ".autosubmitrc")

        # File should exist
        assert os.path.exists(rc_file)

        with open(rc_file, "r") as f:
            content = f.read()
            assert "[database]" in content
            assert f"path = {fixture_gen_rc_sqlite}" in content
            assert "filename = autosubmit.db" in content
            assert "backend = sqlite" in content
