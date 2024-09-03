#!/usr/bin/env python
from typing import Optional
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.config.config_common import AutosubmitConfigResolver
from autosubmit_api.builders.basic_builder import BasicBuilder
from autosubmit_api.components.experiment.configuration_facade import AutosubmitConfigurationFacade, BasicConfigurationFacade, ConfigurationFacade
from bscearth.utils.config_parser import ConfigParserFactory
from abc import ABCMeta, abstractmethod

class Builder(BasicBuilder, metaclass=ABCMeta):
  def __init__(self, expid: str):
    super(Builder, self).__init__(expid)

  @abstractmethod
  def generate_autosubmit_config(self):
    pass

  @abstractmethod
  def make_configuration_facade(self) -> ConfigurationFacade:
    pass

class BasicConfigurationBuilder(Builder):
  def __init__(self, expid: str):
    super(BasicConfigurationBuilder, self).__init__(expid)

  def generate_autosubmit_config(self):
    raise NotImplementedError

  def make_configuration_facade(self) -> ConfigurationFacade:
    if not self.basic_config:
      raise Exception("BasicConfig is missing.")
    return BasicConfigurationFacade(self.expid, self.basic_config)

class AutosubmitConfigurationFacadeBuilder(Builder):
  def __init__(self, expid: str):
    super(AutosubmitConfigurationFacadeBuilder, self).__init__(expid)

  def generate_autosubmit_config(self):
    self._validate_basic_config()
    self.autosubmit_config = AutosubmitConfigResolver(self.expid, self.basic_config, ConfigParserFactory())

  def make_configuration_facade(self) -> ConfigurationFacade:
    self._validate_basic_config()
    if not self.autosubmit_config:
      raise Exception("AutosubmitConfig is missing.")
    return AutosubmitConfigurationFacade(self.expid, self.basic_config, self.autosubmit_config)


class ConfigurationFacadeDirector(object):
  def __init__(self, builder: Builder):
    self.builder = builder

  def _set_basic_config(self, basic_config=None):
    if basic_config:
      self.builder.set_basic_config(basic_config)
    else:
      self.builder.generate_basic_config()

  def build_basic_configuration_facade(
      self, basic_config: Optional[APIBasicConfig] = None
  ) -> BasicConfigurationFacade:
    self._set_basic_config(basic_config)
    return self.builder.make_configuration_facade()

  def build_autosubmit_configuration_facade(
      self, basic_config: Optional[APIBasicConfig] = None
  ) -> AutosubmitConfigurationFacade:
    self._set_basic_config(basic_config)
    self.builder.generate_autosubmit_config()
    return self.builder.make_configuration_facade()