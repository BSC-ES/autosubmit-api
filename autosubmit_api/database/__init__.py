import os
from sqlalchemy import text
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.database.common import (
    create_as_times_db_engine,
    create_autosubmit_db_engine,
)
from autosubmit_api.database.tables import experiment_status_table, details_table


def prepare_db():
    with create_as_times_db_engine().connect() as conn:
        experiment_status_table.create(conn, checkfirst=True)

    with create_autosubmit_db_engine().connect() as conn:
        details_table.create(conn, checkfirst=True)

        view_name = "listexp"
        view_from = "select id,name,user,created,model,branch,hpc,description from experiment left join details on experiment.id = details.exp_id"
        new_view_stmnt = f"CREATE VIEW IF NOT EXISTS {view_name} as {view_from}"
        conn.execute(text(new_view_stmnt))

    os.makedirs(APIBasicConfig.GRAPHDATA_DIR, exist_ok=True)
