import os

from autosubmit_api.config.basicConfig import APIBasicConfig


class TestFixtures:
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

    def test_mock_basic_config(self, fixture_mock_basic_config: str, fixture_gen_rc_sqlite: str):
        rc_file = os.path.join(fixture_gen_rc_sqlite, ".autosubmitrc")
        # Environment variable should be set and should point to the .autosubmitrc file
        assert 'AUTOSUBMIT_CONFIGURATION' in os.environ and os.path.exists(os.environ['AUTOSUBMIT_CONFIGURATION'])
        assert os.environ['AUTOSUBMIT_CONFIGURATION'] == rc_file

        # Reading the configuration file
        APIBasicConfig.read()
        assert APIBasicConfig.GRAPHDATA_DIR == f"{fixture_gen_rc_sqlite}/metadata/graph"
        assert APIBasicConfig.LOCAL_ROOT_DIR == fixture_gen_rc_sqlite
        assert APIBasicConfig.DATABASE_BACKEND == "sqlite"
        assert APIBasicConfig.DB_DIR == fixture_gen_rc_sqlite
        assert APIBasicConfig.DB_FILE == "autosubmit.db"

    def test_fixture_temp_dir_copy_exclude_db(
        self, fixture_temp_dir_copy_exclude_db: str
    ):
        """
        Test if all the files are copied from FAKEDIR to the temporary directory except .db files
        """
        FILES_SHOULD_EXIST = [
            "a003/conf/minimal.yml",
        ]
        FILES_SHOULD_EXCLUDED = ["metadata/data/job_data_a007.db"]
        for file in FILES_SHOULD_EXIST:
            assert os.path.exists(os.path.join(fixture_temp_dir_copy_exclude_db, file))

        for file in FILES_SHOULD_EXCLUDED:
            assert not os.path.exists(
                os.path.join(fixture_temp_dir_copy_exclude_db, file)
            )
