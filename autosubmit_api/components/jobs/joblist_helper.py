#!/usr/bin/env python
from autosubmit_api.autosubmit_legacy.job.job_list import JobList
from autosubmit_api.common.utils import datechunk_to_year
from autosubmit_api.components.jobdata import JobDataStructure, JobRow
from autosubmit_api.components.experiment.configuration_facade import AutosubmitConfigurationFacade
from autosubmit_api.components.experiment.pkl_organizer import PklOrganizer
from autosubmit_api.config.basicConfig import APIBasicConfig
from typing import List, Dict
from autosubmit_api.components.jobs.job_factory import Job
from autosubmit_api.persistance.job_package_reader import JobPackageReader

class JobListHelper(object):
  """ Loads time (queuing runnning) and packages. Applies the fix for queue time of jobs in wrappers. """
  def __init__(self, expid, configuration_facade: AutosubmitConfigurationFacade, pkl_organizer: PklOrganizer, basic_config: APIBasicConfig):
    self.basic_config: APIBasicConfig = basic_config
    self.configuration_facade: AutosubmitConfigurationFacade = configuration_facade
    self.pkl_organizer: PklOrganizer = pkl_organizer
    self.job_to_package: Dict[str, str] = {}
    self.package_to_jobs: Dict[str, List[str]] = {}
    self.package_to_package_id: Dict[str, str] = {}
    self.package_to_symbol: Dict[str, str] = {}
    self.job_name_to_job_row: Dict[str, JobRow] = {}
    self.job_running_time_to_text: Dict[str, str] = {}
    self._run_id_to_run_object: Dict = {}
    self.warning_messages: List = []
    self.expid: str = expid
    self.simple_jobs = self.pkl_organizer.get_simple_jobs(self.configuration_facade.tmp_path)
    self._initialize_main_values()

  def _initialize_main_values(self):
    job_package_reader = JobPackageReader(self.expid)
    try:
      job_package_reader.read()
      self.job_to_package = job_package_reader.job_to_package
      self.package_to_jobs = job_package_reader.package_to_jobs
      self.package_to_package_id = job_package_reader.package_to_package_id
      self.package_to_symbol = job_package_reader.package_to_symbol
    except Exception:
      self.warning_messages.append("Failed to read job_packages")
      
    self.job_name_to_job_row, self.job_running_time_to_text, self.warning_messages  = JobList.get_job_times_collection(
                self.basic_config, self.simple_jobs, self.expid, self.job_to_package, self.package_to_jobs, timeseconds=True)

  def update_with_timedata(self, section_jobs: List[Job]):
    """ Update Job information with JobRow (time) data from Historical Database (Or as_times information) """
    for job in section_jobs:
      # if job.name in self.job_name_to_job_row:
      job.update_from_jobrow(self.job_name_to_job_row.get(job.name, None))

  def update_with_yps_per_run(self, section_jobs: List[Job]):
    """ Update Job information with Historical Run information: years_per_sim  """
    self._retrieve_current_experiment_runs_required(section_jobs)
    for job in section_jobs:
      yps_per_run = self._get_yps_per_run_id(job.run_id)
      if yps_per_run > 0.0:
        job.set_years_per_sim(yps_per_run)

  def _retrieve_current_experiment_runs_required(self, section_jobs: List[Job]):
    for job in section_jobs:
      self._add_experiment_run(job.run_id)

  def _get_yps_per_run_id(self, run_id: int) -> float:
    experiment_run = self._run_id_to_run_object.get(run_id, None)
    if experiment_run:
      return datechunk_to_year(experiment_run.chunk_unit, experiment_run.chunk_size)
    else:
      return 0.0

  def _add_experiment_run(self, run_id: int):
    if run_id and run_id not in self._run_id_to_run_object:
      self._run_id_to_run_object[run_id] = JobDataStructure(self.expid, self.basic_config).get_experiment_run_by_id(run_id)
