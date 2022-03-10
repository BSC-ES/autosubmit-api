#!/usr/bin/env python
from autosubmit_api.autosubmit_legacy.job.job_list import JobList
from autosubmit_api.database.db_jobdata import JobDataStructure, JobRow
from autosubmit_api.components.experiment.configuration_facade import AutosubmitConfigurationFacade
from autosubmit_api.components.experiment.pkl_organizer import PklOrganizer
from autosubmit_api.config.basicConfig import BasicConfig
from autosubmit_api.autosubmit_legacy.job.job_utils import datechunk_to_year
from typing import List, Dict
from autosubmit_api.components.jobs.job_factory import Job

class JobListHelper(object):
  """ Loads time (queuing runnning) and packages. """
  def __init__(self, expid, configuration_facade, pkl_organizer, basic_config):
    # type: (str, AutosubmitConfigurationFacade, PklOrganizer, BasicConfig) -> None
    self.basic_config = basic_config # type: BasicConfig
    self.configuration_facade = configuration_facade # type: AutosubmitConfigurationFacade
    self.pkl_organizer = pkl_organizer # type: PklOrganizer
    self.job_to_package = {} # type: Dict[str, str]    
    self.package_to_jobs = {} # type: Dict[str, List[str]]
    self.package_to_package_id = {} # type: Dict[str, str]
    self.package_to_symbol = {} # type: Dict[str, str]
    self.job_name_to_job_row = {} # type: Dict[str, JobRow]
    self.job_running_time_to_text = {} # type: Dict[str, str]
    self._run_id_to_run_object = {} # type: Dict
    self.warning_messages = [] # type: List
    self.expid = expid # type: str
    self.simple_jobs = self.pkl_organizer.get_simple_jobs(self.configuration_facade.tmp_path)
    self._initialize_main_values()

  def _initialize_main_values(self):
    # type: () -> None
    self.job_to_package, self.package_to_jobs, self.package_to_package_id, self.package_to_symbol = JobList.retrieve_packages(self.basic_config, self.expid)    
    self.job_name_to_job_row, self.job_running_time_to_text, self.warning_messages  = JobList.get_job_times_collection(
                self.basic_config, self.simple_jobs, self.expid, self.job_to_package, self.package_to_jobs, timeseconds=True)      
        
  def update_with_timedata(self, section_jobs):
    # type: (List[Job]) -> None
    """ Update Job information with JobRow (time) data from Historical Database (Or as_times information) """    
    for job in section_jobs:
      # if job.name in self.job_name_to_job_row:
      job.update_from_jobrow(self.job_name_to_job_row.get(job.name, None))
  
  def update_with_yps_per_run(self, section_jobs):
    # type: (List[Job]) -> None
    """ Update Job information with Historical Run information: years_per_sim  """    
    self._retrieve_current_experiment_runs_required(section_jobs)
    for job in section_jobs:
      yps_per_run = self._get_yps_per_run_id(job.run_id)
      if yps_per_run > 0.0:
        job.set_years_per_sim(yps_per_run)
  
  def _retrieve_current_experiment_runs_required(self, section_jobs):
    # type: (List[Job]) -> None
    for job in section_jobs:
      self._add_experiment_run(job.run_id)

  def _get_yps_per_run_id(self, run_id):
    # type: (int) -> float
    experiment_run = self._run_id_to_run_object.get(run_id, None)
    if experiment_run:
      return datechunk_to_year(experiment_run.chunk_unit, experiment_run.chunk_size)
    else:
      return 0.0
  
  def _add_experiment_run(self, run_id):
    # type: (int) -> None
    if run_id and run_id not in self._run_id_to_run_object:
      self._run_id_to_run_object[run_id] = JobDataStructure(self.expid, self.basic_config).get_experiment_run_by_id(run_id)





    


