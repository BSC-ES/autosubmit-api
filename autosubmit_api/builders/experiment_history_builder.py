#!/usr/bin/python3.7
from typing import Optional
from autosubmit_api.history.experiment_history import ExperimentHistory
from autosubmit_api.history.internal_logging import Logging
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.history.database_managers.experiment_history_db_manager import ExperimentHistoryDbManager
from autosubmit_api.builders.basic_builder import BasicBuilder
from abc import ABCMeta, abstractmethod

class Builder(BasicBuilder, metaclass=ABCMeta):
  def __init__(self, expid: str):
    super(Builder, self).__init__(expid)

  @abstractmethod
  def generate_experiment_history_db_manager(self):
    pass

  @abstractmethod
  def generate_logger(self):
    pass

  @abstractmethod
  def make_experiment_history(self) -> ExperimentHistory:
    pass

class ExperimentHistoryBuilder(Builder):
  def __init__(self, expid: str):
    super(ExperimentHistoryBuilder, self).__init__(expid)

  def generate_experiment_history_db_manager(self):
    self._validate_basic_config()
    self.experiment_history_db_manager = ExperimentHistoryDbManager(self.expid, self.basic_config)

  def generate_logger(self):
    self._validate_basic_config()
    self.logger = Logging(self.expid, self.basic_config)

  def make_experiment_history(self) -> ExperimentHistory:
    self._validate_basic_config()
    if not self.experiment_history_db_manager:
      raise Exception("Experiment Database Manager is missing")
    else:
      if not self.experiment_history_db_manager.my_database_exists():
        raise Exception("Job/Runs database does not exist")
    if not self.logger:
      raise Exception("Logging is missing.")
    return ExperimentHistory(self.expid, self.basic_config, self.experiment_history_db_manager, self.logger)

class ExperimentHistoryDirector(object):
  def __init__(self, builder: Builder):
    self.builder = builder

  def build_reader_experiment_history(self, basic_config: Optional[APIBasicConfig] = None) -> ExperimentHistory:
    """ Buids ExperimentHistory that doesn't update to current version automatically. """
    if basic_config:
      self.builder.set_basic_config(basic_config)
    else:
      self.builder.generate_basic_config()
    self.builder.generate_experiment_history_db_manager()
    self.builder.generate_logger()
    return self.builder.make_experiment_history()
