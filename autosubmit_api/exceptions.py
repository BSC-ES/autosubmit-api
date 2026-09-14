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


class SectionNotFoundError(ValidationError):
    """Raised when no jobs match the requested section for an experiment."""


class SectionNotChunkedError(ValidationError):
    """Raised when the section exists but is not configured with RUNNING: chunk."""
