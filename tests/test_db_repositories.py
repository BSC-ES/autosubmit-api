from autosubmit_api.database.repositories.experiment import ExperimentDbRepository
from autosubmit_api.database.repositories.experiment_structure import (
    ExperimentStructureDbRepository,
)
from autosubmit_api.database.repositories.graph_draw import ExpGraphDrawDBRepository
from autosubmit_api.database.repositories.join.experiment_join import (
    ExperimentJoinDbRepository,
)


class TestExperimentDbRepository:
    def test_operations(self, fixture_mock_basic_config):
        experiment_db = ExperimentDbRepository()

        # Check get_all
        rows = experiment_db.get_all()
        assert len(rows) >= 4
        for expid in ["a003", "a007", "a3tb", "a6zj"]:
            assert expid in [row.get("name") for row in rows]

        # Check get_by_expid
        row = experiment_db.get_by_expid("a003")
        assert row["name"] == "a003"


class TestExpGraphDrawDBRepository:
    def test_operations(self, fixture_mock_basic_config):
        expid = "g001"
        graph_draw_db = ExpGraphDrawDBRepository(expid)

        # Create table
        graph_draw_db.create_table()

        # Table exists and is empty
        assert graph_draw_db.get_all() == []

        # Insert data
        data = [
            {"id": 1, "job_name": "job1", "x": 1, "y": 2},
            {"id": 2, "job_name": "job2", "x": 2, "y": 3},
        ]
        assert graph_draw_db.insert_many(data) == len(data)

        # Get data
        assert graph_draw_db.get_all() == data

        # Delete data
        assert graph_draw_db.delete_all() == len(data)

        # Table is empty
        assert graph_draw_db.get_all() == []


class TestExperimentJoinDbRepository:
    def test_search(self, fixture_mock_basic_config):
        experiment_join_db = ExperimentJoinDbRepository()

        # Check search
        rows, total = experiment_join_db.search(limit=3)
        assert len(rows) == 3
        assert total >= 4

        for row in rows:
            assert row.get("status")


class TestExperimentStructureDbRepository:
    def test_get(self, fixture_mock_basic_config):
        structure_db = ExperimentStructureDbRepository("a007")
        
        # Check get_structure
        structure = structure_db.get_structure()
        assert sorted(structure) == sorted({
            "a007_20000101_fc0_1_SIM": ["a007_20000101_fc0_2_SIM"],
            "a007_20000101_fc0_2_SIM": ["a007_POST"],
            "a007_20000101_fc0_INI": ["a007_20000101_fc0_1_SIM"],
            "a007_20000101_fc0_TRANSFER": [],
            "a007_CLEAN": ["a007_20000101_fc0_TRANSFER"],
            "a007_LOCAL_SETUP": ["a007_REMOTE_SETUP"],
            "a007_POST": ["a007_CLEAN"],
            "a007_REMOTE_SETUP": ["a007_20000101_fc0_INI"],
        })
