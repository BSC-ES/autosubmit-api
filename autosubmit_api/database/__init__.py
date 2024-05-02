from autosubmit_api.database.repositories import (
    ExperimentDbRepository,
    ExperimentDetailsDbRepository,
    ExperimentStatusDbRepository,
)


def prepare_db():
    ExperimentDbRepository().create_table()
    ExperimentDetailsDbRepository().create_table()
    ExperimentStatusDbRepository().create_table()
