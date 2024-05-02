"""
This module contains the repositories for the database tables.

The repositories are used to interact with the database tables delegating the SQL statements generation and execution order.

Other modules can use the repositories to interact with the database tables without the need to know the SQL syntax.
"""

from autosubmit_api.database.repositories.experiment import ExperimentDbRepository
from autosubmit_api.database.repositories.experiment_details import (
    ExperimentDetailsDbRepository,
)
from autosubmit_api.database.repositories.experiment_status import (
    ExperimentStatusDbRepository,
)
from autosubmit_api.database.repositories.experiment_structure import (
    ExperimentStructureDbRepository,
)
from autosubmit_api.database.repositories.graph_draw import ExpGraphDrawDBRepository
from autosubmit_api.database.repositories.join.experiment_join import (
    ExperimentJoinDbRepository,
)
from autosubmit_api.database.repositories.job_packages import (
    JobPackagesDbRepository,
    WrapperJobPackagesDbRepository,
)
from autosubmit_api.database.repositories.experiment_run import (
    ExperimentRunDbRepository,
)
from autosubmit_api.database.repositories.job_data import JobDataDbRepository


__all__ = [
    "ExperimentDbRepository",
    "ExperimentDetailsDbRepository",
    "ExperimentStatusDbRepository",
    "ExperimentStructureDbRepository",
    "ExperimentRunDbRepository",
    "JobDataDbRepository",
    "ExpGraphDrawDBRepository",
    "ExperimentJoinDbRepository",
    "JobPackagesDbRepository",
    "WrapperJobPackagesDbRepository",
]
