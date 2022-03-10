#!/usr/bin/env python
from autosubmit_api.config.basicConfig import BasicConfig
from abc import ABCMeta

class BasicBuilder:
  __metaclass__ = ABCMeta

  def __init__(self, expid):
    # type: (str) -> None
    self.expid = expid
    
  def set_basic_config(self, basic_config):
    # type: (BasicConfig) -> None
    self.basic_config = basic_config

  def generate_basic_config(self):
    # type: () -> None
    BasicConfig.read()
    self.basic_config = BasicConfig 
  
  def _validate_basic_config(self):
    if not self.basic_config:
      raise Exception("BasicConfig is missing.")