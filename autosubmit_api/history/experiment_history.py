#!/usr/bin/python

# Copyright 2015-2020 Earth Sciences Department, BSC-CNS
# This file is part of Autosubmit.

# Autosubmit is free software: you can redistribute it and/or modify
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# it under the terms of the GNU General Public License as published by
# Autosubmit is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of

# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Autosubmit.  If not, see <http://www.gnu.org/licenses/>.
import traceback
from autosubmit_api.history.database_managers import database_models as Models
from autosubmit_api.performance import utils as PUtils
from autosubmit_api.history.database_managers.experiment_history_db_manager import ExperimentHistoryDbManager
from autosubmit_api.history.data_classes.job_data import JobData
from autosubmit_api.history.data_classes.experiment_run import ExperimentRun
from autosubmit_api.history.internal_logging import Logging
from autosubmit_api.config.basicConfig import APIBasicConfig
from typing import List, Dict, Optional, Tuple, Any

SECONDS_WAIT_PLATFORM = 60

class ExperimentHistory():
  def __init__(self, expid: str, basic_config: APIBasicConfig, experiment_history_db_manager: ExperimentHistoryDbManager, logger: Logging) -> None:
    self.expid = expid
    self._log = logger
    self.basic_config = basic_config
    self._job_data_dir_path = basic_config.JOBDATA_DIR
    self._historiclog_dir_path = basic_config.HISTORICAL_LOG_DIR
    try:
      self.manager = experiment_history_db_manager
    except Exception as exp:
      self._log.log(str(exp), traceback.format_exc())
      self.manager = None

  def get_historic_job_data(self, job_name: str) -> List[Dict[str, Any]]:
    result = []
    all_job_data_dcs = self.manager.get_job_data_dcs_by_name(job_name)
    post_job_data_dcs = self.manager.get_job_data_dcs_COMPLETED_by_section("POST")

    run_id_to_POST_job_data_dcs: Dict[int, List[JobData]] = {}
    run_id_wrapper_code_to_job_data_dcs: Dict[Tuple[int, int], List[JobData]] = {}
    for job_data_dc in post_job_data_dcs:
      run_id_to_POST_job_data_dcs.setdefault(job_data_dc.run_id, []).append(job_data_dc)
      if (job_data_dc.run_id, job_data_dc.rowtype) not in run_id_wrapper_code_to_job_data_dcs:
        run_id_wrapper_code_to_job_data_dcs[(job_data_dc.run_id, job_data_dc.rowtype)] = self.manager.get_job_data_dc_COMPLETED_by_wrapper_run_id(job_data_dc.rowtype, job_data_dc.run_id)

    run_id_to_experiment_run_involved: Dict[int, ExperimentRun] = {}
    for job_data_dc in all_job_data_dcs:
      if job_data_dc.run_id not in run_id_to_experiment_run_involved:
        run_id_to_experiment_run_involved[job_data_dc.run_id] = self.manager.get_experiment_run_by_id(job_data_dc.run_id)
      if (job_data_dc.run_id, job_data_dc.rowtype) not in run_id_wrapper_code_to_job_data_dcs:
        run_id_wrapper_code_to_job_data_dcs[(job_data_dc.run_id, job_data_dc.rowtype)] = self.manager.get_job_data_dc_COMPLETED_by_wrapper_run_id(job_data_dc.rowtype, job_data_dc.run_id)

    for job_data_dc in all_job_data_dcs:
      experiment_run = run_id_to_experiment_run_involved.get(job_data_dc.run_id, None)
      jobs_in_package = run_id_wrapper_code_to_job_data_dcs.get((job_data_dc.run_id, job_data_dc.rowtype), [])
      if experiment_run:
        average_post_time = 0.0
        post_job_data_dcs_in_run = run_id_to_POST_job_data_dcs.get(job_data_dc.run_id, [])
        if len(post_job_data_dcs_in_run) > 0:
          for post_job_data_dc in post_job_data_dcs_in_run:
            if post_job_data_dc.rowtype > Models.RowType.NORMAL:
              jobs_in_package_for_post_job = run_id_wrapper_code_to_job_data_dcs.get((post_job_data_dc.run_id, post_job_data_dc.rowtype), [])
              average_post_time += post_job_data_dc.queuing_time_considering_package(jobs_in_package_for_post_job)
            else:
              average_post_time += (post_job_data_dc.queuing_time + post_job_data_dc.running_time)
          average_post_time = average_post_time/len(post_job_data_dcs_in_run)
      result.append({"counter": job_data_dc.counter,
                      "created": job_data_dc.created,
                      "submit": job_data_dc.submit_datetime_str,
                      "start": job_data_dc.start_datetime_str,
                      "finish": job_data_dc.finish_datetime_str,
                      "queue_time": job_data_dc.delta_queueing_time_considering_package(jobs_in_package),
                      "run_time": job_data_dc.delta_running_time,
                      "ncpus": job_data_dc.ncpus,
                      "wallclock": job_data_dc.wallclock,
                      "qos": job_data_dc.qos,
                      "platform": job_data_dc.platform,
                      "job_id": job_data_dc.job_id,
                      "nodes": job_data_dc.nnodes,
                      "energy": job_data_dc.energy,
                      "status": job_data_dc.status,
                      "PSYPD": PUtils.calculate_PSYPD_perjob(experiment_run.chunk_unit, experiment_run.chunk_size, job_data_dc.chunk, job_data_dc.queuing_time_considering_package(jobs_in_package) + job_data_dc.running_time, average_post_time, job_data_dc.status_code) if experiment_run else "NA",
                      "ASYPD": PUtils.calculate_PSYPD_perjob(experiment_run.chunk_unit, experiment_run.chunk_size, job_data_dc.chunk, job_data_dc.queuing_time_considering_package(jobs_in_package) + job_data_dc.running_time, average_post_time, job_data_dc.status_code) if experiment_run else "NA",
                      "SYPD": PUtils.calculate_SYPD_perjob(experiment_run.chunk_unit, experiment_run.chunk_size, job_data_dc.chunk, job_data_dc.running_time, job_data_dc.status_code) if experiment_run else "NA",
                      "run_id": job_data_dc.run_id,
                      "run_created": experiment_run.created if experiment_run else "NA",
                      "out": job_data_dc.out,
                      "err": job_data_dc.err
                      })
    return result
  
  def get_experiment_runs(self) -> List[ExperimentRun]:
    """
    Gets all the experiment runs
    """
    return self.manager.get_experiment_runs_dcs()

  def get_all_jobs_last_run_dict(self) -> Dict[str, Optional[ExperimentRun]]:
    """
    Gets the last run of all jobs in the experiment
    """
    # Map all experiment runs by run_id
    runs = self.manager.get_experiment_runs_dcs()
    runs_dict = {run.run_id: run for run in runs}

    # Map last jobs data by job name
    last_jobs_data = self.manager.get_all_last_job_data_dcs()
    return {
      job_data.job_name: runs_dict.get(job_data.run_id)
      for job_data in last_jobs_data
    }