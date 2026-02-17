import pytest
from unittest.mock import patch, MagicMock
from autosubmit_api.builders.experiment_builder import ExperimentBuilder
from autosubmit_api.database.models import ExperimentModel
from autosubmit_api.repositories.experiment_details import ExperimentDetailsModel


@pytest.fixture
def experiment_builder():
    return ExperimentBuilder()


class TestExperimentBuilder:
    def test_produce_pkl_modified_time(self):
        experiment_builder = ExperimentBuilder()
        with patch(
            "autosubmit_api.builders.experiment_builder.create_jobs_repository"
        ) as MockPklReader:
            mock_pkl_reader = MockPklReader.return_value
            mock_pkl_reader.get_last_modified_timestamp.return_value = (
                1609459200  # Mock timestamp for 2021-01-01 00:00:00 UTC
            )

            experiment_builder._product = MagicMock()
            experiment_builder.produce_pkl_modified_time()

            assert isinstance(experiment_builder._product.modified, str)
            assert experiment_builder._product.modified.startswith(
                "2021-01-01T00:00:00"
            )

    def test_produce_base_from_dict(self):
        experiment_builder = ExperimentBuilder()

        mock_dict = {
            "id": 1,
            "name": "test_experiment",
            "description": "A test experiment",
            "autosubmit_version": "1.0",
        }

        experiment_builder.produce_base_from_dict(mock_dict)

        assert isinstance(experiment_builder._product, ExperimentModel)
        assert experiment_builder._product.id == 1
        assert experiment_builder._product.name == "test_experiment"
        assert experiment_builder._product.description == "A test experiment"
        assert experiment_builder._product.autosubmit_version == "1.0"

    def test_produce_base(self):
        experiment_builder = ExperimentBuilder()

        with patch(
            "autosubmit_api.builders.experiment_builder.create_experiment_repository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_expid.return_value = ExperimentModel(
                id=1,
                name="test_experiment",
                description="A test experiment",
                autosubmit_version="1.0",
            )

            experiment_builder.produce_base("test_experiment")

            assert isinstance(experiment_builder._product, ExperimentModel)
            assert experiment_builder._product.id == 1
            assert experiment_builder._product.name == "test_experiment"
            assert experiment_builder._product.description == "A test experiment"
            assert experiment_builder._product.autosubmit_version == "1.0"

    def test_produce_details(self):
        experiment_builder = ExperimentBuilder()

        with patch(
            "autosubmit_api.builders.experiment_builder.create_experiment_details_repository"
        ) as MockRepo:
            mock_repo = MockRepo.return_value
            mock_repo.get_by_exp_id.return_value = ExperimentDetailsModel(
                exp_id=1,
                user="test_user",
                created="2021-01-01T00:00:00",
                model="test_model",
                branch="test_branch",
                hpc="test_hpc",
            )

            experiment_builder._product = MagicMock()
            experiment_builder._product.id = 1
            experiment_builder.produce_details()

            assert experiment_builder._product.user == "test_user"
            assert experiment_builder._product.created == "2021-01-01T00:00:00"
            assert experiment_builder._product.model == "test_model"
            assert experiment_builder._product.branch == "test_branch"
            assert experiment_builder._product.hpc == "test_hpc"
