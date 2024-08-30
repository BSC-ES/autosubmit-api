#!/usr/bin/env python
from autosubmit_api.config.basicConfig import APIBasicConfig
from abc import ABCMeta

class BasicBuilder(metaclass=ABCMeta):
  def __init__(self, expid: str) -> None:
    self.expid = expid

  def set_basic_config(self, basic_config: APIBasicConfig) -> None:
    self.basic_config = basic_config

  def generate_basic_config(self) -> None:
    APIBasicConfig.read()
    self.basic_config = APIBasicConfig

  def _validate_basic_config(self) -> None:
    if not self.basic_config:
      raise Exception("BasicConfig is missing.")