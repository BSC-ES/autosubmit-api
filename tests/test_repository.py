from typing import Any, Dict, List
from autosubmit_api.repositories.join.experiment_join import generate_query_listexp_extended
import pytest

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
