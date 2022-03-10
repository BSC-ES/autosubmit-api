#!/usr/bin/env python
from autosubmitAPIwu.config.basicConfig import BasicConfig
from autosubmitAPIwu.config.config_common import AutosubmitConfig
from autosubmitAPIwu.builders.basic_builder import BasicBuilder
from autosubmitAPIwu.components.experiment.configuration_facade import AutosubmitConfigurationFacade, BasicConfigurationFacade, ConfigurationFacade
from bscearth.utils.config_parser import ConfigParserFactory
from abc import ABCMeta, abstractmethod

class Builder(BasicBuilder):
  __metaclass__ = ABCMeta

  def __init__(self, expid):
    # type: (str) -> None
    super(Builder, self).__init__(expid)  

  @abstractmethod
  def generate_autosubmit_config(self):
    # type: () -> None
    pass

  @abstractmethod
  def make_configuration_facade(self):
    # type: () -> ConfigurationFacade
    pass

class BasicConfigurationBuilder(Builder):
  def __init__(self, expid):
    # type: (str) -> None
    super(BasicConfigurationBuilder, self).__init__(expid)

  def generate_autosubmit_config(self):
    raise NotImplementedError
  
  def make_configuration_facade(self):
    # type: () -> ConfigurationFacade
    if not self.basic_config:
      raise Exception("BasicConfig is missing.")
    return BasicConfigurationFacade(self.expid, self.basic_config)

class AutosubmitConfigurationFacadeBuilder(Builder):
  def __init__(self, expid):
    # type: (str) -> None
    super(AutosubmitConfigurationFacadeBuilder, self).__init__(expid)
  
  def generate_autosubmit_config(self):
    self._validate_basic_config()
    self.autosubmit_config = AutosubmitConfig(self.expid, self.basic_config, ConfigParserFactory())
  
  def make_configuration_facade(self):
    # type: () -> ConfigurationFacade
    self._validate_basic_config()
    if not self.autosubmit_config:
      raise Exception("AutosubmitConfig is missing.")
    return AutosubmitConfigurationFacade(self.expid, self.basic_config, self.autosubmit_config)
  

class ConfigurationFacadeDirector(object):
  def __init__(self, builder):
    # type: (Builder) -> None
    self.builder = builder

  def _set_basic_config(self, basic_config=None):
    if basic_config:
      self.builder.set_basic_config(basic_config)
    else:
      self.builder.generate_basic_config()
  
  def build_basic_configuration_facade(self, basic_config=None):
    # type: (BasicConfig) -> BasicConfigurationFacade
    self._set_basic_config(basic_config)
    return self.builder.make_configuration_facade()

  def build_autosubmit_configuration_facade(self, basic_config=None):
    # type: (BasicConfig) -> AutosubmitConfigurationFacade
    self._set_basic_config(basic_config)
    self.builder.generate_autosubmit_config()
    return self.builder.make_configuration_facade()