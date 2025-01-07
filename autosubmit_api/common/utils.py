#!/usr/bin/env python
import statistics
import subprocess
import time
import datetime
import math
from collections import namedtuple
from bscearth.utils.date import date2str
from dateutil.relativedelta import relativedelta
from typing import List, Tuple

class Section:
  CONFIG = "CONFIG"
  MAIL = "MAIL"
  STORAGE = "STORAGE"
  DEFAULT = "DEFAULT"
  EXPERIMENT = "EXPERIMENT"
  PROJECT = "PROJECT"
  GIT = "GIT"
  SVN = "SVN"
  LOCAL = "LOCAL"
  PROJECT_FILES = "PROJECT_FILES"
  RERUN = "RERUN"
  JOBS = "JOBS"

class JobSection:
  SIM = "SIM"
  POST = "POST"
  TRANSFER_MEMBER = "TRANSFER_MEMBER"
  TRANSFER = "TRANSFER"
  CLEAN_MEMBER = "CLEAN_MEMBER"
  CLEAN = "CLEAN"

THRESHOLD_OUTLIER = 7
SECONDS_IN_ONE_HOUR = 3600
SECONDS_IN_A_DAY = 86400

PklJob = namedtuple('PklJob', ['name', 'id', 'status', 'priority', 'section', 'date', 'member', 'chunk', 'out_path_local', 'err_path_local', 'out_path_remote', 'err_path_remote'])
PklJob14 = namedtuple('PklJob14', ['name', 'id', 'status', 'priority', 'section', 'date', 'member', 'chunk', 'out_path_local', 'err_path_local', 'out_path_remote', 'err_path_remote', 'wrapper_type'])

def tostamp(string_date: str) -> int:
  """
  String datetime to timestamp
  """
  timestamp_value = 0
  if string_date and len(string_date) > 0:    
    try:
      timestamp_value = int(time.mktime(datetime.datetime.strptime(string_date,"%Y-%m-%d %H:%M:%S").timetuple()))
    except Exception:
      try: 
        timestamp_value = int(time.mktime(datetime.datetime.strptime(string_date,"%Y-%m-%d-%H:%M:%S").timetuple()))
      except Exception:        
        pass
  return timestamp_value



def parse_number_processors(processors_str: str) -> int:
  """ Defaults to 1 in case of error """
  if ':' in processors_str:  
    components = processors_str.split(":")
    processors = int(sum(
        [math.ceil(float(x) / 36.0) * 36.0 for x in components]))
    return processors
  else:
    try:
      processors = int(processors_str)
      return processors
    except Exception:
      return 1


def separate_job_outliers(jobs: List) -> Tuple[List, List]:
  """
  Detect job outliers and separate them from the job list. 
  Zero (and negative) run times are considered outliers.
  
  Method: https://www.ibm.com/docs/en/cognos-analytics/11.1.0?topic=terms-modified-z-score
  """
  MAD_K = 1.4826 # = 1/(CDF-1(3/4)) https://en.wikipedia.org/wiki/Median_absolute_deviation#Derivation
  MEANAD_K = 1.2533 # Ratio STD / MeanAD - Geary (1935) = 1/sqrt(2/pi)

  data_run_times = [job.run_time for job in jobs if job.run_time > 0]

  if len(data_run_times) <= 1:
    return (
       [job for job in jobs if job.run_time > 0], 
       [job for job in jobs if job.run_time <= 0]
    )
  
  mean = statistics.mean(data_run_times)
  mean_ad = statistics.mean([abs(x - mean) for x in data_run_times])

  median = statistics.median(data_run_times)
  mad = statistics.median([abs(x - median) for x in data_run_times])

  if mad == 0 and mean_ad == 0:
    return (
       [job for job in jobs if job.run_time > 0], 
       [job for job in jobs if job.run_time <= 0]
    )

  new_list = []
  outliers = []
  for job in jobs:
    if mad == 0:
       modified_z_score = (job.run_time - median) / (MEANAD_K*mean_ad)
    else:
      modified_z_score = (job.run_time - median) / (MAD_K*mad)

    if math.fabs(modified_z_score) <= THRESHOLD_OUTLIER and job.run_time > 0:
      new_list.append(job)
    else:
      outliers.append(job)

  return (new_list, outliers)


def get_jobs_with_no_outliers(jobs: List) -> List:
  """
  Returns a list of jobs without outliers
  """  
  return separate_job_outliers(jobs)[0]


def date_plus(date, chunk_unit, chunk, chunk_size=1):
  if not date:
    return (None, None)
  previous_date = date
  if chunk is not None and chunk_unit is not None:
      chunk_previous = (chunk - 1) * (chunk_size)
      chunk = chunk * chunk_size
      if (chunk_unit == "month"):
          date = date + relativedelta(months=+chunk)
          previous_date = previous_date + \
              relativedelta(months=+chunk_previous)
      elif (chunk_unit == "year"):
          date = date + relativedelta(years=+chunk)
          previous_date = previous_date + \
              relativedelta(years=+chunk_previous)
      elif (chunk_unit == "day"):
          date = date + datetime.timedelta(days=+chunk)
          previous_date = previous_date + \
              datetime.timedelta(days=+chunk_previous)
      elif (chunk_unit == "hour"):
          date = date + datetime.timedelta(days=+int(chunk / 24))
          previous_date = previous_date + \
              datetime.timedelta(days=+int(chunk_previous / 24))
  return _date_to_str_space(date2str(previous_date)), _date_to_str_space(date2str(date))

def _date_to_str_space(date_str):
  if (len(date_str) == 8):
      return str(date_str[0:4] + " " + date_str[4:6] + " " + date_str[6:])
  else:
      return ""

def get_average_total_time(jobs: List[object]) -> float:
  """ Job has attribute total_time (See JobFactory)"""
  if len(jobs):
    average = sum(job.total_time for job in jobs)/ len(jobs)
    return round(average, 4)
  return 0.0

def parse_version_number(str_version: str) -> Tuple[int, int]:
  if len(str_version.strip()) > 0:
    version_split = str_version.split('.')
    main = int(version_split[0])
    secondary = int(version_split[1])
    return (main, secondary)
  return (0, 0)

def is_version_historical_ready(str_version):
  main, secondary = parse_version_number(str_version)
  if (main >= 3 and secondary >= 13) or (main >= 4): # 3.13 onwards.
    return True
  return False

def is_wrapper_type_in_pkl_version(str_version):
  main, secondary = parse_version_number(str_version)
  if (main >= 3 and secondary >= 14) or (main >= 4): # 3.14 onwards.
    return True
  return False

def get_current_timestamp() -> int:
  return int(time.time())


def get_experiments_from_folder(root_folder: str) -> List[str]:     
  currentDirectories = subprocess.Popen(['ls', '-t', root_folder], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
  stdOut, _ = currentDirectories.communicate()
  folders = stdOut.split()      
  return [expid for expid in folders if len(expid) == 4]


def get_local_tz():
  return datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo


def timestamp_to_datetime_format(timestamp: int) -> str:
  """
  Formats a timestamp to a iso format datetime string with timezone information.
  """
  try:
    if timestamp and timestamp > 0:
      return datetime.datetime.fromtimestamp(timestamp, tz=get_local_tz()).isoformat()
  except Exception as exp:    
    print(("Timestamp {} cannot be converted to datetime string. {}".format(str(timestamp), str(exp))))
    return None
  return None

def datechunk_to_year(chunk_unit: int, chunk_size: int) -> float:
    """
    Gets chunk unit and size and returns the value in years

    :return: years  
    :rtype: float
    """    
    chunk_size = chunk_size * 1.0
    # options = ["year", "month", "day", "hour"]
    if (chunk_unit == "year"):
        return chunk_size
    elif (chunk_unit == "month"):
        return chunk_size / 12
    elif (chunk_unit == "day"):
        return chunk_size / 365
    elif (chunk_unit == "hour"):
        return chunk_size / 8760
    else:
        return 0.0


class Status:
    """
    Class to handle the status of a job
    """
    WAITING = 0
    READY = 1
    SUBMITTED = 2
    QUEUING = 3
    RUNNING = 4
    COMPLETED = 5
    HELD = 6
    PREPARED = 7
    SKIPPED = 8
    DELAYED = 9
    FAILED = -1
    UNKNOWN = -2
    SUSPENDED = -3
    #######
    # Note: any change on constants must be applied on the dict below!!!
    VALUE_TO_KEY = {-3: 'SUSPENDED', -2: 'UNKNOWN', -1: 'FAILED', 0: 'WAITING', 1: 'READY',
                    2: 'SUBMITTED', 3: 'QUEUING', 4: 'RUNNING', 5: 'COMPLETED', 6: 'HELD', 7: 'PREPARED', 8: 'SKIPPED', 9: 'DELAYED'}
    STRING_TO_CODE = {v: k for k, v in list(VALUE_TO_KEY.items())}

    def retval(self, value):
        return getattr(self, value)


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    # Status Colors
    UNKNOWN = '\033[37;1m'
    WAITING = '\033[37m'

    READY = '\033[36;1m'
    SUBMITTED = '\033[36m'
    QUEUING = '\033[35;1m'
    RUNNING = '\033[32m'
    COMPLETED = '\033[33m'
    SKIPPED = '\033[33m'
    PREPARED = '\033[34;2m'
    HELD = '\033[34;1m'
    FAILED = '\033[31m'
    SUSPENDED = '\033[31;1m'
    CODE_TO_COLOR = {-3: SUSPENDED, -2: UNKNOWN, -1: FAILED, 0: WAITING, 1: READY,
                     2: SUBMITTED, 3: QUEUING, 4: RUNNING, 5: COMPLETED, 6: HELD, 7: PREPARED, 8: SKIPPED}