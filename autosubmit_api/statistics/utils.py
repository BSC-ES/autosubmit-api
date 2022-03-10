#!/bin/env/python

from autosubmit_api.autosubmit_legacy.job.job import Job
from datetime import datetime, timedelta
from autosubmit_api.common.utils import Status
from typing import List, Tuple

# from log.log import AutosubmitCritical

def filter_by_section(jobs, section):
  # type: (List[Job], str) -> List[Job]
  """ Filter jobs by provided sections """
  if section and section != "Any":
    return [job for job in jobs if job.section == section]
  return jobs
  
def discard_ready_and_waiting(jobs):
  if jobs and len(jobs) > 0:
    return [job for job in jobs if job.status not in [Status.READY, Status.WAITING]]
  return jobs

def filter_by_time_period(jobs, hours_span):
  # type: (List[Job], int) -> Tuple[List[Job], datetime, datetime]
  current_time = datetime.now().replace(second=0, microsecond=0)
  start_time = None
  if hours_span:
    if hours_span <= 0:
      raise Exception("{} is not a valid input for the statistics filter -fp.".format(hours_span))
    start_time = current_time - timedelta(hours=int(hours_span))
    return ([job for job in jobs if job.check_started_after(start_time) or job.check_running_after(start_time)], start_time, current_time)
  return (jobs, start_time, current_time)


def timedelta2hours(deltatime):
    # type: (timedelta) -> float
    return deltatime.days * 24 + deltatime.seconds / 3600.0
