"""
This module contains the adapters for the database tables.

The adapters are used to interact with the database tables delegating the SQL statements generation and execution order.

Other modules can use the adapters to interact with the database tables without the need to know the SQL syntax.
"""

from autosubmit_api.database.adapters.experiment import ExperimentDbAdapter
from autosubmit_api.database.adapters.experiment_details import (
    ExperimentDetailsDbAdapter,
)
from autosubmit_api.database.adapters.experiment_status import (
    ExperimentStatusDbAdapter,
)
from autosubmit_api.database.adapters.graph_draw import ExpGraphDrawDBAdapter
from autosubmit_api.database.adapters.join.experiment_join import ExperimentJoinDbAdapter


__all__ = [
    "ExperimentDbAdapter",
    "ExperimentDetailsDbAdapter",
    "ExperimentStatusDbAdapter",
    "ExpGraphDrawDBAdapter",
    "ExperimentJoinDbAdapter"
]
