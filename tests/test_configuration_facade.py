from typing import Any, Dict
import pytest
from autosubmit_api.builders.configuration_facade_builder import (
    AutosubmitConfigurationFacadeBuilder,
    ConfigurationFacadeDirector,
)


@pytest.mark.parametrize(
    "expid, expected, expected_method_results",
    [
        (
            "a003",
            {
                "chunk_unit": "month",
                "chunk_size": 4,
                "current_years_per_sim": 1 / 3,
                "sim_processors": 16,
                "sim_tasks": None,
                "sim_nodes": None,
                "sim_processors_per_node": None,
                "sim_exclusive": False,
            },
            {
                "version": "4.0.0",
                "main_platform": "LOCAL",
                "model": "NA",
                "branch": "NA",
            },
        ),
        (
            "a3tb",
            {
                "chunk_unit": "month",
                "chunk_size": 1,
                "current_years_per_sim": 1 / 12,
                "sim_processors": 768,
                "sim_tasks": None,
                "sim_nodes": None,
                "sim_processors_per_node": None,
                "sim_exclusive": False,
            },
            {
                "version": "3.13.0",
                "main_platform": "marenostrum4",
                "model": "https://earth.bsc.es/gitlab/es/auto-ecearth3.git",
                "branch": "trunk",
            },
        ),
        (
            "a007",
            {
                "chunk_unit": "month",
                "chunk_size": 4,
                "current_years_per_sim": 1 / 3,
                "sim_processors": 8,
                "sim_tasks": None,
                "sim_nodes": None,
                "sim_processors_per_node": None,
                "sim_exclusive": True,
            },
            {
                "version": "4.0.95",
                "main_platform": "LOCAL",
                "model": "NA",
                "branch": "NA",
            },
        ),
    ],
)
def test_configuration_facade(
    fixture_mock_basic_config,
    expid: str,
    expected: Dict[str, Any],
    expected_method_results: Dict[str, Any],
):
    autosubmit_config_facade = ConfigurationFacadeDirector(
        AutosubmitConfigurationFacadeBuilder(expid)
    ).build_autosubmit_configuration_facade()

    assert autosubmit_config_facade.expid == expid

    # Assert properties
    assert {
        "chunk_unit": autosubmit_config_facade.chunk_unit,
        "chunk_size": autosubmit_config_facade.chunk_size,
        "current_years_per_sim": autosubmit_config_facade.current_years_per_sim,
        "sim_processors": autosubmit_config_facade.sim_processors,
        "sim_tasks": autosubmit_config_facade.sim_tasks,
        "sim_nodes": autosubmit_config_facade.sim_nodes,
        "sim_processors_per_node": autosubmit_config_facade.sim_processors_per_node,
        "sim_exclusive": autosubmit_config_facade.sim_exclusive,
    } == expected

    # Assert methods
    assert (
        autosubmit_config_facade.get_autosubmit_version()
        == expected_method_results["version"]
    )
    assert (
        autosubmit_config_facade.get_main_platform()
        == expected_method_results["main_platform"]
    )
    assert autosubmit_config_facade.get_model() == expected_method_results["model"]
    assert autosubmit_config_facade.get_branch() == expected_method_results["branch"]
