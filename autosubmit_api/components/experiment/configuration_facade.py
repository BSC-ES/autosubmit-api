#!/usr/bin/env python
import os
from abc import ABCMeta, abstractmethod
from typing import List, Optional

from autosubmit_api.common.utils import (
  JobSection,
  datechunk_to_year,
  get_processors_number,
  timestamp_to_datetime_format,
)
from autosubmit_api.components.experiment.file_metadata import FileMetadata
from autosubmit_api.components.experiment.utils import (
  calculate_processing_elements,
)
from autosubmit_api.components.jobs.job_factory import SimJob
from autosubmit_api.components.jobs.job_section_config import JobSectionConfiguration
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.config.config_common import AutosubmitConfigResolver
from autosubmit_api.persistance.experiment import ExperimentPaths
from autosubmit_api.repositories.jobs import create_jobs_repository


class ProjectType:
  GIT = "git"
  SVN = "svn"

class ConfigurationFacade(metaclass=ABCMeta):
  """

  """

  def __init__(self, expid: str, basic_config: APIBasicConfig):
    self.basic_configuration: APIBasicConfig = basic_config
    self.expid: str = expid
    self.experiment_path: str = ""
    self.tmp_path: str = ""
    self.log_path: str = ""
    self.structures_path: str = ""
    self.warnings: List[str] = []
    self._process_basic_config()

  def _process_basic_config(self):
    exp_paths = ExperimentPaths(self.expid)
    self.experiment_path = exp_paths.exp_dir
    self.tmp_path = exp_paths.tmp_dir
    self.log_path = exp_paths.tmp_log_dir
    self.structures_path = self.basic_configuration.STRUCTURES_DIR
    if not os.path.exists(self.experiment_path):
      raise IOError("Experiment folder {0} not found".format(self.experiment_path))
    if not os.path.exists(self.tmp_path):
      raise IOError("Required folder {0} not found.".format(self.tmp_path))

  @abstractmethod
  def _process_advanced_config(self):
    pass

  @abstractmethod
  def get_autosubmit_version(self):
    pass

  @abstractmethod
  def get_model(self) -> str:
    pass

  @abstractmethod
  def get_branch(self) -> str:
    pass

  @abstractmethod
  def get_owner_name(self) -> str:
    pass

  @abstractmethod
  def get_owner_id(self) -> str:
    pass

class BasicConfigurationFacade(ConfigurationFacade):
  """ BasicConfig and paths """
  def __init__(self, expid: str, basic_config: APIBasicConfig):
    super(BasicConfigurationFacade, self).__init__(expid, basic_config)

  def _process_advanced_config(self):
    raise NotImplementedError

  def get_autosubmit_version(self):
    raise NotImplementedError

  def get_model(self):
    raise NotImplementedError

  def get_branch(self):
    raise NotImplementedError

  def get_owner_name(self):
    raise NotImplementedError

  def get_owner_id(self):
    raise NotImplementedError

class AutosubmitConfigurationFacade(ConfigurationFacade):
  """ Provides an interface to the Configuration of the experiment.  """
  def __init__(self, expid: str, basic_config: APIBasicConfig, autosubmit_config: AutosubmitConfigResolver):
    super(AutosubmitConfigurationFacade, self).__init__(expid, basic_config)
    self.autosubmit_conf = autosubmit_config
    self.file_metadata = FileMetadata(self.experiment_path)
    self.sim_section_config = JobSectionConfiguration(expid, JobSection.SIM, basic_config, autosubmit_config)
    self._process_advanced_config()

  def _process_advanced_config(self):
    """ Advanced Configuration from AutosubmitConfig """
    self.autosubmit_conf.reload()

  @property
  def chunk_unit(self) -> str:
    if not hasattr(self, '_chunk_unit'):
      self._chunk_unit = self.autosubmit_conf.get_chunk_size_unit()
    return self._chunk_unit

  @chunk_unit.setter
  def chunk_unit(self, value: str):
    self._chunk_unit = value
  
  @property
  def chunk_size(self) -> int:
    if not hasattr(self, '_chunk_size'):
      self._chunk_size = self.autosubmit_conf.get_chunk_size()
    return self._chunk_size

  @chunk_size.setter
  def chunk_size(self, value: int):
    self._chunk_size = value
  
  @property
  def current_years_per_sim(self) -> float:
    if not hasattr(self, '_current_years_per_sim'):
      self._current_years_per_sim = datechunk_to_year(self.chunk_unit, self.chunk_size)
    return self._current_years_per_sim

  @current_years_per_sim.setter
  def current_years_per_sim(self, value: float):
    self._current_years_per_sim = value
  
  @property
  def sim_processors(self) -> int:
    if not hasattr(self, '_sim_processors'):
      self._sim_processors = self.sim_section_config.processors
    return self._sim_processors

  @sim_processors.setter
  def sim_processors(self, value: int):
    self._sim_processors = value
  
  @property
  def sim_processing_elements(self) -> int:
    if not hasattr(self, '_sim_processing_elements'):
      self._sim_processing_elements = self._calculate_processing_elements()
    return self._sim_processing_elements

  @sim_processing_elements.setter
  def sim_processing_elements(self, value: int):
    self._sim_processing_elements = value

  @property
  def sim_tasks(self) -> Optional[int]:
    if not hasattr(self, '_sim_tasks'):
      self._sim_tasks = self.sim_section_config.tasks
    return self._sim_tasks

  @sim_tasks.setter
  def sim_tasks(self, value: Optional[int]):
    self._sim_tasks = value
  
  @property
  def sim_nodes(self) -> Optional[int]:
    if not hasattr(self, '_sim_nodes'):
      self._sim_nodes = self.sim_section_config.nodes
    return self._sim_nodes

  @sim_nodes.setter
  def sim_nodes(self, value: Optional[int]):
    self._sim_nodes = value
  
  @property
  def sim_processors_per_node(self) -> Optional[int]:
    if not hasattr(self, '_sim_processors_per_node'):
      self._sim_processors_per_node = self.sim_section_config.processors_per_node
    return self._sim_processors_per_node

  @sim_processors_per_node.setter
  def sim_processors_per_node(self, value: Optional[int]):
    self._sim_processors_per_node = value
  
  @property
  def sim_exclusive(self) -> bool:
    if not hasattr(self, '_sim_exclusive'):
      self._sim_exclusive = self.sim_section_config.exclusive
    return self._sim_exclusive

  @sim_exclusive.setter
  def sim_exclusive(self, value: bool):
    self._sim_exclusive = value

  def get_pkl_last_modified_timestamp(self) -> int:
    job_list_repo = create_jobs_repository(self.expid)
    return job_list_repo.get_last_modified_timestamp()

  def get_pkl_last_modified_time_as_datetime(self) -> str:
    return timestamp_to_datetime_format(self.get_pkl_last_modified_timestamp())

  def get_experiment_last_access_time_as_datetime(self) -> str:
    return self.file_metadata.access_time

  def get_experiment_last_modified_time_as_datetime(self) -> str:
    return self.file_metadata.modified_time

  def get_experiment_created_time_as_datetime(self) -> str:
    """ Important: Under OpenSUSE, it returns the last modified time."""
    return self.file_metadata.created_time

  def get_owner_id(self) -> int:
    return self.file_metadata.owner_id

  def get_owner_name(self) -> str:
    try:
      return self.file_metadata.owner_name
    except Exception:
      return "NA"

  def get_autosubmit_version(self) -> str:
    return self.autosubmit_conf.get_version()

  def get_main_platform(self):
    return str(self.autosubmit_conf.get_platform())

  def get_section_processors(self, section_name: str) -> int:
    return get_processors_number(str(self.autosubmit_conf.get_processors(section_name)))

  def get_section_qos(self, section_name):
    return str(self.autosubmit_conf.get_queue(section_name))

  def get_section_platform(self, section_name):
    return str(self.autosubmit_conf.get_job_platform(section_name))

  def get_platform_qos(self, platform_name: str, number_processors: int) -> str:
    if number_processors == 1:
      qos = str(self.autosubmit_conf.get_platform_serial_queue(platform_name))
      if len(qos.strip()) > 0:
        return qos
    return str(self.autosubmit_conf.get_platform_queue(platform_name))

  def get_wrapper_qos(self) -> str:
    return str(self.autosubmit_conf.get_wrapper_queue())

  def get_wrapper_type(self) -> Optional[str]:
    if self.autosubmit_conf.get_wrapper_type() and self.autosubmit_conf.get_wrapper_type().upper() != "NONE":
      return self.autosubmit_conf.get_wrapper_type().upper()
    return None

  def get_section_wallclock(self, section_name):
    return str(self.autosubmit_conf.get_wallclock(section_name))

  def get_platform_max_wallclock(self, platform_name):
    return str(self.autosubmit_conf.get_platform_wallclock(platform_name))
  
  def get_platorm_conf_footprint(self, platform_name):
    return self.autosubmit_conf.get_platform_conf_footprint(platform_name)

  def get_safety_sleep_time(self) -> int:
    return self.autosubmit_conf.get_safetysleeptime()

  def get_project_type(self) -> str:
    return self.autosubmit_conf.get_project_type()

  def get_model(self) -> str:
    if self.get_project_type() == ProjectType.GIT:
      return self.get_git_project_origin()
    elif self.get_project_type() == ProjectType.SVN:
      return self.get_svn_project_url()
    else:
      return "NA"

  def get_branch(self) -> str:
    if self.get_project_type() == ProjectType.GIT:
      return self.get_git_project_branch()
    elif self.get_project_type() == ProjectType.SVN:
      return self.get_svn_project_url()
    else:
      return "NA"

  def get_git_project_origin(self) -> str:
    return self.autosubmit_conf.get_git_project_origin()

  def get_git_project_branch(self) -> str:
    return self.autosubmit_conf.get_git_project_branch()

  def get_svn_project_url(self) -> str:
    return self.autosubmit_conf.get_svn_project_url()
  
  def get_workflow_commit(self) -> str:
    return self.autosubmit_conf.get_workflow_commit()

  def update_sim_jobs(self, sim_jobs: List[SimJob]):
    """ Update the jobs with the latest configuration values: Processors, years per sim """
    for job in sim_jobs:
      job.set_ncpus(self.sim_processing_elements)
      job.set_years_per_sim(self.current_years_per_sim)

  def _add_warning(self, message: str):
    self.warnings.append(message)

  def _calculate_processing_elements(self) -> int:
    return calculate_processing_elements(
      nodes=self.sim_nodes,
      processors=self.sim_processors,
      tasks=self.sim_tasks,
      processors_per_node=self.sim_processors_per_node,
      exclusive=self.sim_exclusive
    )
