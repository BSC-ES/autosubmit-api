"""Custom domain exceptions.

The exceptions defined in this module should not carry any HTTP semantics.
The API layer should be responsible to map them to HTTP responses in
``autosubmit_api.api_error_handlers``."""


class DomainError(Exception):
    """Base class for domain exceptions."""


class NotFoundError(DomainError, ValueError):
    """Raised when a resource does not exist.

    Inherits from ``ValueError`` for backwards compatibility with callers
    that previously caught ``ValueError`` for not-found conditions.
    """


class ValidationError(DomainError):
    """Raised when a request is not valid for the domain."""


class ExperimentNotFoundError(NotFoundError):
    """Raised when an experiment does not exist."""

    def __init__(self, expid: str) -> None:
        super().__init__(f"Experiment with expid '{expid}' not found.")


class JobNotFoundError(NotFoundError):
    """Raised when a job does not exist in an experiment."""

    def __init__(self, expid: str, job_name: str) -> None:
        super().__init__(
            f"Job with name '{job_name}' not found in experiment '{expid}'"
        )


class JobListNotFoundError(NotFoundError):
    """Raised when the job list of an experiment is not available yet.

    Experiments that have never run do not have a job list: neither the
    ``job_list_<expid>.pkl`` file (Autosubmit before 4.2.0) nor the
    ``job_list.db`` file / ``<expid>.job_list`` table (4.2.0 and later).
    """

    def __init__(self, expid: str) -> None:
        super().__init__(f"Job list for experiment '{expid}' not found.")


class ExperimentRunNotFoundError(NotFoundError):
    """Raised when an experiment has no run data available yet.

    Experiments that have never run do not have run data: neither the
    ``experiment_run`` table of the ``job_data_<expid>.db`` file (sqlite) nor
    the ``<expid>.experiment_run`` table (postgres).
    """

    def __init__(self, expid: str) -> None:
        super().__init__(f"Run data for experiment '{expid}' not found.")


class SectionNotFoundError(ValidationError):
    """Raised when no jobs match the requested section for an experiment."""


class SectionNotChunkedError(ValidationError):
    """Raised when the section exists but is not configured with RUNNING: chunk."""
