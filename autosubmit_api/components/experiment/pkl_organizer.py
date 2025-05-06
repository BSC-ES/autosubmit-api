#!/usr/bin/env python
from autosubmit_api.components.jobs import job_factory as factory
from autosubmit_api.common.utils import JobSection, PklJob, PklJob14, Status
from autosubmit_api.performance.utils import find_critical_path
from autosubmit_api.components.jobs.job_factory import Job, SimpleJob, StandardJob
from autosubmit_api.database.db_structure import get_structure
from typing import List, Dict, Set, Union

from autosubmit_api.persistance.pkl_reader import PklReader

class PklOrganizer(object):
  """
  Identifies dates, members, and sections. Distributes jobs into SIM, POST, TRANSFER, and CLEAN).
  SIM jobs are sorted by start times. POST, TRANSFER, and CLEAN are sorted by finish time.
  Warnings are stored in self.warnings.
  """

  def __init__(self, expid: str):
    self.current_content: List[Union[PklJob,PklJob14]] = []
    self.expid = expid
    self.sim_jobs: List[Job] = [] 
    self.post_jobs: List[Job] = [] 
    self.transfer_jobs: List[Job] = [] 
    self.clean_jobs: List[Job] = []
    self.other_jobs: List[Job] = [] 
    self.warnings: List[str] = [] 
    self.workflow_structure_error = False  # New attribute to track structure errors
    self.dates: Set[str] = set() 
    self.members: Set[str] = set() 
    self.sections: Set[str] = set() 
    self.section_jobs_map: Dict[str, List[Job]] = {}
    self._process_pkl()

  def prepare_jobs_for_performance_metrics(self):
    self.identify_dates_members_sections()
    self.distribute_jobs()
    self._sort_distributed_jobs()
    self._validate_current()
    self.load_and_assign_parent_child_relationships()

  def get_completed_section_jobs(self, section: str) -> List[Job]:
    if section in self.section_jobs_map:
      return [job for job in self.section_jobs_map[section] if job.status == Status.COMPLETED]
    else:
      return []
      # raise KeyError("Section not supported.")

  def get_simple_jobs(self, tmp_path: str) -> List[SimpleJob]:
    """ Get jobs in pkl as SimpleJob objects."""
    return [SimpleJob(job.name, tmp_path, job.status) for job in self.current_content]

  def _process_pkl(self):
    try:
      self.current_content = PklReader(self.expid).parse_job_list()
    except Exception as exc:
      raise Exception("Exception while reading the pkl content: {}".format(str(exc)))

  def identify_dates_members_sections(self):
    for job in self.current_content:
      if job.date and job.date not in self.dates:
        self.dates.add(job.date)
      if job.section and job.section not in self.sections:
        self.sections.add(job.section)
      if job.member and job.member not in self.members:
        self.members.add(job.member)


  def distribute_jobs(self):
    for pkl_job in self.current_content:
      if JobSection.SIM == pkl_job.section:
        self.sim_jobs.append(factory.get_job_from_factory(pkl_job.section).from_pkl(pkl_job))
      elif JobSection.POST == pkl_job.section:
        self.post_jobs.append(factory.get_job_from_factory(pkl_job.section).from_pkl(pkl_job))
      elif JobSection.TRANSFER == pkl_job.section:
        self.transfer_jobs.append(factory.get_job_from_factory(pkl_job.section).from_pkl(pkl_job))
      elif JobSection.CLEAN == pkl_job.section:
        self.clean_jobs.append(factory.get_job_from_factory(pkl_job.section).from_pkl(pkl_job))
      else:
        self.other_jobs.append(StandardJob.from_pkl(pkl_job))
    self.section_jobs_map = {
      JobSection.SIM : self.sim_jobs,
      JobSection.POST : self.post_jobs,
      JobSection.TRANSFER : self.transfer_jobs,
      JobSection.CLEAN : self.clean_jobs,
      JobSection.OTHER : self.other_jobs,
    }

  def _sort_distributed_jobs(self):
    """ SIM jobs are sorted by start_time  """
    self._sort_list_by_start_time(self.sim_jobs)
    self._sort_list_by_finish_time(self.post_jobs)
    self._sort_list_by_finish_time(self.transfer_jobs)
    self._sort_list_by_finish_time(self.clean_jobs)

  def _validate_current(self):
    if len(self.get_completed_section_jobs(JobSection.SIM)) == 0:
      self._add_warning("We couldn't find COMPLETED SIM jobs in the experiment.")
    if len(self.get_completed_section_jobs(JobSection.POST)) == 0:
      self._add_warning("We couldn't find COMPLETED POST jobs in the experiment. The time of the POST jobs will not be included in the PSYPD calculation.")
    if len(self.get_completed_section_jobs(JobSection.TRANSFER)) == 0 and len(self.get_completed_section_jobs(JobSection.CLEAN)) == 0:
      self._add_warning("RSYPD | There are no TRANSFER nor CLEAN (COMPLETED) jobs in the experiment, RSYPD cannot be computed.")
    if len(self.get_completed_section_jobs(JobSection.TRANSFER)) == 0 and len(self.get_completed_section_jobs(JobSection.CLEAN)) > 0:
      self._add_warning("RSYPD | There are no TRANSFER (COMPLETED) jobs in the experiment. We will use (COMPLETED) CLEAN jobs to compute RSYPD.")

  def _add_warning(self, message: str):
    self.warnings.append(message)

  def _sort_list_by_finish_time(self, jobs: List[Job]):
    if len(jobs):
      jobs.sort(key = lambda x: x.finish, reverse=False)

  def _sort_list_by_start_time(self, jobs: List[Job]):
    if len(jobs):
      jobs.sort(key = lambda x: x.start, reverse=False)

  def load_and_assign_parent_child_relationships(self):
    """
    Loads structure adjacency and assigns parent-child relationships to all jobs.
    """
    try:
      structure_adjacency = get_structure(self.expid)
    except Exception:
      warning_msg = ("Could not obtain the workflow structure; ideal critical path will not be calculated.")
      self._add_warning(warning_msg)
      self.workflow_structure_error = True
      return  

    job_name_map = {}
    for section in self.section_jobs_map:
      for job in self.section_jobs_map[section]:
        job_name_map[job.name] = job

    parents_adjacency = {}
      
    for job_name, job in job_name_map.items():
      children = set(structure_adjacency.get(job_name, []))
      job.children_names = children
      
      for child_name in children:
        parents_adjacency.setdefault(child_name, set()).add(job_name)
      
    for job_name, job in job_name_map.items():
      job.parents_names = set(parents_adjacency.get(job_name, []))

  def find_ideal_critical_path(self) -> List[dict]:
    """
    Prepares the completed jobs for critical path calculation.
    Processes the jobs into a dictionary and calls the generalized algorithm.
    Returns a list of dictionaries representing the jobs of the ideal critical path.
    """
    if self.workflow_structure_error:
      return []

    completed_jobs = []
    for section in self.section_jobs_map:
        completed_jobs.extend(self.get_completed_section_jobs(section))
    
    if not completed_jobs:
        self._add_warning("Critical path: No completed jobs found.")
        return []
    
    jobs_dict = {}
    for job in completed_jobs:
        jobs_dict[job.name] = {
            'run_time': job.run_time or 0,
            'queue_time': job.queue_time or 0,
            'children_names': job.children_names,
            'section': job.section
        }
    
    return find_critical_path(jobs_dict)
    
  def __repr__(self):
    return "Total {0}\nSIM {1}\nPOST {2}\nTRANSFER {3}\nCLEAN {4}\nOTHER {5}".format(
      len(self.current_content),
      len(self.sim_jobs),
      len(self.post_jobs),
      len(self.transfer_jobs),
      len(self.clean_jobs),
      len(self.other_jobs)
    )