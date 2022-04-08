#!/usr/bin/env python
import os
import pickle
import autosubmit_api.components.jobs.job_factory as factory 
from autosubmit_api.common.utils import JobSection, PklJob, PklJob14, is_wrapper_type_in_pkl_version, Status
from autosubmit_api.autosubmit_legacy.job.job_utils import SimpleJob
from autosubmit_api.components.experiment.configuration_facade import AutosubmitConfigurationFacade
from autosubmit_api.components.jobs.job_factory import Job
from typing import List, Dict, Set


class PklOrganizer(object):
  """ 
  Identifies dates, members, and sections. Distributes jobs into SIM, POST, TRANSFER, and CLEAN).
  SIM jobs are sorted by start times. POST, TRANSFER, and CLEAN are sorted by finish time.
  Warnings are stored in self.warnings.
  """
  
  def __init__(self, configuration_facade):  
    # type: (AutosubmitConfigurationFacade) -> None
    self.current_content = [] # type: List[PklJob]
    self.configuration_facade = configuration_facade # type: AutosubmitConfigurationFacade
    self.sim_jobs = [] # type: List[Job]
    self.post_jobs = [] # type: List[Job]
    self.transfer_jobs = [] # type: List[Job]
    self.clean_jobs = [] # type: List[Job]
    self.pkl_path = configuration_facade.pkl_path # type: str      
    self.warnings = [] # type: List[str]    
    self.dates = set() # type: Set[str]
    self.members = set() # type: Set[str]
    self.sections = set() # type: Set[str]    
    self.section_jobs_map = {} # type: Dict[str, List[Job]]
    # self.is_wrapper_type_in_pkl = is_wrapper_type_in_pkl_version(configuration_facade.get_autosubmit_version())
    self._process_pkl()   
  
  def prepare_jobs_for_performance_metrics(self):
    # type: () -> None
    self.identify_dates_members_sections()
    self.distribute_jobs()
    self._sort_distributed_jobs()    
    self._validate_current()

  def get_completed_section_jobs(self, section):
    # type: (str) -> List[Job]    
    if section in self.section_jobs_map:
      return [job for job in self.section_jobs_map[section] if job.status == Status.COMPLETED]
    else:
      return []
      # raise KeyError("Section not supported.")

  def get_simple_jobs(self, tmp_path):
    # type: (str) -> List[SimpleJob]
    """ Get jobs in pkl as SimpleJob objects."""    
    return [SimpleJob(job.name, tmp_path, job.status) for job in self.current_content]

  def _process_pkl(self):
    # type: () -> None
    if os.path.exists(self.pkl_path):
      with (open(self.pkl_path, "rb")) as openfile:                
        for item in pickle.load(openfile):
          try:    
            if len(item) == 13:
              self.current_content.append(PklJob14(*item))
            else:
              self.current_content.append(PklJob(*item))
          except Exception as ex:
            print("Exception while reading the pkl content: {}".format(str(ex)))
            return
    else:
      raise Exception("Pkl file {0} not found.".format(self.pkl_path))            
  
  def identify_dates_members_sections(self):
    # type: () -> None
    for job in self.current_content:
      if job.date and job.date not in self.dates:        
        self.dates.add(job.date)
      if job.section and job.section not in self.sections:
        self.sections.add(job.section)
      if job.member and job.member not in self.members:
        self.members.add(job.member)
      
  
  def distribute_jobs(self):
    # type: () -> None    
    for pkl_job in self.current_content:  
      if JobSection.SIM == pkl_job.section:
        self.sim_jobs.append(factory.get_job_from_factory(pkl_job.section).from_pkl(pkl_job))
      elif JobSection.POST == pkl_job.section:
        self.post_jobs.append(factory.get_job_from_factory(pkl_job.section).from_pkl(pkl_job))      
      elif JobSection.TRANSFER == pkl_job.section:
        self.transfer_jobs.append(factory.get_job_from_factory(pkl_job.section).from_pkl(pkl_job))          
      elif JobSection.CLEAN == pkl_job.section:
        self.clean_jobs.append(factory.get_job_from_factory(pkl_job.section).from_pkl(pkl_job))    
    self.section_jobs_map = {
      JobSection.SIM : self.sim_jobs,
      JobSection.POST : self.post_jobs,
      JobSection.TRANSFER : self.transfer_jobs,
      JobSection.CLEAN : self.clean_jobs
    } 

  def _sort_distributed_jobs(self):
    # type : () -> None
    """ SIM jobs are sorted by start_time  """
    self._sort_list_by_start_time(self.sim_jobs)
    self._sort_list_by_finish_time(self.post_jobs)
    self._sort_list_by_finish_time(self.transfer_jobs)
    self._sort_list_by_finish_time(self.clean_jobs)

  def _validate_current(self):
    # type : () -> None
    if len(self.get_completed_section_jobs(JobSection.SIM)) == 0:
      self._add_warning("We couldn't find COMPLETED SIM jobs in the experiment.")
    if len(self.get_completed_section_jobs(JobSection.POST)) == 0:
      self._add_warning("We couldn't find COMPLETED POST jobs in the experiment. ASYPD can't be calculated.")
    if len(self.get_completed_section_jobs(JobSection.TRANSFER)) == 0 and len(self.get_completed_section_jobs(JobSection.CLEAN)) == 0:
      self._add_warning("RSYPD | There are no TRANSFER nor CLEAN (COMPLETED) jobs in the experiment, RSYPD cannot be computed.")
    if len(self.get_completed_section_jobs(JobSection.TRANSFER)) == 0 and len(self.get_completed_section_jobs(JobSection.CLEAN)) > 0:
      self._add_warning("RSYPD | There are no TRANSFER (COMPLETED) jobs in the experiment. We will use (COMPLETED) CLEAN jobs to compute RSYPD.")
  
  def _add_warning(self, message):
    # type: (str) -> None
    self.warnings.append(message)

  def _sort_list_by_finish_time(self, jobs):
    # type: (List[Job]) -> None
    if len(jobs):
      jobs.sort(key = lambda x: x.finish, reverse=False)
  
  def _sort_list_by_start_time(self, jobs):
    # type: (List[Job]) -> None
    if len(jobs):
      jobs.sort(key = lambda x: x.start, reverse=False)

  def __repr__(self):
    return "Path: {5} \nTotal {0}\nSIM {1}\nPOST {2}\nTRANSFER {3}\nCLEAN {4}".format(
      len(self.current_content),
      len(self.sim_jobs),
      len(self.post_jobs),
      len(self.transfer_jobs),
      len(self.clean_jobs),
      self.pkl_path
    )
  
