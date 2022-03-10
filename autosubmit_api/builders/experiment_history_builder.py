#!/usr/bin/env python
from autosubmit_api.history.experiment_history import ExperimentHistory
from autosubmit_api.history.internal_logging import Logging
from autosubmit_api.config.basicConfig import BasicConfig
from autosubmit_api.history.database_managers.experiment_history_db_manager import ExperimentHistoryDbManager
from autosubmit_api.builders.basic_builder import BasicBuilder
from abc import ABCMeta, abstractmethod

class Builder(BasicBuilder):
  __metaclass__ = ABCMeta

  def __init__(self, expid):
    # type: (str) -> None
    super(Builder, self).__init__(expid)    

  @abstractmethod
  def generate_experiment_history_db_manager(self):
    # type: () -> None
    pass

  @abstractmethod
  def initialize_experiment_history_db_manager(self):
    # type; () -> None
    pass
  
  @abstractmethod
  def generate_logger(self):
    # type: () -> None
    pass
  
  @abstractmethod
  def make_experiment_history(self):
    # type: () -> ExperimentHistory
    pass

class ExperimentHistoryBuilder(Builder):
  def __init__(self, expid):
    # type: (str) -> None
    super(ExperimentHistoryBuilder, self).__init__(expid)
  
  def generate_experiment_history_db_manager(self):
    # type: () -> None
    self._validate_basic_config()
    self.experiment_history_db_manager = ExperimentHistoryDbManager(self.expid, self.basic_config)
  
  def initialize_experiment_history_db_manager(self):
    # type: () -> None
    if not self.experiment_history_db_manager:
      raise Exception("Experiment Database Manager is missing")
    self.experiment_history_db_manager.initialize()
  
  def generate_logger(self):
    # type: () -> None
    self._validate_basic_config()
    self.logger = Logging(self.expid, self.basic_config)

  def make_experiment_history(self):
    # type: () -> ExperimentHistory
    self._validate_basic_config()
    if not self.experiment_history_db_manager:
      raise Exception("Experiment Database Manager is missing")
    if not self.logger:
      raise Exception("Logging is missing.")   
    return ExperimentHistory(self.expid, self.basic_config, self.experiment_history_db_manager, self.logger)

class ExperimentHistoryDirector(object):
  def __init__(self, builder):
    # type: (Builder) -> None
    self.builder = builder
  
  def build_current_experiment_history(self, basic_config=None):    
    # type: (BasicConfig) -> ExperimentHistory
    """ Builds ExperimentHistory updated to current version. """
    if basic_config:
      self.builder.set_basic_config(basic_config)
    else:
      self.builder.generate_basic_config()
    self.builder.generate_experiment_history_db_manager()
    self.builder.initialize_experiment_history_db_manager()
    self.builder.generate_logger()
    return self.builder.make_experiment_history()
  
  def build_reader_experiment_history(self, basic_config=None):
    # type: (BasicConfig) -> ExperimentHistory
    """ Buids ExperimentHistory that doesn't update to current version automatically. """
    if basic_config:
      self.builder.set_basic_config(basic_config)
    else:
      self.builder.generate_basic_config()
    self.builder.generate_experiment_history_db_manager()
    self.builder.generate_logger()
    return self.builder.make_experiment_history()
