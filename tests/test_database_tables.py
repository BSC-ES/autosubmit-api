from autosubmit_api.database import tables


def test_experiment_structure_v4_2_0_uses_weak_dependency_column():
    columns = set(tables.ExperimentStructureV4_2_0.c.keys())

    assert "weak" in columns
    assert "fail_ok" not in columns
