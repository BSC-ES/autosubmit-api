import os

from sqlalchemy import select

from autosubmit_api.database import common, tables


def count_pid_lsof(pid):
    openfiles = os.popen(f"lsof -p {pid} | grep db").read()
    print(openfiles)
    return len([x for x in openfiles.strip("\n ").split("\n") if len(x.strip()) > 0])


class TestDatabase:

    def test_open_files(self, fixture_mock_basic_config):
        current_pid = os.getpid()

        counter = count_pid_lsof(current_pid)

        engine = common.create_autosubmit_db_engine()

        assert counter == count_pid_lsof(current_pid)

        with engine.connect() as conn:
            conn.execute(select(tables.ExperimentTable))
            assert counter + 1 == count_pid_lsof(current_pid)

        assert counter == count_pid_lsof(current_pid)
