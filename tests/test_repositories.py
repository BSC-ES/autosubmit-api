from typing import Any, Dict, List
from uuid import uuid4

import pytest

from autosubmit_api.repositories.experiment import create_experiment_repository
from autosubmit_api.repositories.experiment_status import (
    create_experiment_status_repository,
)
from autosubmit_api.repositories.graph_layout import create_exp_graph_layout_repository
from autosubmit_api.repositories.jobs import JobsPklRepository
from autosubmit_api.repositories.join.experiment_join import (
    generate_query_listexp_extended,
)
from autosubmit_api.repositories.runner_processes import (
    create_runner_processes_repository,
)

BASE_FROM = (
    "FROM experiment LEFT OUTER JOIN details ON experiment.id = details.exp_id "
    "LEFT OUTER JOIN experiment_status ON experiment.id = experiment_status.exp_id"
)


@pytest.mark.parametrize(
    "query_args, expected_in_query, expected_params",
    [
        # Test the basic query generation
        (dict(), [BASE_FROM], {}),
        # Test the query generation with a search query
        (
            dict(query="test"),
            [
                BASE_FROM,
                "experiment.name LIKE :name_1",
                "experiment.description LIKE :description_1",
                'details."user" LIKE :user_1',
            ],
            {"name_1": "%test%", "description_1": "%test%", "user_1": "%test%"},
        ),
        # Test the query generation with active filter
        (
            dict(only_active=True),
            [BASE_FROM, "experiment_status.status = :status_1"],
            {"status_1": "RUNNING"},
        ),
        # Test the query generation with owner filter
        (
            dict(owner="test"),
            [BASE_FROM, 'details."user" LIKE :user_1'],
            {"user_1": "test"},
        ),
        # Test the query generation with experiment type filter
        (
            dict(exp_type="test"),
            [BASE_FROM, "experiment.name LIKE :name_1"],
            {"name_1": "t%"},
        ),
        (
            dict(exp_type="operational"),
            [BASE_FROM, "experiment.name LIKE :name_1"],
            {"name_1": "o%"},
        ),
        (
            dict(exp_type="experiment"),
            [
                BASE_FROM,
                "experiment.name NOT LIKE :name_1",
                "experiment.name NOT LIKE :name_2",
            ],
            {"name_1": "t%", "name_2": "o%"},
        ),
        # Test the query generation with autosubmit version filter
        (
            dict(autosubmit_version="1.0"),
            [BASE_FROM, "experiment.autosubmit_version LIKE :autosubmit_version_1"],
            {"autosubmit_version_1": "1.0"},
        ),
        # Test the query generation with hpc filter
        (
            dict(hpc="MN5"),
            [BASE_FROM, "details.hpc LIKE :hpc_1"],
            {"hpc_1": "MN5"},
        ),
        # Test the query generation with order by
        (
            dict(order_by="expid"),
            [BASE_FROM, "ORDER BY experiment.name"],
            {},
        ),
        (
            dict(order_by="expid", order_desc=True),
            [BASE_FROM, "ORDER BY experiment.name DESC"],
            {},
        ),
        # Test wildcard search query
        (
            dict(owner="foo*bar"),
            [BASE_FROM, 'details."user" LIKE :user_1'],
            {"user_1": "foo%bar"},
        ),
        (
            dict(owner="!foo*bar*baz"),
            [BASE_FROM, 'details."user" NOT LIKE :user_1'],
            {"user_1": "foo%bar%baz"},
        ),
        (
            dict(autosubmit_version="3.*.0"),
            [BASE_FROM, "experiment.autosubmit_version LIKE :autosubmit_version_1"],
            {"autosubmit_version_1": "3.%.0"},
        ),
        (
            dict(autosubmit_version="!3.*.0"),
            [BASE_FROM, "experiment.autosubmit_version NOT LIKE :autosubmit_version_1"],
            {"autosubmit_version_1": "3.%.0"},
        ),
        (
            dict(owner="!foo*bar*baz", autosubmit_version="3.*.0", hpc="MN*"),
            [
                BASE_FROM,
                'details."user" NOT LIKE :user_1',
                "experiment.autosubmit_version LIKE :autosubmit_version_1",
                "details.hpc LIKE :hpc_1",
            ],
            {"user_1": "foo%bar%baz", "autosubmit_version_1": "3.%.0", "hpc_1": "MN%"},
        ),
    ],
)
def test_experiment_search_query_generator(
    query_args: Dict[str, Any],
    expected_in_query: List[str],
    expected_params: Dict[str, str],
):
    query = generate_query_listexp_extended(**query_args)

    for expected in expected_in_query:
        assert expected in str(query)

    query_params = query.compile().params

    for param, value in expected_params.items():
        assert query_params[param] == value


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


class TestExperimentStatusRepository:
    def test_operations(self, fixture_mock_basic_config):
        experiment_status_db = create_experiment_status_repository()

        experiment_status_db.delete_all()
        assert experiment_status_db.get_all() == []

        # Insert data
        experiment_status_db.upsert_status(1, "a003", "RUNNING")
        experiment_status_db.upsert_status(2, "a007", "NOT_RUNNING")
        experiment_status_db.upsert_status(3, "a3tb", "RUNNING")

        data = experiment_status_db.get_all()
        assert len(data) == 3

        experiment_status_db.upsert_status(1, "a003", "NOT_RUNNING")
        data = experiment_status_db.get_all()
        assert len(data) == 3

        # Assert only_running
        only_running = experiment_status_db.get_only_running_expids()
        assert set(only_running) == {"a3tb"}


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


class TestExperimentRunnerRepository:
    def test_runner_repository(self, fixture_mock_basic_config):
        runner_repo = create_runner_processes_repository()

        TEST_EXPID = str(uuid4())

        # Insert a new process
        inserted_runner = runner_repo.insert_process(
            expid=TEST_EXPID,
            pid=1234,
            status="ACTIVE",
            runner="LOCAL",
            module_loader="no_module",
            modules="",
        )

        # Check if the process was inserted correctly
        active_runners = runner_repo.get_active_processes_by_expid(TEST_EXPID)
        assert len(active_runners) == 1
        assert active_runners[0].id == inserted_runner.id
        assert active_runners[0].expid == TEST_EXPID
        assert active_runners[0].status == "ACTIVE"

        # Update the process status
        runner_repo.update_process_status(id=inserted_runner.id, status="COMPLETED")

        # Check if there is no active process
        active_runners = runner_repo.get_active_processes_by_expid(TEST_EXPID)
        assert len(active_runners) == 0

        # Check if is the last process
        last_process = runner_repo.get_last_process_by_expid(TEST_EXPID)
        assert last_process.id == inserted_runner.id
        assert last_process.expid == TEST_EXPID
        assert last_process.status == "COMPLETED"


@pytest.mark.parametrize(
    "expression,value,expected",
    [
        # No expression matches everything
        (None, "foobar", True),
        ("", "foobar", True),
        # Simple match
        ("foo", "foo", True),
        ("foo", "foobar", True),
        # Wildcard at end
        ("foo*", "foobar", True),
        ("foo*", "fo", False),
        # Wildcard at start
        ("*bar", "foobar", True),
        ("*bar", "barfoo", True),
        # Wildcard at both ends
        ("*foo*", "barfoo", True),
        ("*foo*", "bar", False),
        # Negation
        ("!foo*", "foobar", False),
        ("!foo*", "barfoo", False),
        # Edge cases
        ("*", "foobar", True),
        ("!*", "foobar", False),
        # Wildcard in the middle
        ("foo*bar", "foobazbar", True),
        ("foo*bar", "foobaz", False),
    ],
)
def test_wildcard_compare(expression: str, value: str, expected: bool):
    assert JobsPklRepository._wildcard_compare(expression, value) == expected
