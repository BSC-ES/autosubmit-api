import datetime
from abc import ABC, abstractmethod
from typing import Any, List, Literal, Optional, Union

from pydantic import BaseModel

from autosubmit_api.common import utils as common_utils
from autosubmit_api.persistance.pkl_reader import PklReader


class JobData(BaseModel):
    id: Any
    name: str
    status: Optional[int] = common_utils.Status.UNKNOWN
    priority: int
    section: str
    date: Optional[datetime.datetime]
    member: Optional[str]
    chunk: Optional[int]
    split: Optional[int]
    splits: Optional[int]
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

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[JobData]:
        """
        Gets a job by its name
        """

    @abstractmethod
    def get_by_names(self, names: List[str]) -> List[JobData]:
        """
        Gets jobs matching any of the given names
        """

    def search(
        self,
        status: Optional[str] = None,
        date: Optional[str] = None,
        member: Optional[str] = None,
        section: Optional[str] = None,
    ) -> List[JobData]:
        """
        Searches jobs
        """

    @abstractmethod
    def get_properties_counts(self, properties: List[str]) -> dict[tuple, int]:
        """
        Gets the counts of jobs in each set of properties (e.g., status, section, etc.)
        Do similar to a group by query in SQL, but for the given properties.
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
                split=job.split,
                splits=job.splits,
                out_path_local=job.out_path_local,
                err_path_local=job.err_path_local,
                out_path_remote=job.out_path_remote,
                err_path_remote=job.err_path_remote,
            )
            for job in pkl_content
        ]

    def get_last_modified_timestamp(self) -> int:
        return self.pkl_reader.get_modified_time()

    def get_by_name(self, name: str) -> Optional[JobData]:
        """
        Gets a job by its name from pkl file
        """
        pkl_content = self.pkl_reader.parse_job_list()
        for job in pkl_content:
            if job.name == name:
                return JobData(
                    id=job.id,
                    name=job.name,
                    status=job.status,
                    priority=job.priority,
                    section=job.section,
                    date=job.date,
                    member=job.member,
                    chunk=job.chunk,
                    split=job.split,
                    splits=job.splits,
                    out_path_local=job.out_path_local,
                    err_path_local=job.err_path_local,
                    out_path_remote=job.out_path_remote,
                    err_path_remote=job.err_path_remote,
                )
        return None

    def get_by_names(self, names: List[str]) -> List[JobData]:
        """
        Gets all jobs whose names are in the given list, reading the pkl once.
        """
        name_set = set(names)
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
                split=job.split,
                splits=job.splits,
                out_path_local=job.out_path_local,
                err_path_local=job.err_path_local,
                out_path_remote=job.out_path_remote,
                err_path_remote=job.err_path_remote,
            )
            for job in pkl_content
            if job.name in name_set
        ]

    def search(
        self,
        status: Optional[str] = None,
        date: Optional[str] = None,
        member: Optional[str] = None,
        section: Optional[str] = None,
        chunk: Optional[Union[int, Literal["NA"]]] = None,
    ) -> List[JobData]:
        """
        Searches jobs based on the given criteria, reading the pkl once.
        """
        pkl_content = self.pkl_reader.parse_job_list()
        results = []
        print(f"Searching jobs with criteria - status: {status}, date: {date}, member: {member}, section: {section}, chunk: {chunk}")
        for job in pkl_content:
            print(f"Checking job: {job.name}, status: {job.status}, date: {job.date}, member: {job.member}, section: {job.section}, chunk: {job.chunk}")
            if date is not None:
                if date == "NA" and job.date is not None:
                    continue
                if date != "NA" and (job.date is None or job.date.strftime("%Y-%m-%d") != date):
                    continue
            if member is not None:
                if member == "NA" and job.member is not None:
                    continue
                if member != "NA" and job.member != member:
                    continue
            if section is not None:
                if section == "NA" and job.section is not None:
                    continue
                if section != "NA" and job.section != section:
                    continue
            if chunk is not None:
                if chunk == "NA" and job.chunk is not None:
                    continue
                if chunk != "NA" and job.chunk != chunk:
                    continue

            results.append(
                JobData(
                    id=job.id,
                    name=job.name,
                    status=job.status,
                    priority=job.priority,
                    section=job.section,
                    date=job.date,
                    member=job.member,
                    chunk=job.chunk,
                    split=job.split,
                    splits=job.splits,
                    out_path_local=job.out_path_local,
                    err_path_local=job.err_path_local,
                    out_path_remote=job.out_path_remote,
                    err_path_remote=job.err_path_remote,
                )
            )
        return results

    def get_properties_counts(self, properties: List[str]) -> dict[tuple, int]:
        pkl_content = self.pkl_reader.parse_job_list()
        counts = {}
        for job in pkl_content:
            key = tuple(getattr(job, prop) for prop in properties)
            counts[key] = counts.get(key, 0) + 1
        return counts


def create_jobs_repository(expid: str) -> JobsRepository:
    """
    Factory function to create a JobsRepository instance.
    TODO: For future Autosubmit versions, this should verify
    the version to decide using SQL or PKL repository.
    """
    return JobsPklRepository(expid)
