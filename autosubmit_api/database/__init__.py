from autosubmit_api.database.adapters import (
    ExperimentDbAdapter,
    ExperimentDetailsDbAdapter,
    ExperimentStatusDbAdapter,
)


def prepare_db():
    ExperimentDbAdapter().create_table()
    ExperimentDetailsDbAdapter().create_table()
    ExperimentStatusDbAdapter().create_table()
