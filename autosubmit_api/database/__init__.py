import os

from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.repositories.experiment import create_experiment_repository
from autosubmit_api.repositories.experiment_details import (
    create_experiment_details_repository,
)
from autosubmit_api.repositories.experiment_status import (
    create_experiment_status_repository,
)


def prepare_db():
    create_experiment_repository()
    create_experiment_status_repository()
    create_experiment_details_repository()

    os.makedirs(APIBasicConfig.GRAPHDATA_DIR, exist_ok=True)
