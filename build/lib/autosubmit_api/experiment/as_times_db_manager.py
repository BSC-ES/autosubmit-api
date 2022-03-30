# References BasicConfig.DB_DIR + BasicConfig.AS_TIMES_DB
import os
import autosubmit_api.history.database_managers.database_models as Models
from autosubmit_api.history.database_managers.database_manager import DatabaseManager
from autosubmit_api.config.basicConfig import BasicConfig
from typing import List

class ASTimesDbManager(DatabaseManager):
  def __init__(self, basic_config, expid):
    # type: (BasicConfig, str) -> None
    super(DatabaseManager, self).__init__(expid, basic_config)
    self.basic_config = basic_config
    self._as_times_file_path = os.path.join(self.basic_config.DB_DIR, self.basic_config.AS_TIMES_DB)
  
  