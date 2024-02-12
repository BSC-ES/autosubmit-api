from autosubmit_api.bgtasks.tasks.status_updater import StatusUpdater
from autosubmit_api.database import tables
from autosubmit_api.database.common import (
    create_autosubmit_db_engine,
    create_as_times_db_engine,
)
from autosubmit_api.history.database_managers.database_models import RunningStatus

class TestStatusUpdater:

    def test_same_tables(self, fixture_mock_basic_config):
        
        StatusUpdater.run()
        
        with create_autosubmit_db_engine().connect() as conn:
            experiments = conn.execute(tables.experiment_table.select()).all()
        
        with create_as_times_db_engine().connect() as conn:
            exps_status = conn.execute(tables.experiment_status_table.select()).all()

        assert len(experiments) == len(exps_status)
        assert set([x.id for x in experiments]) == set([x.exp_id for x in exps_status])
        assert set([x.name for x in experiments]) == set([x.name for x in exps_status])
        
        for e_st in exps_status:
            assert e_st.status in [RunningStatus.RUNNING, RunningStatus.NOT_RUNNING]
