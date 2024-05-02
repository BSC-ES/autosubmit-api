
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.database import tables
from autosubmit_api.database.common import create_autosubmit_db_engine
from autosubmit_api.workers.populate_details.populate import DetailsProcessor

class TestDetailsPopulate:

    def test_process(self,fixture_mock_basic_config: APIBasicConfig):

        with create_autosubmit_db_engine().connect() as conn:
            conn.execute(tables.DetailsTable.delete())
            conn.commit()

            count = DetailsProcessor(fixture_mock_basic_config).process()

            rows = conn.execute(tables.DetailsTable.select()).all()

            assert len(rows) > 0
            assert len(rows) == count