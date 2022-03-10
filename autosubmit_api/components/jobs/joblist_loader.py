#!/usr/bin/env python

import os
from fnmatch import fnmatch
from autosubmit_api.components.jobs.joblist_helper import JobListHelper
from autosubmit_api.components.experiment.pkl_organizer import PklOrganizer
from autosubmit_api.components.experiment.configuration_facade import AutosubmitConfigurationFacade
from autosubmit_api.components.jobs.job_factory import StandardJob, Job
from autosubmit_api.database.db_structure import get_structure
from autosubmit_api.autosubmit_legacy.job.job_common import Status
from bscearth.utils.date import date2str, parse_date
from typing import Dict, List, Set, Tuple
# Builder Imports
from autosubmit_api.config.config_common import AutosubmitConfig
from bscearth.utils.config_parser import ConfigParserFactory
from autosubmit_api.config.basicConfig import BasicConfig

class JobListLoader(object):
  """ Class that manages loading the list of jobs from the pkl. Adds other resources. """
  def __init__(self, expid, joblist_helper):
    # type: (str, JobListHelper) -> None
    self.expid = expid
    self.joblist_helper = joblist_helper
    self.configuration_facade = self.joblist_helper.configuration_facade 
    self.pkl_organizer = self.joblist_helper.pkl_organizer    
    self._jobs = [] # type: List[Job]
    self._structure_adjacency = {} # type: Dict[str, List[str]]
    self._job_dictionary = {} # type: Dict[str, Job]
    

  def load_jobs(self):    
    """ Reads Pkl -> Makes StandardJobs -> Loads Adjacency -> Loads Packages -> Loads Q+R times -> Finds Logs -> Updates StandardJobs with Q+R times and Packages """
    self.pkl_organizer.identify_dates_members_sections()    
    self._jobs = [StandardJob().from_pkl(pkl_job) for pkl_job in self.pkl_organizer.current_content]
    self.load_existing_structure_adjacency()
    self.distribute_adjacency_into_jobs()
    self.assign_packages_to_jobs()
    self.assign_running_time_text_to_jobs()
    self.assign_configuration_data_to_jobs()
    self.joblist_helper.update_with_timedata(self._jobs)
    self.joblist_helper.update_with_yps_per_run(self._jobs)    
    self._generate_job_dictionary()
    self._update_job_logs()

  def are_these_in_same_package(self, *names):
    # type: (List[str]) -> bool
    packages = set()
    for job_name in names:
      package_name = self.joblist_helper.job_to_package.get(job_name, None)
      if package_name is None:
        return False
      packages.add(package_name)
    if len(packages) == 1:
      return True
    return False 
  
  def are_these_in_same_level(self, *names):
    level = set()
    for job_name in names:
      level.add(self.job_dictionary[job_name].level)
    return len(level) == 1


  def validate_job_list_configuration(self):
    """ No repeated dates """
    dates = self.dates
    if len(dates) != len(set(dates)):
      raise Exception("Repeated dates found. Autosubmit API can't generate a representation for this configuration. Review your configuration files.")

  def get_all_jobs_in_package(self, package_name):
    # type: (str) -> List[Job]
    jobs = []
    job_names = self.joblist_helper.package_to_jobs.get(package_name, [])
    if job_names and len(job_names) > 0:
      jobs = [self._job_dictionary.get(name, None) for name in job_names]
    return jobs


  @property
  def log_path(self):
    return self.configuration_facade.log_path
    
  @property
  def package_names(self):
    # type: () -> Set[str]
    if self.joblist_helper.package_to_jobs:
      return set([package for package in self.joblist_helper.package_to_jobs])
    return []

  @property
  def jobs(self):
    # type: () -> List[Job]
    return self._jobs

  @property
  def job_dictionary(self):
    # type: () -> Dict[str, Job]
    return self._job_dictionary

  @property
  def chunk_unit(self):
    # type: () -> str
    return self.configuration_facade.chunk_unit

  @property
  def chunk_size(self):
    # type: () -> int
    return self.configuration_facade.chunk_size

  @property
  def dates(self):
    return self.pkl_organizer.dates
  
  @property
  def dates_formatted_dict(self):
    # type: () -> Dict[str, str]
    if len(self.dates) > 0:
      date_format = self.date_format
      return {date: date2str(date, date_format) for date in self.dates}
    else:
      return {}

  @property
  def members(self):
    return self.pkl_organizer.members
  
  @property
  def sections(self):
    return self.pkl_organizer.sections
  
  @property
  def date_format(self):
    # type: () -> str
    date_format = ''
    for date in self.pkl_organizer.dates:
      if date.hour > 1:
        date_format = 'H'
      if date.minute > 1:
        date_format = 'M'
    return date_format

  def _generate_job_dictionary(self):
    """ Generates Dict[Name] -> Job """
    for job in self._jobs:
      self._job_dictionary[job.name] = job

  def load_existing_structure_adjacency(self):
    self._structure_adjacency = get_structure(self.expid, self.configuration_facade.structures_path)

  def distribute_adjacency_into_jobs(self):
    parents_adjacency = {}
    for job in self._jobs:
      job.children_names = set(self._structure_adjacency.get(job.name, []))
      for children_name in job.children_names:
        parents_adjacency.setdefault(children_name, set()).add(job.name)
    for job in self._jobs:
      job.parents_names = set(parents_adjacency.get(job.name, []))
  
  def assign_configuration_data_to_jobs(self):
    # type: () -> None
    """ Sets Number of Processors, Platform, QoS, Wallclock"""
    section_to_config = {}
    for job in self._jobs:
      if job.section in section_to_config:
        job.ncpus = section_to_config[job.section]["ncpus"]
        job.platform = section_to_config[job.section]["platform"]
        job.qos = section_to_config[job.section]["qos"]
        job.wallclock = section_to_config[job.section]["wallclock"]
      else:
        job.ncpus = self.configuration_facade.get_section_processors(job.section)
        job.platform = self._determine_platform(job.section)
        job.qos = self._determine_qos(job)
        job.wallclock = self._determine_wallclock(job)
        section_to_config[job.section] = {"ncpus": job.ncpus, "platform": job.platform, "qos": job.qos, "wallclock": job.wallclock}

  def _determine_platform(self, section_name):    
    job_platform = self.configuration_facade.get_section_platform(section_name)
    if len(job_platform.strip()) == 0:
      job_platform = self.configuration_facade.get_main_platform()
    return job_platform

  def _determine_qos(self, job):
    # type: (Job) -> None
    job_qos = ""
    if job.package is not None:
      job_qos = self.configuration_facade.get_wrapper_qos()
    else:
      job_qos = self.configuration_facade.get_section_qos(job.section)
    if len(job_qos.strip()) == 0:
      job_qos = self.configuration_facade.get_platform_qos(job.platform, job.ncpus)
    return job_qos
  
  def _determine_wallclock(self, job):
    # type: (Job) -> None
    wallclock = self.configuration_facade.get_section_wallclock(job.section)
    if len(wallclock.strip()) == 0:
      wallclock = self.configuration_facade.get_platform_max_wallclock(job.platform)
    return wallclock

  def assign_packages_to_jobs(self):
    # type: () -> None
    if self.joblist_helper.job_to_package:
      for job in self._jobs:
        job.package = self.joblist_helper.job_to_package.get(job.name, None)
        if job.package:
          job.package_code = self.joblist_helper.package_to_package_id.get(job.package, None)
          job.package_symbol = self.joblist_helper.package_to_symbol.get(job.package, None)
  
  def assign_running_time_text_to_jobs(self):
    if self.joblist_helper.job_running_time_to_text:
      for job in self._jobs:
        job.running_time_text = self.joblist_helper.job_running_time_to_text.get(job.name, None)


  def _update_job_logs(self):
    # type: () -> None
    """
    Updates job out and err logs of the job list
    """               
    file_names = [name for name in os.listdir(self.configuration_facade.log_path) if fnmatch(
        name, '*.out') or fnmatch(name, '*.err')]

    try:
      out_set = [name for name in file_names if name.split('.')[-1] == 'out']
      out_set.sort()
      new_outs = {name.split('.')[0]: name for name in out_set}
    except:
      out_set = set()
      new_outs = dict()
    try:
      err_set = [name for name in file_names if name.split('.')[-1] == 'err']
      err_set.sort()
      new_errs = {name.split('.')[0]: name for name in err_set}
    except:
      err_set = set()
      new_errs = dict()

    for job in self._jobs:
      if job.status in [Status.COMPLETED, Status.FAILED]:
          job.out_path_local = os.path.join(self.log_path, new_outs.get(job.name, None)) if new_outs.get(job.name, None) else "NA"
          job.err_path_local = os.path.join(self.log_path, new_errs.get(job.name, None)) if new_errs.get(job.name, None) else "NA"

  def do_print(self):
    for job in self._jobs:
      print(job)





