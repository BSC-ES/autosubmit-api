from autosubmit_api.repositories.experiment import create_experiment_repository
from autosubmit_api.repositories.graph_layout import create_exp_graph_layout_repository


class TestExperimentRepository:
    def test_operations(self, fixture_mock_basic_config):
        experiment_db = create_experiment_repository()

        EXPIDS = ["a003", "a007", "a3tb", "a6zj"]

        # Check get_all
        rows = experiment_db.get_all()
        assert len(rows) >= 4
        for expid in EXPIDS:
            assert expid in [row.name for row in rows]

        # Check get_by_expid
        for expid in EXPIDS:
            row = experiment_db.get_by_expid(expid)
            assert row.name == expid


class TestExpGraphLayoutRepository:
    def test_operations(self, fixture_mock_basic_config):
        expid = "g001"
        graph_draw_db = create_exp_graph_layout_repository(expid)

        # Table exists and is empty
        assert graph_draw_db.get_all() == []

        # Insert data
        data = [
            {"id": 1, "job_name": "job1", "x": 1, "y": 2},
            {"id": 2, "job_name": "job2", "x": 2, "y": 3},
        ]
        assert graph_draw_db.insert_many(data) == len(data)

        # Get data
        graph_data = [x.model_dump() for x in graph_draw_db.get_all()]
        assert graph_data == data

        # Delete data
        assert graph_draw_db.delete_all() == len(data)

        # Table is empty
        graph_data = [x.model_dump() for x in graph_draw_db.get_all()]
        assert graph_data == []
