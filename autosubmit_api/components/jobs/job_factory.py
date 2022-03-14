#!/usr/bin/env python
import collections
import time
import autosubmit_api.common.utils as util
import autosubmit_api.components.jobs.utils as JUtils
from autosubmit_api.common.utils import Status
from autosubmit_api.monitor.monitor import Monitor
from autosubmit_api.history.data_classes.job_data import JobData
from typing import Tuple, List, Dict, Set
# from autosubmitAPIwu.database.db_jobdata import JobData
from abc import ABCMeta, abstractmethod
JobRow = collections.namedtuple(
    'JobRow', ['name', 'queue_time', 'run_time', 'status', 'energy', 'submit', 'start', 'finish', 'ncpus', 'run_id'])

class Job:
  """ Abstract Job """
  __metaclass__ = ABCMeta
  
  def __init__(self):
    self.name = None # type: str
    self._id = None # type: int  
    self.status = Status.UNKNOWN # type: int
    self.priority = 0 # type: int
    self.date = None # type: str
    self.member = None # type: str
    self.chunk = None # type: str
    self.out_path_local = None # type: str
    self.err_path_local = None # type: str
    self.out_path_remote = None # type: str
    self.err_path_remote = None # type: str
    self.section = "" # type: str
    self._queue_time = 0 # type: int
    self._run_time = 0 # type: int
    self.energy = 0 # type: int
    self._submit = 0 # type: int
    self._start = 0 # type: int
    self._finish = 0 # type: int
    self.ncpus = 0 # type: int
    self.platform = None # type: str
    self.qos = "" # type: str
    self.wallclock = "" # type: str
    self.parents_names = set() # type: Set[str]
    self.children_names = set() # type: Set[str]
    self.package = None # type: str
    self.package_code = None # type: str
    self.package_symbol = None # type: str
    self.running_time_text = None # type: str
    self.tree_parent = [] # type: List[str]
    self.run_id = None # type: int
    self.x_coordinate = 0 # type: int
    self.y_coordinate = 0 # type: int
    self.level = 0 # type: int
    self.horizontal_order = 1 # type: int
    self.barycentric_value = 0.0 # type: float

  def has_parents(self):
    return len(self.parents_names) > 0
  
  def has_children(self):
    return len(self.children_names) > 0

  @property
  def queue_time(self):
    # type: () -> int
    """ Queue time fixed is provided. """
    return self._queue_time    
  
  @property
  def run_time(self):
    # type: () -> int
    """ Proper run time is provided. """
    return self._run_time

  @property
  def submit(self):
    if self.status in JUtils.SUBMIT_STATUS:
      return self._submit
    return 0
  
  @property
  def start(self):
    if self.status in JUtils.START_STATUS:
      return self._start
    return 0
  
  @property
  def finish(self):
    if self.status in JUtils.FINISH_STATUS:
      return self._finish
    return 0

  @property
  def submit_ts(self):
    return self.submit
  
  @property
  def start_ts(self):
    return self.start
  
  @property
  def finish_ts(self):
    return self.finish

  @property
  def submit_datetime(self):
    # type: () -> str
    return util.timestamp_to_datetime_format(self.submit)

  @property
  def start_datetime(self):
    # type: () -> str
    return util.timestamp_to_datetime_format(self.start)

  @property
  def finish_datetime(self):
    # type: () -> str
    return util.timestamp_to_datetime_format(self.finish)

  @property
  def status_color(self):    
    return Monitor.color_status(self.status)
  
  @property 
  def status_text(self):
    # type: () -> str
    return str(Status.VALUE_TO_KEY[self.status])

  @property
  def total_time(self):
    # type: () -> int
    return self.queue_time + self.run_time
  
  @property
  def total_processors(self):
    # type: () -> int
    return self.ncpus
  
  @property
  def total_wallclock(self):
    # type: () -> float
    """ In hours """
    if self.wallclock:
      hours, minutes = self.wallclock.split(':')
      return float(minutes) / 60 + float(hours)
    return 0

  @property
  def tree_title(self):
    # type: () -> str
    title = "{0} <span class='badge' style='background-color: {1}; color:{3};'>#{2}</span>".format(self.name, self.status_color, self.status_text, JUtils.get_status_text_color(self.status))
    if self.running_time_text and len(self.running_time_text) > 0:
      title += " ~ {0}".format(self.running_time_text)
    if len(self.children_names) == 0:
      title += JUtils.target_tag
    if len(self.parents_names) == 0:
      title += JUtils.source_tag
    if self.date is not None and self.member == None:
      title += JUtils.sync_tag
    if self.package:
      title += JUtils.wrapped_title_format.format(self.package_code)
    return title
  
  @property
  def leaf(self):
    # type: () -> Dict[str, str]
    return {
      "title": self.tree_title,
      "refKey": self.name,
      "data": "Empty",
      "children": []
    } 

  @abstractmethod
  def do_print(self):
    # type: () -> None
    print("Job {0} \n Date {5} \n Section {1} \n Qos {2} \n Children: {3} \n Platform {4} \n TreeParent {6}. ".format(
      self.name, self.section, self.qos, self.children_names, self.platform, self.date, self.tree_parent))
  
  def update_from_jobrow(self, jobrow):
    # type: (JobRow) -> None
    """ Updates: submit, start, finish, queue_time, run_time, energy, run_id. """
    if jobrow:
      self._queue_time = max(int(jobrow.queue_time), 0)
      self._run_time = max(int(jobrow.run_time), 0)
      self.energy = max(int(jobrow.energy), 0)
      self._submit = int(jobrow.submit)
      self._start = int(jobrow.start)
      self._finish = int(jobrow.finish)      
      self.run_id = jobrow.run_id

  def set_ncpus(self, parallelization):
    # type: (int) -> None
    self.ncpus = parallelization
  
  def set_years_per_sim(self, years_per_sim):
    # type: (float) -> None    
    self.years_per_sim = max(years_per_sim, 0.0)
  
  def get_date_ini_end(self, chunk_size, chunk_unit):
    # type: (int, str) -> Tuple[str, str]
    return util.date_plus(self.date, chunk_unit, self.chunk, chunk_size)
    
  
  @classmethod
  def from_pkl(cls, pkl_item):
    # type: (str) -> Job
    job = cls()
    job.name = pkl_item.name
    job._id = pkl_item.id
    job.status = pkl_item.status
    job.priority = pkl_item.priority
    job.date = pkl_item.date
    job.section = pkl_item.section
    job.member = pkl_item.member
    job.chunk = pkl_item.chunk
    job.out_path_local = pkl_item.out_path_local
    job.err_path_local = pkl_item.err_path_local
    job.out_path_remote = pkl_item.out_path_remote
    job.err_path_remote = pkl_item.err_path_remote
    return job
  
  @classmethod
  def from_old_job_data(cls, job_data):    
    job = cls()
    job.name = job_data.job_name
    job._id = job_data._id
    job.status = job_data.status
    job.priority = 0
    job.date = job_data.date
    job.section = job_data.section
    job.member = job_data.member
    job.chunk = job_data.chunk
    job.out_path_local = job_data.out
    job.err_path_local = job_data.err
    job.out_path_remote = job_data.out
    job.err_path_remote = job_data.err
    job._queue_time = job_data.queuing_time()
    job._run_time = job_data.running_time()
    job.energy = job_data.energy 
    job._submit = job_data.submit
    job._start = job_data.start
    job._finish = job_data.finish
    job.ncpus = job_data.ncpus 
    job.run_id = job_data.run_id    
    return job
  
  @classmethod
  def from_job_data_dc(cls, job_data_dc):
    # type: (JobData) -> Job
    job = cls()
    job.name = job_data_dc.job_name
    job._id = job_data_dc._id
    job.status = job_data_dc.status_code
    job.priority = 0
    job.date = job_data_dc.date
    job.section = job_data_dc.section
    job.member = job_data_dc.member
    job.chunk = job_data_dc.chunk
    job.out_path_local = job_data_dc.out
    job.err_path_local = job_data_dc.err
    job.out_path_remote = job_data_dc.out
    job.err_path_remote = job_data_dc.err
    job._queue_time = job_data_dc.queuing_time
    job._run_time = job_data_dc.running_time
    job.energy = job_data_dc.energy 
    job._submit = job_data_dc.submit
    job._start = job_data_dc.start
    job._finish = job_data_dc.finish
    job.ncpus = job_data_dc.ncpus
    job.run_id = job_data_dc.run_id    
    return job
class StandardJob(Job):
  """ Straightforward implementation of Job """
  def __init__(self):
      super(StandardJob, self).__init__()

  def do_print(self):
    return super(StandardJob, self).do_print()


class SimJob(Job):
  """ Simulation Job """
  def __init__(self):
    super(SimJob, self).__init__()
    self.section = util.JobSection.SIM 
    self.post_jobs_total_time_average = 0.0 # type: float
    self.years_per_sim = 0 # type: float   


  @property
  def CHSY(self):
    # type: () -> float
    if self.years_per_sim > 0:
      return round(((self.ncpus * self.run_time) / self.years_per_sim) / util.SECONDS_IN_ONE_HOUR, 2)
    return 0
  
  @property
  def JPSY(self):
    # type: () -> float
    if self.years_per_sim > 0:
      return round(self.energy / self.years_per_sim, 2)
    return 0
  
  @property
  def SYPD(self):
    # type: () -> float
    if self.years_per_sim > 0 and self.run_time > 0:      
      return round((self.years_per_sim * util.SECONDS_IN_A_DAY) / self.run_time, 2)
    return 0
  
  @property
  def ASYPD(self):
    """ ASYPD calculation requires the average of the queue and run time of all post jobs """
    # type: () -> float
    divisor = self.total_time + self.post_jobs_total_time_average
    if divisor > 0:
      return round((self.years_per_sim * util.SECONDS_IN_A_DAY) / (divisor), 2)
    return 0
  

  def do_print(self):
    return super(SimJob, self).do_print()
  
  def set_post_jobs_total_average(self, val):
    # type: (float) -> None
    self.post_jobs_total_time_average = val
  


class PostJob(Job):
  def __init__(self):
    super(PostJob, self).__init__()
    self.section = util.JobSection.POST

  def do_print(self):
    return super(PostJob, self).do_print()

class TransferMemberJob(Job):
  def __init__(self):
    super(TransferMemberJob, self).__init__()
    self.section = util.JobSection.TRANSFER_MEMBER

  def do_print(self):
    return super(TransferMemberJob, self).do_print()
  
class TransferJob(Job):
  def __init__(self):
    super(TransferJob, self).__init__()
    self.section = util.JobSection.TRANSFER

  def do_print(self):
    return super(TransferJob, self).do_print()

class CleanMemberJob(Job):
  def __init__(self):
    super(CleanMemberJob, self).__init__()
    self.section = util.JobSection.CLEAN_MEMBER

  def do_print(self):
    return super(CleanMemberJob, self).do_print()

class CleanJob(Job):
  def __init__(self):
    super(CleanJob, self).__init__()
    self.section = util.JobSection.CLEAN

  def do_print(self):
    return super(CleanJob, self).do_print()

class JobFactory:
  """ Generic Factory """
  __metaclass__ = ABCMeta

  @abstractmethod
  def factory_method(self):
    # type: () -> Job 
    """ """

class SimFactory(JobFactory):
  def factory_method(self):
    # type: () -> Job
    return SimJob()

class PostFactory(JobFactory):
  def factory_method(self):
    # type: () -> Job
    return PostJob()

class TransferMemberFactory(JobFactory):
  def factory_method(self):
    # type: () -> Job
    return TransferMemberJob()

class TransferFactory(JobFactory):
  def factory_method(self):
    # type: () -> Job
    return TransferJob()

class CleanMemberFactory(JobFactory):
  def factory_method(self):
    # type: () -> Job
    return CleanMemberJob()

class CleanFactory(JobFactory):
  def factory_method(self):
    # type: () -> Job
    return CleanJob()


def get_job_from_factory(section):
  # type: (str) -> StandardJob
  factories = {
    util.JobSection.SIM : SimFactory(),
    util.JobSection.POST : PostFactory(),
    util.JobSection.TRANSFER_MEMBER : TransferMemberFactory(),
    util.JobSection.TRANSFER : TransferFactory(),
    util.JobSection.CLEAN_MEMBER : CleanMemberFactory(),
    util.JobSection.CLEAN : CleanFactory()
  }
  if section in factories:
    return factories[section].factory_method()
  else:
    raise KeyError("JobSection not implemented in factory.")


  



