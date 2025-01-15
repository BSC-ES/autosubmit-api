from autosubmit_api.bgtasks.tasks.details_updater import PopulateDetailsDB
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.database import tables
from autosubmit_api.database.common import create_autosubmit_db_engine
from autosubmit_api.repositories.experiment_details import (
    create_experiment_details_repository,
)


class TestDetailsPopulate:
    def test_process(self, fixture_mock_basic_config: APIBasicConfig):
        details_repo = create_experiment_details_repository()
        details_repo.delete_all()

        with create_autosubmit_db_engine().connect() as conn:
            rows = conn.execute(tables.details_table.select()).all()
            assert len(rows) == 0

            count = PopulateDetailsDB.procedure()

            rows = conn.execute(tables.details_table.select()).all()

        assert len(rows) > 0
        assert len(rows) == count

        first_detail = details_repo.get_by_exp_id(rows[0].exp_id)
        assert first_detail.exp_id is not None
