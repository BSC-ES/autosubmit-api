# References BasicConfig.DB_PATH

import autosubmit_api.history.database_managers.database_models as Models
from autosubmit_api.history.database_managers.database_manager import DatabaseManager
from autosubmit_api.config.basicConfig import BasicConfig
from typing import List

class ExperimentDbManager(DatabaseManager):
  # The current implementation only handles the experiment table. The details table is ignored because it is handled by a different worker.
  def __init__(self, basic_config, expid):
    # type: (BasicConfig, str) -> None
    super(ExperimentDbManager, self).__init__(expid, basic_config)
    self.basic_config = basic_config
    self._ecearth_file_path = self.basic_config.DB_PATH
  
  def get_experiment_row_by_expid(self, expid):
    # type: (str) -> Models.ExperimentRow | None
    """
    Get the experiment from ecearth.db by expid as Models.ExperimentRow.      
    """
    statement = self.get_built_select_statement("experiment", "name=?")
    current_rows = self.get_from_statement_with_arguments(self._ecearth_file_path, statement, (expid,))
    if len(current_rows) <= 0:   
      return None   
      # raise ValueError("Experiment {0} not found in {1}".format(expid, self._ecearth_file_path))
    return Models.ExperimentRow(*current_rows[0])
  
  def get_experiments_with_valid_version(self):
    # type: () ->  List[Models.ExperimentRow]
    statement = self.get_built_select_statement("experiment", "autosubmit_version IS NOT NULL")
    rows = self.get_from_statement(self._ecearth_file_path, statement)
    return [Models.ExperimentRow(*row) for row in rows]
  
  # def insert_experiment_details(self, exp_id, user, created, model, branch, hpc):
    
  #   statement = ''' INSERT INTO details(exp_id, user, created, model, branch, hpc) VALUES(?,?,?,?,?,?) '''
  #   arguments = (exp_id, user, status, 0, HUtils.get_current_datetime())
  #   return self.insert_statement_with_arguments(self._as_times_file_path, statement, arguments)