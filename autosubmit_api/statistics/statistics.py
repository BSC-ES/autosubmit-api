#!/bin/env/python

from datetime import datetime, timedelta
from typing import List, Union, Dict

from autosubmit.job.job import Job
from .jobs_stat import JobStat
from .stats_summary import StatsSummary
from .utils import timedelta2hours, parse_number_processors

# from collections import namedtuple

_COMPLETED_RETRIAL = 1
_FAILED_RETRIAL = 0


class Statistics(object):

    def __init__(self, jobs, start, end, queue_time_fix):
        # type: (List[Job], datetime, datetime, Dict[str, int]) -> None
        """
        """
        self._jobs = jobs
        self._start = start
        self._end = end
        self._queue_time_fixes = queue_time_fix
        self._name_to_jobstat_dict = dict()  # type: Dict[str, JobStat]
        self.jobs_stat = []  # type: List[JobStat]
        # Old format
        self.max_time = 0.0  # type: float
        self.max_fail = 0  # type: int
        self.start_times = []  # type: List[Union[datetime, None]]
        self.end_times = []  # type: List[Union[datetime, None]]
        self.queued = []  # type: List[timedelta]
        self.run = []  # type: List[timedelta]
        self.failed_jobs = []  # type: List[int]
        self.fail_queued = []  # type: List[timedelta]
        self.fail_run = []  # type: List[timedelta]
        self.wallclocks = []  # type: List[float]
        self.threshold = 0.0  # type: float
        self.failed_jobs_dict = {}  # type: Dict[str, int]
        self.summary = StatsSummary()
        self.totals = [" Description text \n", "Line 1"]

    def calculate_statistics(self):
        # type: () -> List[JobStat]
        for index, job in enumerate(self._jobs):
            retrials = job.get_last_retrials()
            for retrial in retrials:
                job_stat = self._name_to_jobstat_dict.setdefault(job.name, JobStat(job.name, parse_number_processors(
                    job.processors), job.total_wallclock, job.section, job.date, job.member, job.chunk, job.processors_per_node, job.tasks, job.nodes, job.exclusive ))
                job_stat.inc_retrial_count()
                if Job.is_a_completed_retrial(retrial):
                    job_stat.inc_completed_retrial_count()
                    job_stat.submit_time = retrial[0]
                    job_stat.start_time = retrial[1]
                    job_stat.finish_time = retrial[2]
                    adjusted_queue = max(job_stat.start_time - job_stat.submit_time, timedelta()) - timedelta(
                        seconds=self._queue_time_fixes.get(job.name, 0))
                    job_stat.completed_queue_time += max(adjusted_queue, timedelta())
                    job_stat.completed_run_time += max(job_stat.finish_time - job_stat.start_time, timedelta())
                else:
                    job_stat.inc_failed_retrial_count()
                    job_stat.submit_time = retrial[0] if len(retrial) >= 1 and type(retrial[0]) == datetime else None
                    job_stat.start_time = retrial[1] if len(retrial) >= 2 and type(retrial[1]) == datetime else None
                    job_stat.finish_time = retrial[2] if len(retrial) >= 3 and type(retrial[2]) == datetime else None
                    if job_stat.finish_time and job_stat.start_time:
                        job_stat.failed_run_time += max(job_stat.finish_time - job_stat.start_time, timedelta())
                    if job_stat.start_time and job_stat.submit_time:
                        adjusted_failed_queue = max(job_stat.start_time - job_stat.submit_time,
                                                    timedelta()) - timedelta(
                            seconds=self._queue_time_fixes.get(job.name, 0))
                        job_stat.failed_queue_time += max(adjusted_failed_queue, timedelta())
        self.jobs_stat = sorted(list(self._name_to_jobstat_dict.values()), key=lambda x: (
        x.date if x.date else datetime.now(), x.member if x.member else "", x.section if x.section else "", x.chunk))
        return self.jobs_stat

    def calculate_summary(self):
        # type: () -> StatsSummary
        stat_summary = StatsSummary()
        for job in self.jobs_stat:
            # print("{} -> {}".format(job._name, job.expected_real_consumption))
            job_stat_dict = job.get_as_dict()
            # Counter
            stat_summary.submitted_count += job_stat_dict["submittedCount"]
            stat_summary.run_count += job_stat_dict["retrialCount"]
            stat_summary.completed_count += job_stat_dict["completedCount"]
            stat_summary.failed_count += job_stat_dict["failedCount"]
            # Consumption
            stat_summary.expected_consumption += job_stat_dict["expectedConsumption"]
            stat_summary.real_consumption += job_stat_dict["realConsumption"]
            stat_summary.failed_real_consumption += job_stat_dict["failedRealConsumption"]
            # CPU Consumption
            stat_summary.expected_cpu_consumption += job_stat_dict["expectedCpuConsumption"]
            stat_summary.cpu_consumption += job_stat_dict["cpuConsumption"]
            stat_summary.failed_cpu_consumption += job_stat_dict["failedCpuConsumption"]
            stat_summary.total_queue_time += job_stat_dict["completedQueueTime"] + job_stat_dict["failedQueueTime"]
        stat_summary.calculate_consumption_percentage()
        self.summary = stat_summary

    def get_summary_as_list(self):
        return self.summary.get_as_list()

    def get_statistics(self):
        job_stat_list = self.calculate_statistics()
        return {
            "Period": {"From": str(self._start), "To": str(self._end)},
            "JobStatistics": [job.get_as_dict() for job in job_stat_list]
        }

    def make_old_format(self):
        # type: () -> None
        """ Makes old format """
        self.start_times = [job.start_time for job in self.jobs_stat]
        self.end_times = [job.finish_time for job in self.jobs_stat]
        self.queued = [timedelta2hours(job.completed_queue_time) for job in self.jobs_stat]
        self.run = [timedelta2hours(job.completed_run_time) for job in self.jobs_stat]
        self.failed_jobs = [job.failed_retrial_count for job in self.jobs_stat]
        if len(self.failed_jobs) == 0:
            self.max_fail = 0
        else:
            self.max_fail = max(self.failed_jobs)
        self.fail_run = [timedelta2hours(job.failed_run_time) for job in self.jobs_stat]
        self.fail_queued = [timedelta2hours(job.failed_queue_time) for job in self.jobs_stat]
        self.wallclocks = [job.expected_real_consumption for job in self.jobs_stat]
        if len(self.wallclocks) == 0:
            self.threshold = 0.0
        else:
            self.threshold = max(self.wallclocks)
        if len(self.queued) == 0:
            max_queue = 0.0
        else:
            max_queue = max(self.queued)
        if len(self.run) == 0:
            max_run = 0.0
        else:
            max_run = max(self.run)
        if len(self.fail_queued) == 0:
            max_fail_queue = 0.0
        else:
            max_fail_queue = max(self.fail_queued)
        if len(self.fail_run) == 0:
            max_fail_run = 0.0
        else:
            max_fail_run = max(self.fail_run)
        self.max_time = max(max_queue, max_run, max_fail_queue, max_fail_run, self.threshold)

    def build_failed_jobs_only_list(self):
        # type: () -> Dict[str, int]
        for i, job in enumerate(self.jobs_stat):
            if self.failed_jobs[i] > 0:
                self.failed_jobs_dict[job._name] = self.failed_jobs[i]
        return self.failed_jobs_dict
