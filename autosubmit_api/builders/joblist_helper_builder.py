#!/usr/bin/env python
from autosubmitAPIwu.config.basicConfig import BasicConfig
from autosubmitAPIwu.builders.configuration_facade_builder import AutosubmitConfigurationFacadeBuilder, ConfigurationFacadeDirector
from autosubmitAPIwu.builders.basic_builder import BasicBuilder
from autosubmitAPIwu.builders.pkl_organizer_builder import PklOrganizerBuilder, PklOrganizerDirector
from autosubmitAPIwu.components.jobs.joblist_helper import JobListHelper
from abc import ABCMeta, abstractmethod


class Builder(BasicBuilder):
  __metaclass__ = ABCMeta

  def __init__(self, expid):
    # type: (str) -> None
    super(Builder, self).__init__(expid) 
  
  @abstractmethod
  def generate_autosubmit_configuration_facade(self):
    # type: () -> None
    pass

  @abstractmethod
  def generate_pkl_organizer(self):
    # type: () -> None
    pass

  @abstractmethod
  def make_joblist_helper(self):
    # type: () -> JobListHelper
    pass

class JobListHelperBuilder(Builder):
  def __init__(self, expid):
    # type: (str) -> None
    super(JobListHelperBuilder, self).__init__(expid)
  
  def _validate_autosubmit_configuration_facade(self):
    if not self.configuration_facade:
      raise Exception("AutosubmitConfigurationFacade is missing.")
  
  def _validate_pkl_organizer(self):
    if not self.pkl_organizer:
      raise Exception("PklOrganizer is missing.")
  
  def generate_autosubmit_configuration_facade(self):
    self._validate_basic_config()
    self.configuration_facade = ConfigurationFacadeDirector(AutosubmitConfigurationFacadeBuilder(self.expid)).build_autosubmit_configuration_facade(self.basic_config)

  def generate_pkl_organizer(self):
    self._validate_autosubmit_configuration_facade()
    self.pkl_organizer = PklOrganizerDirector(PklOrganizerBuilder(self.expid)).build_pkl_organizer_with_configuration_provided(self.configuration_facade)
  
  def make_joblist_helper(self):
    # type: () -> JobListHelper
    self._validate_basic_config()
    self._validate_autosubmit_configuration_facade()
    self._validate_pkl_organizer()
    return JobListHelper(self.expid, self.configuration_facade, self.pkl_organizer, self.basic_config)
  
class JobListHelperDirector:
  def __init__(self, builder):
    # type: (Builder) -> None
    self.builder = builder
  
  def _set_basic_config(self, basic_config=None):
    if basic_config:
      self.builder.set_basic_config(basic_config)
    else:
      self.builder.generate_basic_config()
  
  def build_job_list_helper(self, basic_config=None):
    # type: (BasicConfig) -> JobListHelper
    self._set_basic_config(basic_config)
    self.builder.generate_autosubmit_configuration_facade()
    self.builder.generate_pkl_organizer()
    return self.builder.make_joblist_helper()
