import traceback
from autosubmit_api.components.experiment.configuration_facade import AutosubmitConfigurationFacade
from autosubmit_api.components.experiment.pkl_organizer import PklOrganizer
from autosubmit_api.logger import logger
from autosubmit_api.common import utils as utils
from autosubmit_api.components.jobs.joblist_helper import JobListHelper
from autosubmit_api.components.jobs.job_factory import Job, SimJob

UNITS_CONVERSOR_ENERGY = 3.6e9 
OPA_SIMULATED_YEARS_PER_JOB = 1 / 365.25 # One simulated day per OPA job

class PerformanceMetrics(object):
  """Manages Performance Metrics."""

  def __init__(self, expid: str, joblist_helper: JobListHelper):
    self.expid = expid
    self.error = False
    self.error_message = ""
    self.total_sim_run_time: int = 0
    self.total_sim_queue_time: int = 0
    self.valid_sim_yps_sum: float = 0.0
    self.valid_sim_energy_sum: float= 0.0
    self.valid_sim_footprint_sum: float = 0.0
    self.SYPD: float = 0
    self.ASYPD: float = 0
    self.CHSY: float = 0
    self.JPSY: float = 0
    self.RSYPD: float = 0
    self.processing_elements: int = 1
    self._considered: list[dict] = []
    self._not_considered: list[dict] = []
    self._sim_processors: int = 1
    self.warnings: list[str] = []
    self.post_jobs_total_time_average: int = 0
    self.sim_jobs_valid: list[SimJob] = []
    self.sim_jobs_invalid: list[SimJob] = []
    self.sim_jobs_platform = ""
    self.sim_platform_CF = 0.0
    self.sim_platform_PUE = 0.0
    # Simulated years per wall-clock day, averaged over completed SIM chunks (member, chunk).
    self.mean_sypd_per_chunk: float = 0.0
    self.mean_qsypd_per_chunk: float = 0.0
    # Total simulated years over the wall clock of the whole experiment.
    self.experiment_throughput: float = 0.0
    # SIM chunks coupled with their OPA stages.
    self.mean_csypd_per_chunk: float = 0.0
    self.mean_cqsypd_per_chunk: float = 0.0
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
      self._identify_outlier_jobs()
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
    self.joblist_helper.update_with_timedata(self.pkl_organizer.opa_jobs)
    # Update yps with the latest historical data
    self.joblist_helper.update_with_yps_per_run(self.pkl_organizer.sim_jobs)

  def _calculate_global_metrics(self):
      self.valid_sim_yps_sum = self._calculate_sum_yps()
      self.valid_sim_energy_sum = self._calculate_sum_energy()
      self.valid_sim_footprint_sum = self._calculate_sum_footprint()
      self.SYPD = self._calculate_SYPD()
      self.ASYPD = self._calculate_ASYPD()
      self.RSYPD = self._calculate_RSYPD()
      self.JPSY = self._calculate_JPSY()
      self.CHSY = self._calculate_CHSY()
      self._calculate_descriptive_throughput_metrics()

  def _calculate_descriptive_throughput_metrics(self):
      """Chunk based throughput metrics. They use COMPLETED jobs and do not apply the legacy outlier filter."""
      sim_chunks = self._get_completed_sim_chunks()
      self.mean_sypd_per_chunk = self._calculate_mean_sim_throughput(sim_chunks, include_queue_time=False)
      self.mean_qsypd_per_chunk = self._calculate_mean_sim_throughput(sim_chunks, include_queue_time=True)
      self.experiment_throughput = self._calculate_experiment_wall_clock_throughput(sim_chunks)
      (self.mean_csypd_per_chunk,
       self.mean_cqsypd_per_chunk) = self._calculate_opa_throughput_metrics(sim_chunks)

  def _get_completed_sim_chunks(self) -> dict[tuple, list[SimJob]]:
    """COMPLETED SIM jobs grouped by member and chunk. The splits of a chunk stay together."""
    sim_chunks = {}
    completed_sim_jobs = self.pkl_organizer.get_completed_section_jobs(utils.JobSection.SIM)
    for job in completed_sim_jobs:
      sim_chunks.setdefault((job.member, job.chunk), []).append(job)
    return sim_chunks

  def _get_last_completed_opa_jobs(self) -> dict[tuple, Job]:
    """COMPLETED OPA job that finished last for each member and chunk."""
    last_opa_jobs = {}
    for job in self.pkl_organizer.opa_jobs:
      if job.status != utils.Status.COMPLETED or job.finish <= 0:
        continue
      chunk = (job.member, job.chunk)
      last_opa_job = last_opa_jobs.get(chunk)
      if last_opa_job is None or job.finish > last_opa_job.finish:
        last_opa_jobs[chunk] = job
    return last_opa_jobs

  def _get_chunk_first_timestamp(self, jobs: list[Job], include_queue_time: bool) -> int:
    """Earliest submit (or start) of the jobs. 0 when no timestamp is available."""
    timestamps = [job.submit if include_queue_time else job.start for job in jobs]
    timestamps = [timestamp for timestamp in timestamps if timestamp > 0]
    return min(timestamps) if len(timestamps) > 0 else 0

  def _get_chunk_last_finish(self, jobs: list[Job]) -> int:
    """Latest finish of the jobs. 0 when no timestamp is available."""
    timestamps = [job.finish for job in jobs if job.finish > 0]
    return max(timestamps) if len(timestamps) > 0 else 0

  def _calculate_chunk_throughput(self, jobs: list[Job], years_per_sim: float, include_queue_time: bool) -> float:
    """Simulated years per wall-clock day. 0 when it cannot be computed."""
    first_timestamp = self._get_chunk_first_timestamp(jobs, include_queue_time)
    elapsed_time = self._get_chunk_last_finish(jobs) - first_timestamp
    if years_per_sim <= 0 or elapsed_time <= 0:
      return 0
    return years_per_sim * utils.SECONDS_IN_A_DAY / elapsed_time

  def _calculate_mean_sim_throughput(self, sim_chunks: dict[tuple, list[SimJob]], include_queue_time: bool) -> float:
    """Mean of the simulated years per wall-clock day of the COMPLETED SIM chunks."""
    throughputs = []
    for jobs in sim_chunks.values():
      throughput = self._calculate_chunk_throughput(jobs, jobs[0].years_per_sim, include_queue_time)
      if throughput > 0:
        throughputs.append(throughput)
    if len(throughputs) == 0:
      return 0
    return round(sum(throughputs) / len(throughputs), 4)

  def _calculate_experiment_wall_clock_throughput(self, sim_chunks: dict[tuple, list[SimJob]]) -> float:
    """Simulated years of the COMPLETED SIM chunks over the wall clock of the experiment."""
    first_submits = []
    last_finishes = []
    years_per_sim_sum = 0.0
    for jobs in sim_chunks.values():
      first_submit = self._get_chunk_first_timestamp(jobs, include_queue_time=True)
      last_finish = self._get_chunk_last_finish(jobs)
      if first_submit <= 0 or last_finish <= first_submit or jobs[0].years_per_sim <= 0:
        continue
      first_submits.append(first_submit)
      last_finishes.append(last_finish)
      years_per_sim_sum += jobs[0].years_per_sim
    if len(first_submits) == 0:
      return 0
    elapsed_time = max(last_finishes) - min(first_submits)
    return round(years_per_sim_sum * utils.SECONDS_IN_A_DAY / elapsed_time, 4)

  def _calculate_opa_throughput_metrics(self, sim_chunks: dict[tuple, list[SimJob]]) -> tuple[float, float]:
    """Bottleneck throughput of each SIM chunk with its last OPA stage, and the full SIM to OPA throughput."""
    last_opa_jobs = self._get_last_completed_opa_jobs()
    if len(last_opa_jobs) == 0:
      return 0, 0
    bottleneck_throughputs = []
    full_cycle_throughputs = []
    not_considered_chunks = 0
    for chunk, sim_jobs in sim_chunks.items():
      last_opa_job = last_opa_jobs.get(chunk)
      years_per_sim = sim_jobs[0].years_per_sim
      sim_throughput = self._calculate_chunk_throughput(sim_jobs, years_per_sim, include_queue_time=False)
      opa_throughput = 0
      if last_opa_job is not None:
        opa_throughput = self._calculate_chunk_throughput([last_opa_job], OPA_SIMULATED_YEARS_PER_JOB, include_queue_time=False)
      if sim_throughput <= 0 or opa_throughput <= 0:
        not_considered_chunks += 1
        continue
      bottleneck_throughputs.append(min(sim_throughput, opa_throughput))
      first_submit = self._get_chunk_first_timestamp(sim_jobs, include_queue_time=True)
      elapsed_time = last_opa_job.finish - first_submit
      if years_per_sim > 0 and elapsed_time > 0:
        full_cycle_throughputs.append(years_per_sim * utils.SECONDS_IN_A_DAY / elapsed_time)
    if not_considered_chunks > 0:
      self.warnings.append("OPA throughput | {0} COMPLETED SIM chunk(s) do not have a valid COMPLETED OPA job and are not considered.".format(not_considered_chunks))
    if len(bottleneck_throughputs) == 0:
      return 0, 0
    bottleneck = round(sum(bottleneck_throughputs) / len(bottleneck_throughputs), 4)
    if len(full_cycle_throughputs) == 0:
      return bottleneck, 0
    return bottleneck, round(sum(full_cycle_throughputs) / len(full_cycle_throughputs), 4)

  def _identify_outlier_jobs(self):
    """Warns about the COMPLETED SIM jobs that are not considered by the legacy metrics."""
    outlier_jobs = [job for job in self.pkl_organizer.get_completed_section_jobs(utils.JobSection.SIM) if job not in self.sim_jobs_valid]
    for job in outlier_jobs:
      self.warnings.append("Considered | Job {0} (Package {1}) is not considered for the legacy metrics because its run time is missing or is a runtime outlier.".format(job.name, self.joblist_helper.job_to_package.get(job.name, "No Package")))

  def _unify_warnings(self):
    self.warnings.extend(self.pkl_organizer.warnings)
    self.warnings.extend(self.configuration_facade.warnings)
    self.warnings.extend(self.joblist_helper.warning_messages)

  def _calculate_post_jobs_total_time_average(self):
    """Average run+queue of all completed POST jobs."""
    completed_post_jobs = self.pkl_organizer.get_completed_section_jobs(utils.JobSection.POST)
    self.post_jobs_total_time_average = utils.get_average_total_time(completed_post_jobs)


  def _get_sims_with_energy_count(self):
    return sum(1 for job in self.sim_jobs_valid if job.energy > 0)

  def _update_valid_sim_jobs_with_post_data(self):
    """Updates required value in sim job."""
    for simjob in self.sim_jobs_valid:
      if self.post_jobs_total_time_average > 0:
        simjob.set_post_jobs_total_average(self.post_jobs_total_time_average)
      # self._add_to_considered(simjob)

  def _populate_considered_jobs(self):
    """Format valid and invalid jobs to be added to the final JSON."""
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
    """Joules per Simulated Year."""
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
  
  def _calculate_sum_yps(self):
    """Sum of the simulated years of the valid SIM jobs. The splits of a chunk share its simulated years."""
    return sum(job.years_per_sim / self._get_job_splits(job) for job in self.sim_jobs_valid)

  @staticmethod
  def _get_job_splits(job: Job) -> int:
    if isinstance(job.splits, int) and job.splits > 0:
      return job.splits
    return 1
  
  def _calculate_sum_energy(self):
    return sum(job.energy for job in self.sim_jobs_valid)
  
  def _calculate_sum_footprint(self):
    if self.sim_jobs_platform == "":
      return 0.0
    return  ((self.valid_sim_energy_sum / UNITS_CONVERSOR_ENERGY) * self.sim_platform_CF * self.sim_platform_PUE)  
  
  def _calculate_sim_job_footprint(self, simjob: SimJob):
    return (simjob.energy / UNITS_CONVERSOR_ENERGY) * self.sim_platform_CF * self.sim_platform_PUE

  def _get_RSYPD_support_list(self) -> list[Job]:
    """The support list for the divisor can have a different source."""
    completed_transfer_jobs = self.pkl_organizer.get_completed_section_jobs(utils.JobSection.TRANSFER)
    completed_clean_jobs = self.pkl_organizer.get_completed_section_jobs(utils.JobSection.CLEAN)
    if len(completed_transfer_jobs) > 0:
      return completed_transfer_jobs
    elif len(completed_clean_jobs) > 0:
      return completed_clean_jobs
    else:
      return []

  def _get_RSYPD_divisor(self) -> float:
    """Wall clock between the first SIM start and the last TRANSFER/CLEAN finish."""
    support_list = self._get_RSYPD_support_list()
    sim_start_timestamps = [job.start_ts for job in self.sim_jobs_valid if job.start_ts > 0]
    support_finish_timestamps = [job.finish_ts for job in support_list if job.finish_ts > 0]
    if len(sim_start_timestamps) == 0 or len(support_finish_timestamps) == 0:
      return 0
    return max(max(support_finish_timestamps) - min(sim_start_timestamps), 0.0)

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

  def to_json(self) -> dict:
    return {"SY": self.valid_sim_yps_sum,
            "SYPD": self.SYPD,
            "ASYPD": self.ASYPD,
            "RSYPD": self.RSYPD,
            "mean_sypd_per_chunk": self.mean_sypd_per_chunk,
            "mean_qsypd_per_chunk": self.mean_qsypd_per_chunk,
            "experiment_throughput": self.experiment_throughput,
            "mean_csypd_per_chunk": self.mean_csypd_per_chunk,
            "mean_cqsypd_per_chunk": self.mean_cqsypd_per_chunk,
            "CHSY": self.CHSY,
            "JPSY": self.JPSY,
            "Parallelization": self.processing_elements,
            "Total_energy": self.valid_sim_energy_sum,
            "Total_footprint": self.valid_sim_footprint_sum,
            "platform_info":{"name": self.sim_jobs_platform, "CF": self.sim_platform_CF, "PUE": self.sim_platform_PUE},
            "considered": self._considered,
            "not_considered": self._not_considered,
            "error": self.error,
            "error_message": self.error_message,
            "warnings_job_data": self.warnings,
            }
