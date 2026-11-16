from autosubmit_api.common.utils import JobSection, Status
from autosubmit_api.components.jobs import job_factory as factory
from autosubmit_api.components.jobs.job_factory import Job, SimpleJob
from autosubmit_api.database.models import PklJobModel
from autosubmit_api.repositories.jobs import create_jobs_repository


class PklOrganizer(object):
  """Identifies dates, members, and sections.
  
  Distributes jobs into SIM, POST, TRANSFER, CLEAN and OPA sections.
  SIM jobs are sorted by start times. Other jobs are sorted by finish time.
  Warnings are stored in self.warnings.
  """

  def __init__(self, expid: str):
    self.current_content: list[PklJobModel] = []
    self.expid = expid
    self.sim_jobs: list[Job] = [] 
    self.post_jobs: list[Job] = [] 
    self.transfer_jobs: list[Job] = [] 
    self.clean_jobs: list[Job] = [] 
    self.opa_jobs: list[Job] = []
    self.warnings: list[str] = [] 
    self.dates: set[str] = set() 
    self.members: set[str] = set() 
    self.sections: set[str] = set() 
    self.section_jobs_map: dict[str, list[Job]] = {}
    self._process_pkl()

  def prepare_jobs_for_performance_metrics(self):
    self.identify_dates_members_sections()
    self.distribute_jobs()
    self._sort_distributed_jobs()
    self._validate_current()

  def get_completed_section_jobs(self, section: str) -> list[Job]:
    if section in self.section_jobs_map:
      return [job for job in self.section_jobs_map[section] if job.status == Status.COMPLETED]
    else:
      return []
      # raise KeyError("Section not supported.")

  def get_simple_jobs(self, tmp_path: str) -> list[SimpleJob]:
    """Get jobs in pkl as SimpleJob objects."""
    return [SimpleJob(job.name, tmp_path, job.status) for job in self.current_content]

  def _process_pkl(self):
    try:
      job_list_repo = create_jobs_repository(self.expid)
      self.current_content = job_list_repo.get_all()
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
      elif pkl_job.section and pkl_job.section.startswith(JobSection.OPA):
        self.opa_jobs.append(factory.StandardJob.from_pkl(pkl_job))
    self.section_jobs_map = {
      JobSection.SIM : self.sim_jobs,
      JobSection.POST : self.post_jobs,
      JobSection.TRANSFER : self.transfer_jobs,
      JobSection.CLEAN : self.clean_jobs,
      **self._get_opa_section_jobs(),
    }

  def _sort_distributed_jobs(self):
    """SIM jobs are sorted by start_time."""
    self._sort_list_by_start_time(self.sim_jobs)
    self._sort_list_by_finish_time(self.post_jobs)
    self._sort_list_by_finish_time(self.transfer_jobs)
    self._sort_list_by_finish_time(self.clean_jobs)
    self._sort_list_by_finish_time(self.opa_jobs)

  def _get_opa_section_jobs(self) -> dict[str, list[Job]]:
    opa_sections: dict[str, list[Job]] = {}
    for job in self.opa_jobs:
      opa_sections.setdefault(job.section, []).append(job)
    return opa_sections

  def _validate_current(self):
    if len(self.get_completed_section_jobs(JobSection.SIM)) == 0:
      self._add_warning("We couldn't find COMPLETED SIM jobs in the experiment.")
    if len(self.get_completed_section_jobs(JobSection.POST)) == 0:
      self._add_warning("We couldn't find COMPLETED POST jobs in the experiment. ASYPD can't be calculated.")
    if len(self.get_completed_section_jobs(JobSection.TRANSFER)) == 0 and len(self.get_completed_section_jobs(JobSection.CLEAN)) == 0:
      self._add_warning("RSYPD | There are no TRANSFER nor CLEAN (COMPLETED) jobs in the experiment, RSYPD cannot be computed.")
    if len(self.get_completed_section_jobs(JobSection.TRANSFER)) == 0 and len(self.get_completed_section_jobs(JobSection.CLEAN)) > 0:
      self._add_warning("RSYPD | There are no TRANSFER (COMPLETED) jobs in the experiment. We will use (COMPLETED) CLEAN jobs to compute RSYPD.")

  def _add_warning(self, message: str):
    self.warnings.append(message)

  def _sort_list_by_finish_time(self, jobs: list[Job]):
    if len(jobs):
      jobs.sort(key = lambda x: x.finish, reverse=False)

  def _sort_list_by_start_time(self, jobs: list[Job]):
    if len(jobs):
      jobs.sort(key = lambda x: x.start, reverse=False)

  def __repr__(self):
    return "Total {0}\nSIM {1}\nPOST {2}\nTRANSFER {3}\nCLEAN {4}\nOPA [{5}]".format(
      len(self.current_content),
      len(self.sim_jobs),
      len(self.post_jobs),
      len(self.transfer_jobs),
      len(self.clean_jobs),
      len(self.opa_jobs)
    )
