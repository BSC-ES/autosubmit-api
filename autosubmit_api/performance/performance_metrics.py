#!/usr/bin/env python
import traceback
from autosubmit_api.components.experiment.configuration_facade import AutosubmitConfigurationFacade
from autosubmit_api.components.experiment.pkl_organizer import PklOrganizer
from autosubmit_api.logger import logger
from autosubmit_api.common import utils as utils
from autosubmit_api.components.jobs.joblist_helper import JobListHelper
from autosubmit_api.components.jobs.job_factory import Job, SimJob
from typing import List, Dict

UNITS_CONVERSOR_ENERGY = 3.6e9 

class PerformanceMetrics(object):
  """ Manages Performance Metrics """

  def __init__(self, expid: str, joblist_helper: JobListHelper):
    self.expid = expid
    self.error = False
    self.error_message = ""
    self.total_sim_run_time: int = 0
    self.total_sim_queue_time: int = 0
    self.valid_sim_yps_sum: float = 0.0
    self.valid_sim_energy_sum: float= 0.0
    self.valid_sim_core_hours_sum: float = 0.0
    self.valid_sim_footprint_sum: float = 0.0
    self.SYPD: float = 0
    self.ASYPD: float = 0
    self.CHSY: float = 0
    self.JPSY: float = 0
    self.RSYPD: float = 0
    self.WSYPD: float = 0
    self.IWSYPD: float = 0
    self.processing_elements: int = 1
    self._considered: List[Dict] = []
    self._not_considered: List[Dict] = []
    self._sim_processors: int = 1
    self.warnings: List[str] = []
    self.post_jobs_total_time_average: int = 0
    self.sim_jobs_valid: List[SimJob] = []
    self.sim_jobs_invalid: List[SimJob] = []
    self.sim_jobs_platform = ""
    self.sim_platform_CF = 0.0
    self.sim_platform_PUE = 0.0
    self.ideal_critical_path = []
    self.phases = {}
    try:
      self.joblist_helper: JobListHelper = joblist_helper
      self.configuration_facade: AutosubmitConfigurationFacade = self.joblist_helper.configuration_facade
      self.pkl_organizer: PklOrganizer = self.joblist_helper.pkl_organizer
      self.pkl_organizer.prepare_jobs_for_performance_metrics()
      self._sim_processors = self.configuration_facade.sim_processors
      self.processing_elements = self.configuration_facade.sim_processing_elements
    except Exception as exp:
      self.error = True
      self.error_message = "Error while preparing data sources: {0}".format(str(exp))
      logger.error((traceback.format_exc()))
      logger.error((str(exp)))
    if self.error is False:
      self.configuration_facade.update_sim_jobs(self.pkl_organizer.sim_jobs) # This will assign self.configuration_facade.sim_processors to all the SIM jobs
      self._update_sim_jobs_platform(self.configuration_facade.get_section_platform(utils.JobSection.SIM))
      self._update_jobs_with_time_data()
      self._calculate_post_jobs_total_time_average()
      self.sim_jobs_valid, self.sim_jobs_invalid = utils.separate_job_outliers(self.pkl_organizer.get_completed_section_jobs(utils.JobSection.SIM))
      self._identify_outlied_jobs()
      self._update_valid_sim_jobs_with_post_data()
      self._populate_considered_jobs()
      self._calculate_total_sim_queue_time()
      self._calculate_total_sim_run_time()
      self._calculate_global_metrics()
      self._unify_warnings()

  def _update_sim_jobs_platform(self, platform: str):
    if platform: 
      self.sim_jobs_platform = platform
      conf_platform = self.configuration_facade.get_platorm_conf_footprint(platform)
      cf = conf_platform["CF"]
      pue = conf_platform["PUE"]
      if not cf:
        self.warnings.append("The CF for platform {0} could not be obtained; therefore the footprint will be 0.".format(self.sim_jobs_platform))
      else:
        try:
          self.sim_platform_CF = float(cf)
        except ValueError:
          self.warnings.append("The CF for platform {0} value is not a valid number; therefore the footprint will be 0.".format(self.sim_jobs_platform))
      if not pue:
        self.warnings.append("The PUE for platform {0} could not be obtained; therefore the footprint will be 0.".format(self.sim_jobs_platform))
      else:
        try:
          self.sim_platform_PUE = float(pue)
        except ValueError:
          self.warnings.append("The PUE for platform {0} value is not a valid number; therefore the footprint will be 0.".format(self.sim_jobs_platform))
    else:
      self.warnings.append("The platform could not be obtained; therefore the footprint will be 0.")


  def _update_jobs_with_time_data(self):
      self.joblist_helper.update_with_timedata(self.pkl_organizer.sim_jobs)
      self.joblist_helper.update_with_timedata(self.pkl_organizer.post_jobs)
      self.joblist_helper.update_with_timedata(self.pkl_organizer.clean_jobs)
      self.joblist_helper.update_with_timedata(self.pkl_organizer.transfer_jobs)
      self.joblist_helper.update_with_timedata(self.pkl_organizer.other_jobs)
      # Update yps with the latest historical data
      self.joblist_helper.update_with_yps_per_run(self.pkl_organizer.sim_jobs)

  def _calculate_global_metrics(self):
      self.valid_sim_yps_sum = self._calculate_sum_yps()
      self.valid_sim_energy_sum = self._calculate_sum_energy()
      self.valid_sim_footprint_sum = self._calculate_sum_footprint()
      self.valid_sim_core_hours_sum = self._calculate_sum_core_hours()
      self.SYPD = self._calculate_SYPD()
      self.ASYPD = self._calculate_ASYPD()
      self.RSYPD = self._calculate_RSYPD()
      self.JPSY = self._calculate_JPSY()
      self.CHSY = self._calculate_CHSY()
      self.ideal_critical_path = self.pkl_organizer.find_ideal_critical_path()
      self.phases = self.pkl_organizer.calculate_ideal_critical_path_phases(self.ideal_critical_path)
      self.WSYPD = self._calculate_WSYPD()
      self.IWSYPD = self._calculate_IWSYPD()

  def _identify_outlied_jobs(self):
    """ Generates warnings """
    outlied = [job for job in self.pkl_organizer.get_completed_section_jobs(utils.JobSection.SIM) if job not in self.sim_jobs_valid]
    for job in outlied:
      self.warnings.append("Considered | Job {0} (Package {1}) has no energy information and is not going to be considered for energy calculations.".format(job.name, self.joblist_helper.job_to_package.get(job.name, "No Package")))

  def _unify_warnings(self):
    self.warnings.extend(self.pkl_organizer.warnings)
    self.warnings.extend(self.configuration_facade.warnings)
    self.warnings.extend(self.joblist_helper.warning_messages)

  def _calculate_post_jobs_total_time_average(self):
    """ Average run+queue of all completed POST jobs """
    completed_post_jobs = self.pkl_organizer.get_completed_section_jobs(utils.JobSection.POST)
    self.post_jobs_total_time_average = utils.get_average_total_time(completed_post_jobs)


  def _get_sims_with_energy_count(self):
    return sum(1 for job in self.sim_jobs_valid if job.energy > 0)

  def _update_valid_sim_jobs_with_post_data(self):
    """ Updates required value in sim job """
    for simjob in self.sim_jobs_valid:
      if self.post_jobs_total_time_average > 0:
        simjob.set_post_jobs_total_average(self.post_jobs_total_time_average)
      # self._add_to_considered(simjob)

  def _populate_considered_jobs(self):
    """
    Format valid and invalid jobs to be added to the final JSON
    """
    for simjob in self.sim_jobs_valid:
      self._considered.append(self._sim_job_to_dict(simjob))

    for simjob in self.sim_jobs_invalid:
      self._not_considered.append(self._sim_job_to_dict(simjob))

  def _calculate_total_sim_run_time(self):
    self.total_sim_run_time =  sum(job.run_time for job in self.sim_jobs_valid)

  def _calculate_total_sim_queue_time(self):
    self.total_sim_queue_time = sum(job.queue_time for job in self.sim_jobs_valid)


  def _calculate_SYPD(self):
    if self.total_sim_run_time > 0:
      SYPD = ((self.valid_sim_yps_sum * utils.SECONDS_IN_A_DAY) /
                  (self.total_sim_run_time)) 
      return round(SYPD, 4)
    return 0

  def _calculate_ASYPD(self):
    if len(self.sim_jobs_valid) > 0 and (self.total_sim_run_time + self.total_sim_queue_time + self.post_jobs_total_time_average)>0:
      ASYPD = ((self.valid_sim_yps_sum * utils.SECONDS_IN_A_DAY) / 
                 (self.total_sim_run_time + self.total_sim_queue_time + self.post_jobs_total_time_average))
      return round(ASYPD, 4)
    return 0

  def _calculate_RSYPD(self):
    divisor = self._get_RSYPD_divisor()
    if len(self.sim_jobs_valid) > 0 and divisor > 0:
      RSYPD = (self.valid_sim_yps_sum * utils.SECONDS_IN_A_DAY) / divisor
      return round(RSYPD, 4)
    return 0

  def _calculate_JPSY(self):
    """ Joules per Simulated Year """
    sims_with_energy_count = self._get_sims_with_energy_count()
    if len(self.sim_jobs_valid) > 0 and sims_with_energy_count > 0:
      JPSY = sum(job.JPSY for job in self.sim_jobs_valid)/sims_with_energy_count
      return round(JPSY, 4)
    return 0

  def _calculate_CHSY(self):
    if len(self.sim_jobs_valid) > 0:
      CHSY = sum(job.CHSY for job in self.sim_jobs_valid)/len(self.sim_jobs_valid)
      return round(CHSY, 4)
    return 0

  def _calculate_WSYPD(self):
    time_workflow = self.phases.get("total_run_time", 0)
    if len(self.sim_jobs_valid) > 0 and time_workflow > 0:
      WSYPD = ((self.valid_sim_yps_sum * utils.SECONDS_IN_A_DAY) / time_workflow)
      return round(WSYPD, 4)
    return 0
  
  def _calculate_IWSYPD(self):
    time_workflow = self.phases.get("total_run_queue_time", 0)
    if len(self.sim_jobs_valid) > 0 and time_workflow > 0:
      IWSYPD = ((self.valid_sim_yps_sum * utils.SECONDS_IN_A_DAY) / time_workflow)
      return round(IWSYPD, 4)
    return 0

  def _calculate_sum_yps(self):
    return sum(job.years_per_sim for job in self.sim_jobs_valid)
  
  def _calculate_sum_energy(self):
    return sum(job.energy for job in self.sim_jobs_valid)
  
  def _calculate_sum_footprint(self):
    if self.sim_jobs_platform == "":
      return 0.0
    return  ((self.valid_sim_energy_sum / UNITS_CONVERSOR_ENERGY) * self.sim_platform_CF * self.sim_platform_PUE)  
  
  def _calculate_sim_job_footprint(self, simjob: SimJob):
    return (simjob.energy / UNITS_CONVERSOR_ENERGY) * self.sim_platform_CF * self.sim_platform_PUE
  
  def _calculate_sum_core_hours(self):
    return round((self._sim_processors * self.total_sim_run_time) / utils.SECONDS_IN_ONE_HOUR , 2)

  def _get_RSYPD_support_list(self) -> List[Job]:
    """ The support list for the divisor can have a different source """
    completed_transfer_jobs = self.pkl_organizer.get_completed_section_jobs(utils.JobSection.TRANSFER)
    completed_clean_jobs = self.pkl_organizer.get_completed_section_jobs(utils.JobSection.CLEAN)
    if len(completed_transfer_jobs) > 0:
      return completed_transfer_jobs
    elif len(completed_clean_jobs) > 0:
      return completed_clean_jobs
    else:
      return []

  def _get_RSYPD_divisor(self) -> float:
    support_list = self._get_RSYPD_support_list()
    divisor = 0
    if len(support_list) > 0 and len(self.sim_jobs_valid):
      divisor = max(support_list[-1].finish_ts - self.sim_jobs_valid[0].start_ts, 0.0)
    return divisor

  def _process_ideal_critical_path(self):
    """
    Process the critical path to get the jobs in the critical path
    """
    if len(self.ideal_critical_path) > 0:
      return [self._job_to_dict(job) for job in self.ideal_critical_path]
    return []
  
  def _process_ideal_critical_path_phases(self):
    """
    Process the critical path phases to get the time in each phase
    """
    return {
      "pre_sim_time": self.phases.get("pre_sim_run_time", 0),
      "sim_time": self.phases.get("sim_run_time", 0),
      "post_sim_time": self.phases.get("post_sim_run_time", 0),
      "total_time": self.phases.get("total_run_time", 0),
    }
  
  def _sim_job_to_dict(self, simjob: SimJob): 
    return {
      "name": simjob.name,
      "queue": simjob.queue_time,
      "running": simjob.run_time,
      "CHSY": simjob.CHSY,
      "SYPD": simjob.SYPD,
      "ASYPD": simjob.ASYPD,
      "JPSY": simjob.JPSY,
      "energy": simjob.energy,
      "yps": simjob.years_per_sim,
      "ncpus": simjob.ncpus,
      "chunk": simjob.chunk,
      "footprint": self._calculate_sim_job_footprint(simjob), 
    }
  
  def _job_to_dict(self, job: Job):
    return {
      "name": job.name,
      "running": job.run_time,
    }

  def to_json(self) -> Dict:
    return {"SY": self.valid_sim_yps_sum,
            "SYPD": self.SYPD,
            "ASYPD": self.ASYPD,
            "RSYPD": self.RSYPD,
            "CHSY": self.CHSY,
            "JPSY": self.JPSY,
            "WSYPD": self.WSYPD,
            "IWSYPD": self.IWSYPD,
            "Parallelization": self.processing_elements,
            "Total_energy": self.valid_sim_energy_sum,
            "Total_footprint": self.valid_sim_footprint_sum,
            "platform_info":{"name": self.sim_jobs_platform, "CF": self.sim_platform_CF, "PUE": self.sim_platform_PUE},
            "Total_core_hours": self.valid_sim_core_hours_sum,
            "ideal_critical_path": self._process_ideal_critical_path(),
            "ideal_phases": self._process_ideal_critical_path_phases(),
            "considered": self._considered,
            "not_considered": self._not_considered,
            "error": self.error,
            "error_message": self.error_message,
            "warnings_job_data": self.warnings,
            }
