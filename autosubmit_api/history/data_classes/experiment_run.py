#!/usr/bin/env python

# Copyright 2015-2020 Earth Sciences Department, BSC-CNS
# This file is part of Autosubmit.

# Autosubmit is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Autosubmit is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Autosubmit.  If not, see <http://www.gnu.org/licenses/>.

import json
import autosubmitAPIwu.common.utils as common_utils
import autosubmitAPIwu.performance.utils as PUtils
from autosubmitAPIwu.history.utils import get_current_datetime_if_none
from autosubmitAPIwu.history.data_classes.job_data import JobData
from autosubmitAPIwu.components.jobs.job_factory import SimJob
from typing import List, Dict, Tuple
class ExperimentRun(object):
  """
  Class that represents an experiment run
  """
  def __init__(self, run_id, created=None, modified=None, start=0, finish=0, chunk_unit="NA", chunk_size=0, completed=0, total=0, failed=0, queuing=0, running=0, submitted=0, suspended=0, metadata=""):
    self.run_id = run_id
    self.created = get_current_datetime_if_none(created) 
    self.modified = get_current_datetime_if_none(modified) # Added on DB 16
    self.start = start
    self.finish = finish
    self.chunk_unit = chunk_unit # type: str
    self.chunk_size = chunk_size # type: int
    self.submitted = submitted # type: int
    self.queuing = queuing # type: int
    self.running = running # type: int
    self.completed = completed # type: int
    self.failed = failed # type: int
    self.total = total # type: int
    self.suspended = suspended # type: int
    self.metadata = metadata    

  @property
  def created_timestamp(self):
    return common_utils.tostamp(self.created)

  @property
  def modified_timestamp(self):    
    return common_utils.tostamp(self.modified)

  def get_wrapper_type(self):
    if self.metadata:              
      data = json.loads(self.metadata)                        
      wrapper_section = data["conf"].get("wrapper", None)
      if wrapper_section:      
        wrapper_type = wrapper_section.get("TYPE", None)
        if wrapper_type:
          return wrapper_type
    return None
  
  def getSYPD(self, job_list):
    # type: (List[JobData]) -> float
    outlier_free_list = []
    if job_list:
        performance_jobs = [SimJob.from_job_data_dc(job_data_dc) for job_data_dc in job_list]
        outlier_free_list = common_utils.get_jobs_with_no_outliers(performance_jobs)
    # print("{} -> {}".format(self.run_id, len(outlier_free_list)))
    if len(outlier_free_list) > 0:
        years_per_sim = PUtils.datechunk_to_year(self.chunk_unit, self.chunk_size)
        # print(self.run_id)
        # print(years_per_sim)
        seconds_per_day = 86400
        number_SIM = len(outlier_free_list)
        # print(len(job_list))
        total_run_time = sum(job.run_time for job in outlier_free_list)
        # print("run {3} yps {0} n {1} run_time {2}".format(years_per_sim, number_SIM, total_run_time, self.run_id))
        if total_run_time > 0:                
            return round((years_per_sim * number_SIM * seconds_per_day) / total_run_time, 2)           
    return None

  def getASYPD(self, job_sim_list, job_post_list, run_id_wrapper_code_to_job_dcs):
    # type: (List[JobData], List[JobData], Dict[Tuple[int, int], List[JobData]]) -> float
    SIM_no_outlier_list = []
    if job_sim_list and len(job_sim_list) > 0:
        performance_jobs = [SimJob.from_job_data_dc(job_data_dc) for job_data_dc in job_sim_list]
        SIM_no_outlier_list = common_utils.get_jobs_with_no_outliers(performance_jobs)
        valid_names = set([job.name for job in SIM_no_outlier_list])
        job_sim_list = [job for job in job_sim_list if job.job_name in valid_names]

    if job_sim_list and len(job_sim_list) > 0 and job_post_list and len(job_post_list) > 0:
        years_per_sim = PUtils.datechunk_to_year(self.chunk_unit, self.chunk_size)
        seconds_per_day = 86400
        number_SIM = len(job_sim_list)
        number_POST = len(job_post_list)        
        average_POST = round(sum(job.queuing_time_considering_package(run_id_wrapper_code_to_job_dcs.get((job.run_id, job.rowtype), [])) + job.running_time for job in job_post_list) / number_POST, 2)

        sum_SIM = round(sum(job.queuing_time_considering_package(run_id_wrapper_code_to_job_dcs.get((job.run_id, job.rowtype), [])) + job.running_time for job in job_sim_list), 2)
        if (sum_SIM + average_POST) > 0:
            return round((years_per_sim * number_SIM * seconds_per_day) / (sum_SIM + average_POST), 2)
    return None

  @classmethod
  def from_model(cls, row):
    """ Build ExperimentRun from ExperimentRunRow """
    row_dict = row._asdict()    
    experiment_run = cls(0)
    experiment_run.run_id = row_dict.get('run_id', 0)
    experiment_run.created = get_current_datetime_if_none(row_dict.get('created', None))
    experiment_run.modified = get_current_datetime_if_none(row_dict.get('modified', None))
    experiment_run.start = int(row_dict.get('start', 0))
    experiment_run.finish = int(row_dict.get('finish', 0))
    experiment_run.chunk_unit = row_dict.get('chunk_unit', None)
    experiment_run.chunk_size = row_dict.get('chunk_size', None)
    experiment_run.completed = int(row_dict.get('completed', 0))
    experiment_run.total = row_dict.get('total', 0)
    experiment_run.failed = row_dict.get('failed', 0)
    experiment_run.queuing = row_dict.get('queuing', 0)
    experiment_run.running = row_dict.get('running', 0)
    experiment_run.submitted = row_dict.get('submitted', 0)
    experiment_run.suspended = int(row_dict.get('suspended', 0))
    experiment_run.metadata = row_dict.get('metadata', "")
    return experiment_run
  