#!/usr/bin/env python
import os
import pickle
import subprocess
import time
import datetime
import math
import numpy as np
from collections import namedtuple
from bscearth.utils.date import date2str
from dateutil.relativedelta import *
from typing import List

class JobSection:
  SIM = "SIM"
  POST = "POST"
  TRANSFER_MEMBER = "TRANSFER_MEMBER"
  TRANSFER = "TRANSFER"
  CLEAN_MEMBER = "CLEAN_MEMBER"
  CLEAN = "CLEAN"

THRESHOLD_OUTLIER = 2
SECONDS_IN_ONE_HOUR = 3600
SECONDS_IN_A_DAY = 86400

PklJob = namedtuple('PklJob', ['name', 'id', 'status', 'priority', 'section', 'date', 'member', 'chunk', 'out_path_local', 'err_path_local', 'out_path_remote', 'err_path_remote'])
PklJob14 = namedtuple('PklJob14', ['name', 'id', 'status', 'priority', 'section', 'date', 'member', 'chunk', 'out_path_local', 'err_path_local', 'out_path_remote', 'err_path_remote', 'wrapper_type'])

def tostamp(string_date):
  # type: (str) -> int
  """
  String datetime to timestamp
  """
  timestamp_value = 0
  if string_date and len(string_date) > 0:    
    try:
      timestamp_value = int(time.mktime(datetime.datetime.strptime(string_date,"%Y-%m-%d %H:%M:%S").timetuple()))
    except:
      try: 
        timestamp_value = int(time.mktime(datetime.datetime.strptime(string_date,"%Y-%m-%d-%H:%M:%S").timetuple()))
      except:        
        pass
  return timestamp_value



def parse_number_processors(processors_str):
  """ Defaults to 1 in case of error """
  # type: (str) -> int
  if ':' in processors_str:  
    components = processors_str.split(":")
    processors = int(sum(
        [math.ceil(float(x) / 36.0) * 36.0 for x in components]))
    return processors
  else:
    try:
      processors = int(processors_str)
      return processors
    except:
      return 1

def get_jobs_with_no_outliers(jobs):
  """ Detects outliers and removes them from the returned list """  
  new_list = []
  data_run_times = [job.run_time for job in jobs]
  # print(data_run_times)
  if len(data_run_times) == 0:
    return jobs  
  
  mean = np.mean(data_run_times)
  std = np.std(data_run_times)
  
  # print("mean {0} std {1}".format(mean, std))
  if std == 0:
    return jobs

  for job in jobs:
    z_score = (job.run_time - mean) / std
    # print("{0} {1} {2}".format(job.name, np.abs(z_score), job.run_time))
    if np.abs(z_score) <= THRESHOLD_OUTLIER and job.run_time > 0:
      new_list.append(job)
    # else:
    #   print(" OUTLIED {0} {1} {2}".format(job.name, np.abs(z_score), job.run_time))  
  return new_list

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

def get_average_total_time(jobs):
  # type: (List[object]) -> float
  """ Job has attribute total_time (See JobFactory)"""
  if len(jobs):
    average = sum(job.total_time for job in jobs)/ len(jobs)
    return round(average, 4)
  return 0.0

def parse_version_number(str_version):
  # type : (str) -> Tuple[int, int]
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

def get_current_timestamp():
  # type: () -> int
  return int(time.time())


def get_experiments_from_folder(root_folder):     
  # type: (str) -> List[str]
  currentDirectories = subprocess.Popen(['ls', '-t', root_folder], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
  stdOut, _ = currentDirectories.communicate()
  folders = stdOut.split()      
  return [expid for expid in folders if len(expid) == 4]

def timestamp_to_datetime_format(timestamp):
  # type: (int) -> str
  """ %Y-%m-%d %H:%M:%S """
  try:
    if timestamp and timestamp > 0:
      return datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
  except Exception as exp:    
    print("Timestamp {} cannot be converted to datetime string. {}".format(str(timestamp), str(exp)))
    return None
  return None

def datechunk_to_year(chunk_unit, chunk_size):
    # type: (str, int) -> float
    """
    Gets chunk unit and size and returns the value in years

    :return: years  
    :rtype: float
    """    
    chunk_size = chunk_size * 1.0
    options = ["year", "month", "day", "hour"]
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
    FAILED = -1
    UNKNOWN = -2
    SUSPENDED = -3
    #######
    # Note: any change on constants must be applied on the dict below!!!
    VALUE_TO_KEY = {-3: 'SUSPENDED', -2: 'UNKNOWN', -1: 'FAILED', 0: 'WAITING', 1: 'READY',
                    2: 'SUBMITTED', 3: 'QUEUING', 4: 'RUNNING', 5: 'COMPLETED', 6: 'HELD', 7: 'PREPARED', 8: 'SKIPPED'}
    STRING_TO_CODE = {v: k for k, v in VALUE_TO_KEY.items()}

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