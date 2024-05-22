import os
from typing import Tuple

import pytest
from sqlalchemy import Engine, select

from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.database import tables
from tests.utils import get_schema_names


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

    @pytest.mark.skip(reason="TODO: Fix this test")
    def test_mock_basic_config(
        self, fixture_mock_basic_config: APIBasicConfig, fixture_gen_rc_sqlite: str
    ):
        rc_file = os.path.join(fixture_gen_rc_sqlite, ".autosubmitrc")
        # Environment variable should be set and should point to the .autosubmitrc file
        assert "AUTOSUBMIT_CONFIGURATION" in os.environ and os.path.exists(
            os.environ["AUTOSUBMIT_CONFIGURATION"]
        )
        assert os.environ["AUTOSUBMIT_CONFIGURATION"] == rc_file

        # Reading the configuration file
        APIBasicConfig.read()
        assert APIBasicConfig.GRAPHDATA_DIR == f"{fixture_gen_rc_sqlite}/metadata/graph"
        assert APIBasicConfig.LOCAL_ROOT_DIR == fixture_gen_rc_sqlite
        assert APIBasicConfig.DATABASE_BACKEND == "sqlite"
        assert APIBasicConfig.DB_DIR == fixture_gen_rc_sqlite
        assert APIBasicConfig.DB_FILE == "autosubmit.db"


class TestPostgresFixtures:
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

    def test_fixture_gen_rc_postgres(self, fixture_gen_rc_pg: str):
        """
        Test if the .autosubmitrc file is generated and the environment variable is set
        """
        rc_file = os.path.join(fixture_gen_rc_pg, ".autosubmitrc")

        # File should exist
        assert os.path.exists(rc_file)

        with open(rc_file, "r") as f:
            content = f.read()
            assert "[database]" in content
            assert "backend = postgres" in content
            assert "postgresql://" in content
            assert fixture_gen_rc_pg in content

    def test_fixture_pg_db(self, fixture_pg_db: Tuple[str, Engine]):
        engine = fixture_pg_db[1]

        # Check if the public schema exists and is the only one
        with engine.connect() as conn:
            schema_names = get_schema_names(conn)
            assert schema_names == ["public"]

    def test_fixture_pg_db_copy_all(self, fixture_pg_db_copy_all: Tuple[str, Engine]):
        engine = fixture_pg_db_copy_all[1]

        # Check if the experiment and details tables are copied
        with engine.connect() as conn:
            exp_rows = conn.execute(select(tables.ExperimentTable)).all()
            details_rows = conn.execute(select(tables.DetailsTable)).all()

        assert len(exp_rows) > 0
        assert len(details_rows) > 0

        # TODO: Check if the other tables are copied
