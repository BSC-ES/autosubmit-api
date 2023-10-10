#!/usr/bin/env python

# Copyright 2015-2020 Earth Sciences Department, BSC-CNS
# This file is part of Autosubmit.

# Autosubmit is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Autosubmit is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Autosubmit.  If not, see <http://www.gnu.org/licenses/>.

import traceback
from .database_managers.experiment_status_db_manager import ExperimentStatusDbManager
from .database_managers.database_manager import DEFAULT_LOCAL_ROOT_DIR, DEFAULT_HISTORICAL_LOGS_DIR
from .internal_logging import Logging
from ..config.basicConfig import BasicConfig
from typing import List
from .database_managers.database_models import ExperimentStatusRow

class ExperimentStatus():
  """ Represents the Experiment Status Mechanism that keeps track of currently active experiments """
  def __init__(self, expid):
    # type: (str) -> None
    self.expid = expid # type: str
    print(expid)
    BasicConfig.read()
    try:
      self.manager = ExperimentStatusDbManager(self.expid, BasicConfig)
    except Exception as exp:
      message = "Error while trying to update {0} in experiment_status.".format(str(self.expid))
      print(message)
      print(str(exp))
      print()
      Logging(self.expid, BasicConfig).log(message, traceback.format_exc())
      self.manager = None

  def validate_database(self):
    # type: () -> None
    self.manager.validate_status_database()

  def get_current_table_content(self):
    # type: () -> List[ExperimentStatusRow]
    return self.manager.get_experiment_table_content()

  def set_as_running(self):
    # type: () -> ExperimentStatusRow
    """ Set the status of the experiment in experiment_status of as_times.db as RUNNING. Inserts row if necessary."""
    if not self.manager:
      raise Exception("ExperimentStatus: The database manager is not available.")
    exp_status_row = self.manager.get_experiment_status_row_by_expid(self.expid)
    if exp_status_row:
      self.manager.set_existing_experiment_status_as_running(exp_status_row.name)
      return self.manager.get_experiment_status_row_by_expid(self.expid)
    else:
      exp_row = self.manager.get_experiment_row_by_expid(self.expid)
      if exp_row:
        self.manager.create_experiment_status_as_running(exp_row)
        return self.manager.get_experiment_status_row_by_expid(self.expid)
      else:
        print(("Couldn't find {} in the main database. There is not enough information to set it as running.".format(self.expid)))
        return self.manager.default_experiment_status_row


  def set_as_not_running(self):
    # type: () -> None
    """ Deletes row by expid. """
    if not self.manager:
      raise Exception("ExperimentStatus: The database manager is not available.")
    exp_status_row = self.manager.get_experiment_status_row_by_expid(self.expid)
    if not exp_status_row:
      # raise Exception("ExperimentStatus: Query error, experiment {} not found in status table.".format(self.expid))
      pass # If it is not in the status table, we don't need to worry about it.
    else:
      self.manager.delete_exp_status(exp_status_row.name)
