from autosubmit_api.database.common import create_as_times_db_engine
from autosubmit_api.database.tables import experiment_status_table


def prepare_db():
    with create_as_times_db_engine().connect() as conn:
        experiment_status_table.create(conn, checkfirst=True)