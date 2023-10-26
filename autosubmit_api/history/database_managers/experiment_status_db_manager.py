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

import os
import textwrap
import time

from autosubmit_api.experiment.common_db_requests import prepare_status_db
from .database_manager import DatabaseManager, DEFAULT_LOCAL_ROOT_DIR
from ...config.basicConfig import APIBasicConfig
from ...history import utils as HUtils
from ...history.database_managers import database_models as Models
from typing import List

class ExperimentStatusDbManager(DatabaseManager):
  """ Manages the actions on the status database """
  def __init__(self, expid, basic_config):
    # type: (str, APIBasicConfig) -> None
    super(ExperimentStatusDbManager, self).__init__(expid, basic_config)
    self._as_times_file_path = os.path.join(APIBasicConfig.DB_DIR, self.AS_TIMES_DB_NAME)
    self._ecearth_file_path = os.path.join(APIBasicConfig.DB_DIR, APIBasicConfig.DB_FILE)
    self._pkl_file_path = os.path.join(APIBasicConfig.LOCAL_ROOT_DIR, self.expid, "pkl", "job_list_{0}.pkl".format(self.expid))
    self.default_experiment_status_row = Models.ExperimentStatusRow(0, "DEFAULT", "NOT RUNNING", 0, "")


  def validate_status_database(self):
      """ Creates experiment_status table if it does not exist """
      prepare_status_db()
      # Redundant code
      # create_table_query = textwrap.dedent(
      #     '''CREATE TABLE
      #         IF NOT EXISTS experiment_status (
      #         exp_id integer PRIMARY KEY,
      #         name text NOT NULL,
      #         status text NOT NULL,
      #         seconds_diff integer NOT NULL,
      #         modified text NOT NULL
      #     );'''
      # )
      # self.execute_statement_on_dbfile(self._as_times_file_path, create_table_query)

  def print_current_table(self):
      for experiment in self._get_experiment_status_content():
          print(experiment)
      if self.current_experiment_status_row:
          print(("Current Row:\n\t" + self.current_experiment_status_row.name + "\n\t" +
                str(self.current_experiment_status_row.exp_id) + "\n\t" + self.current_experiment_status_row.status))

  def get_experiment_table_content(self):
    # type: () -> List[Models.ExperimentStatusRow]
    return self._get_experiment_status_content()

  def is_running(self, time_condition=600):
      # type : (int) -> bool
      """ True if experiment is running, False otherwise. """
      if (os.path.exists(self._pkl_file_path)):
          current_stat = os.stat(self._pkl_file_path)
          timest = int(current_stat.st_mtime)
          timesys = int(time.time())
          time_diff = int(timesys - timest)
          if (time_diff < time_condition):
              return True
          else:
              return False
      return False

  def set_existing_experiment_status_as_running(self, expid):
    """ Set the experiment_status row as running. """
    self.update_exp_status(expid, Models.RunningStatus.RUNNING)

  def create_experiment_status_as_running(self, experiment):
    """ Create a new experiment_status row for the Models.Experiment item."""
    self.create_exp_status(experiment.id, experiment.name, Models.RunningStatus.RUNNING)


  def get_experiment_status_row_by_expid(self, expid):
    # type: (str) -> Models.ExperimentStatusRow | None
    """
    Get Models.ExperimentStatusRow by expid. Uses exp_id (int id) as an intermediate step and validation.
    """
    experiment_row = self.get_experiment_row_by_expid(expid)
    return self.get_experiment_status_row_by_exp_id(experiment_row.id) if experiment_row else None

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

  def _get_experiment_status_content(self):
    # type: () -> List[Models.ExperimentStatusRow]
    """
    Get all registers from experiment_status as List of Models.ExperimentStatusRow.\n
    """
    statement = self.get_built_select_statement("experiment_status")
    current_rows = self.get_from_statement(self._as_times_file_path, statement)
    return [Models.ExperimentStatusRow(*row) for row in current_rows]

  def get_experiment_status_row_by_exp_id(self, exp_id):
    # type: (int) -> Models.ExperimentStatusRow
    """ Get Models.ExperimentStatusRow from as_times.db by exp_id (int)"""
    statement = self.get_built_select_statement("experiment_status", "exp_id=?")
    arguments = (exp_id,)
    current_rows = self.get_from_statement_with_arguments(self._as_times_file_path, statement, arguments)
    if len(current_rows) <= 0:
      return None
    return Models.ExperimentStatusRow(*current_rows[0])


  def create_exp_status(self, exp_id, expid, status):
    # type: (int, str, str) -> None
    """
    Create experiment status
    """
    statement = ''' INSERT INTO experiment_status(exp_id, name, status, seconds_diff, modified) VALUES(?,?,?,?,?) '''
    arguments = (exp_id, expid, status, 0, HUtils.get_current_datetime())
    return self.insert_statement_with_arguments(self._as_times_file_path, statement, arguments)

  def update_exp_status(self, expid, status="RUNNING"):
    # type: (str, str) -> None
    """
    Update status, seconds_diff, modified in experiment_status.
    """
    statement = ''' UPDATE experiment_status SET status = ?, seconds_diff = ?, modified = ? WHERE name = ? '''
    arguments = (status, 0, HUtils.get_current_datetime(), expid)
    self.execute_statement_with_arguments_on_dbfile(self._as_times_file_path, statement, arguments)

  def delete_exp_status(self, expid):
    # type: (str) -> None
    """ Deletes experiment_status row by expid. Useful for testing purposes. """
    statement = ''' DELETE FROM experiment_status where name = ? '''
    arguments = (expid,)
    self.execute_statement_with_arguments_on_dbfile(self._as_times_file_path, statement, arguments)