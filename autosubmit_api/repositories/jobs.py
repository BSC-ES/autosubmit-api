import datetime
import re
from abc import ABC, abstractmethod
from typing import List, Optional

from pydantic import BaseModel

from autosubmit_api.common import utils as common_utils
from autosubmit_api.persistance.pkl_reader import PklReader


class JobData(BaseModel):
    id: int
    name: str
    status: Optional[int] = common_utils.Status.UNKNOWN
    priority: int
    section: str
    date: Optional[datetime.datetime]
    member: Optional[str]
    chunk: Optional[int]
    out_path_local: Optional[str]
    err_path_local: Optional[str]
    out_path_remote: Optional[str]
    err_path_remote: Optional[str]


class JobsRepository(ABC):
    @abstractmethod
    def get_all(self) -> List[JobData]:
        """
        Gets all jobs
        """

    @abstractmethod
    def get_last_modified_timestamp(self) -> int:
        """
        Gets the last modified UNIX timestamp of the jobs
        """

    def search(
        self, job_name: Optional[str] = None, status: Optional[str] = None
    ) -> List[JobData]:
        """
        Searches jobs by a query string
        """


class JobsPklRepository(JobsRepository):
    def __init__(self, expid: str) -> None:
        self.expid = expid
        self.pkl_reader = PklReader(expid)

    def get_all(self) -> List[JobData]:
        """
        Gets all jobs from pkl file
        """
        pkl_content = self.pkl_reader.parse_job_list()
        return [
            JobData(
                id=job.id,
                name=job.name,
                status=job.status,
                priority=job.priority,
                section=job.section,
                date=job.date,
                member=job.member,
                chunk=job.chunk,
                out_path_local=job.out_path_local,
                err_path_local=job.err_path_local,
                out_path_remote=job.out_path_remote,
                err_path_remote=job.err_path_remote,
            )
            for job in pkl_content
        ]

    def get_last_modified_timestamp(self) -> int:
        return self.pkl_reader.get_modified_time()

    @staticmethod
    def _wildcard_compare(expression: Optional[str], value: str) -> bool:
        """
        Compares a value with a wildcard expression.
        The expression can contain '*' as wildcard, and '!' as negation.
        If the expression is empty, it matches everything.
        Examples:
        - 'test*' matches 'test123', 'test_abc', etc. Not matching '123test'.
        - '!test*' does not match 'test123', 'test_abc', etc
        """
        if not expression:
            return True
        if expression.startswith("!"):
            return not JobsPklRepository._wildcard_compare(expression[1:], value)

        # Transform to regex style: escape metacharacters, then convert '*' wildcard to '.*'
        escaped_expression = re.escape(expression)
        pattern = escaped_expression.replace(r"\*", ".*")
        return bool(re.search(pattern, value))

    def search(
        self, job_name: Optional[str] = None, status: Optional[str] = None
    ) -> List[JobData]:
        """
        Searches jobs by a query string
        """
        pkl_content = self.pkl_reader.parse_job_list()

        return [
            JobData(
                id=job.id,
                name=job.name,
                status=job.status,
                priority=job.priority,
                section=job.section,
                date=job.date,
                member=job.member,
                chunk=job.chunk,
                out_path_local=job.out_path_local,
                err_path_local=job.err_path_local,
                out_path_remote=job.out_path_remote,
                err_path_remote=job.err_path_remote,
            )
            for job in pkl_content
            if JobsPklRepository._wildcard_compare(job_name, job.name)
            and (status is None or job.status == status)
        ]


def create_jobs_repository(expid: str) -> JobsRepository:
    """
    Factory function to create a JobsRepository instance.
    TODO: For future Autosubmit versions, this should verify
    the version to decide using SQL or PKL repository.
    """
    return JobsPklRepository(expid)
