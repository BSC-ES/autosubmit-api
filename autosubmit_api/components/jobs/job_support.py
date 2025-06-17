import os
from datetime import datetime
from typing import List

from bscearth.utils.date import parse_date

from autosubmit_api.common.utils import LOCAL_TZ
from autosubmit_api.components.jobs.job_factory import Job
from autosubmit_api.components.jobs.utils import is_a_completed_retrial
from autosubmit_api.config.basicConfig import APIBasicConfig


class TotalStatsPosition:
  SUBMIT = 0
  START = 1
  FINISH = 2
  STATUS = 3

class JobSupport:
  """
  Provides the methods to get the retrials of a job from the TOTAL_STATS files.
  """
  def __init__(self, expid: str, job: Job, basic_config: APIBasicConfig):
    self.expid = expid
    self.job = job
    self.basic_config = basic_config
    self.complete_tmp_path = os.path.join(self.basic_config.LOCAL_ROOT_DIR, self.expid, self.basic_config.LOCAL_TMP_DIR)
    self.total_stats_file_name = "{}_TOTAL_STATS".format(self.job.name)
    self.complete_total_stats_path = os.path.join(self.complete_tmp_path, self.total_stats_file_name)

  def get_last_retrials(self) -> List[List[datetime]]:
    retrials_list = []
    if os.path.exists(self.complete_total_stats_path):
        already_completed = False
        for retrial in reversed(open(self.complete_total_stats_path).readlines()):
            retrial_fields = retrial.split()
            if is_a_completed_retrial(retrial_fields):
                if already_completed:
                    break
                already_completed = True
            retrial_dates = [parse_date(y).replace(tzinfo=LOCAL_TZ) if y != 'COMPLETED' and y != 'FAILED' else y for y in retrial_fields]
            retrials_list.insert(0, retrial_dates)
    return retrials_list

  def check_started_after(self, start_datetime: datetime) -> bool:
    """
    Checks if the job started after the given date
    """
    if any(date_retrial > start_datetime for date_retrial in self.check_retrials_start_time()):
        return True
    else:
        return False

  def check_running_after(self, finish_datetime: datetime) -> bool:
    """
    Checks if the job was running after the given date
    """
    if any(date_end > finish_datetime for date_end in self.check_retrials_end_time()):
        return True
    else:
        return False

  def check_retrials_start_time(self) -> List[datetime]:
    """
    Returns list of start datetime for retrials from total stats file
    """
    return self._get_from_total_stats(TotalStatsPosition.START)

  def check_retrials_end_time(self) -> List[datetime]:
    """
    Returns list of end datetime for retrials from total stats file
    """
    return self._get_from_total_stats(TotalStatsPosition.FINISH)

  def _get_from_total_stats(self, index) -> List[datetime]:
    """
    Returns list of values from given column index position in TOTAL_STATS file associated to job
    """
    result = []
    if os.path.exists(self.complete_total_stats_path):
        f = open(self.complete_total_stats_path)
        lines = f.readlines()
        for line in lines:
            fields = line.split()
            if len(fields) >= index + 1:
                formatted_date = parse_date(fields[index]).replace(tzinfo=LOCAL_TZ)
                result.append(formatted_date)
    return result