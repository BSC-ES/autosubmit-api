from unittest.mock import patch

import pytest
from sqlalchemy import event

from autosubmit_api.bgtasks.tasks.details_updater import PopulateDetailsDB
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.database import common
from autosubmit_api.repositories.experiment_details import (
    ExperimentDetailsModel,
    create_experiment_details_repository,
)


class TestDetailsPopulate:
    def test_process(self, fixture_mock_basic_config: APIBasicConfig):
        details_repo = create_experiment_details_repository()
        details_repo.delete_all()

        rows = details_repo.get_all()
        assert len(rows) == 0

        count = PopulateDetailsDB.procedure()

        rows = details_repo.get_all()
        assert len(rows) > 0
        assert len(rows) == count

        first_detail = details_repo.get_by_exp_id(rows[0].exp_id)
        assert first_detail.exp_id is not None

    def test_process_writes_in_a_single_transaction(
        self, fixture_mock_basic_config: APIBasicConfig
    ):
        details_repo = create_experiment_details_repository()
        details_repo.delete_all()

        commits = []
        event.listen(details_repo.engine, "commit", lambda conn: commits.append(conn))

        with patch(
            "autosubmit_api.bgtasks.tasks.details_updater.create_experiment_details_repository",
            autospec=True,
            return_value=details_repo,
        ) as mock_create_repo:
            count = PopulateDetailsDB.procedure()

        assert count > 1
        assert mock_create_repo.call_count == 1
        assert len(commits) == 1
        assert len(details_repo.get_all()) == count

    def test_process_skips_writes_when_nothing_changed(
        self, fixture_mock_basic_config: APIBasicConfig
    ):
        details_repo = create_experiment_details_repository()
        details_repo.delete_all()
        PopulateDetailsDB.procedure()
        stored = details_repo.get_all()

        commits = []
        event.listen(details_repo.engine, "commit", lambda conn: commits.append(conn))

        with patch(
            "autosubmit_api.bgtasks.tasks.details_updater.create_experiment_details_repository",
            autospec=True,
            return_value=details_repo,
        ):
            count = PopulateDetailsDB.procedure()

        assert count == 0
        assert commits == []
        assert details_repo.get_all() == stored

    def test_process_writes_only_missing_and_changed_details(
        self, fixture_mock_basic_config: APIBasicConfig
    ):
        details_repo = create_experiment_details_repository()
        details_repo.delete_all()
        PopulateDetailsDB.procedure()
        stored = {detail.exp_id: detail for detail in details_repo.get_all()}
        changed_id, missing_id = sorted(stored)[:2]

        details_repo.upsert_many_details(
            [stored[changed_id].model_copy(update={"model": "outdated"})]
        )
        with details_repo.engine.begin() as conn:
            conn.execute(
                details_repo.table.delete().where(
                    details_repo.table.c.exp_id == missing_id
                )
            )

        with patch(
            "autosubmit_api.repositories.experiment_details.execute_upsert",
            autospec=True,
            side_effect=common.execute_upsert,
        ) as mock_upsert:
            count = PopulateDetailsDB.procedure()

        written_ids = {call.args[2]["exp_id"] for call in mock_upsert.call_args_list}
        assert written_ids == {changed_id, missing_id}
        assert count == 2
        assert {detail.exp_id: detail for detail in details_repo.get_all()} == stored

    def test_process_returns_early_without_experiments(
        self, fixture_mock_basic_config: APIBasicConfig
    ):
        with (
            patch.object(
                PopulateDetailsDB, "_get_experiments", autospec=True, return_value=[]
            ),
            patch(
                "autosubmit_api.bgtasks.tasks.details_updater.create_experiment_details_repository",
                autospec=True,
            ) as mock_create_repo,
        ):
            count = PopulateDetailsDB.procedure()

        assert count == 0
        mock_create_repo.assert_not_called()


class TestUpsertManyDetails:
    def test_upsert_many_details_is_atomic(
        self, fixture_mock_basic_config: APIBasicConfig
    ):
        details_repo = create_experiment_details_repository()
        details_repo.delete_all()
        details = [
            ExperimentDetailsModel(
                exp_id=exp_id,
                user="user",
                created="2026-01-01T00:00:00",
                model="model",
                branch="branch",
                hpc="hpc",
            )
            for exp_id in (1, 2)
        ]

        def fail_on_second_row(*args, **kwargs):
            if mock_upsert.call_count == 2:
                raise RuntimeError("write failed")
            return common.execute_upsert(*args, **kwargs)

        with patch(
            "autosubmit_api.repositories.experiment_details.execute_upsert",
            autospec=True,
            side_effect=fail_on_second_row,
        ) as mock_upsert:
            with pytest.raises(RuntimeError):
                details_repo.upsert_many_details(details)

        assert mock_upsert.call_count == 2

        assert details_repo.get_all() == []
