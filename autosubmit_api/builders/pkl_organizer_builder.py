#!/usr/bin/env python
from typing import Optional
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.components.experiment.pkl_organizer import PklOrganizer
from autosubmit_api.builders.configuration_facade_builder import AutosubmitConfigurationFacadeBuilder, ConfigurationFacadeDirector
from autosubmit_api.builders.basic_builder import BasicBuilder
from autosubmit_api.components.experiment.configuration_facade import AutosubmitConfigurationFacade

class PklOrganizerBuilder(BasicBuilder):
  def __init__(self, expid: str):
    super(PklOrganizerBuilder, self).__init__(expid)

  def set_autosubmit_configuration_facade(self, configuration_facade: AutosubmitConfigurationFacade):
    self.configuration_facade = configuration_facade

  def generate_autosubmit_configuration_facade(self):
    self._validate_basic_config()
    self.configuration_facade = ConfigurationFacadeDirector(AutosubmitConfigurationFacadeBuilder(self.expid)).build_autosubmit_configuration_facade(self.basic_config)

  def _validate_autosubmit_configuration_facade(self):
    if not self.configuration_facade:
      raise Exception("AutosubmitConfigurationFacade is missing.")

  def make_pkl_organizer(self) -> PklOrganizer:
    self._validate_basic_config()
    self._validate_autosubmit_configuration_facade()
    return PklOrganizer(self.configuration_facade)

class PklOrganizerDirector:
  def __init__(self, builder: PklOrganizerBuilder):
    self.builder = builder

  def _set_basic_config(self, basic_config=None):
    if basic_config:
      self.builder.set_basic_config(basic_config)
    else:
      self.builder.generate_basic_config()

  def build_pkl_organizer(self, basic_config: Optional[APIBasicConfig] = None) -> PklOrganizer:
    self._set_basic_config(basic_config)
    self.builder.generate_autosubmit_configuration_facade()
    return self.builder.make_pkl_organizer()

  def build_pkl_organizer_with_configuration_provided(self, configuration_facade: AutosubmitConfigurationFacade) -> PklOrganizer:
    self._set_basic_config(configuration_facade.basic_configuration)
    self.builder.set_autosubmit_configuration_facade(configuration_facade)
    return self.builder.make_pkl_organizer()