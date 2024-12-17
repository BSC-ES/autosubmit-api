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

from autosubmit_api.persistance.experiment import ExperimentPaths
from autosubmit_api.history.database_managers import database_models as Models
from autosubmit_api.history.data_classes.job_data import JobData
from autosubmit_api.history.data_classes.experiment_run import ExperimentRun
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.history.database_managers.database_manager import DatabaseManager
from typing import List, Optional
from collections import namedtuple

class ExperimentHistoryDbManager(DatabaseManager):
  """ Manages actions directly on the database.
  """
  def __init__(self, expid: str, basic_config: APIBasicConfig):
    """ Requires expid and jobdata_dir_path. """
    super(ExperimentHistoryDbManager, self).__init__(expid, basic_config)
    self._set_schema_changes()
    self._set_table_queries()
    exp_paths = ExperimentPaths(expid)
    self.historicaldb_file_path = exp_paths.job_data_db
    if self.my_database_exists():
      self.set_db_version_models()

  def initialize(self):
    """ Check if database exists. Updates to current version if necessary. """
    if self.my_database_exists():
      if not self.is_current_version():
        self.update_historical_database()
    else:
      self.create_historical_database()
    self.set_db_version_models()

  def set_db_version_models(self):
    self.db_version = self._get_pragma_version()
    self.experiment_run_row_model = Models.get_experiment_row_model(self.db_version)
    self.job_data_row_model = Models.get_job_data_row_model(self.db_version)

  def my_database_exists(self):
    return os.path.exists(self.historicaldb_file_path)

  def is_header_ready_db_version(self):
    if self.my_database_exists():
      return self._get_pragma_version() >= Models.DatabaseVersion.EXPERIMENT_HEADER_SCHEMA_CHANGES.value
    return False

  def is_current_version(self):
    if self.my_database_exists():
      return self._get_pragma_version() == Models.DatabaseVersion.CURRENT_DB_VERSION.value
    return False

  def _set_table_queries(self):
    """ Sets basic table queries. """
    self.create_table_header_query = textwrap.dedent(
      '''CREATE TABLE
      IF NOT EXISTS experiment_run (
      run_id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
      created TEXT NOT NULL,
      modified TEXT NOT NULL,
      start INTEGER NOT NULL,
      finish INTEGER,
      chunk_unit TEXT NOT NULL,
      chunk_size INTEGER NOT NULL,
      completed INTEGER NOT NULL,
      total INTEGER NOT NULL,
      failed INTEGER NOT NULL,
      queuing INTEGER NOT NULL,
      running INTEGER NOT NULL,
      submitted INTEGER NOT NULL,
      suspended INTEGER NOT NULL DEFAULT 0,
      metadata TEXT
      );
      ''')
    self.create_table_query = textwrap.dedent(
      '''CREATE TABLE
      IF NOT EXISTS job_data (
      id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
      counter INTEGER NOT NULL,
      job_name TEXT NOT NULL,
      created TEXT NOT NULL,
      modified TEXT NOT NULL,
      submit INTEGER NOT NULL,
      start INTEGER NOT NULL,
      finish INTEGER NOT NULL,
      status TEXT NOT NULL,
      rowtype INTEGER NOT NULL,
      ncpus INTEGER NOT NULL,
      wallclock TEXT NOT NULL,
      qos TEXT NOT NULL,
      energy INTEGER NOT NULL,
      date TEXT NOT NULL,
      section TEXT NOT NULL,
      member TEXT NOT NULL,
      chunk INTEGER NOT NULL,
      last INTEGER NOT NULL,
      platform TEXT NOT NULL,
      job_id INTEGER NOT NULL,
      extra_data TEXT NOT NULL,
      nnodes INTEGER NOT NULL DEFAULT 0,
      run_id INTEGER,
      MaxRSS REAL NOT NULL DEFAULT 0.0,
      AveRSS REAL NOT NULL DEFAULT 0.0,
      out TEXT NOT NULL,
      err TEXT NOT NULL,
      rowstatus INTEGER NOT NULL DEFAULT 0,
      children TEXT,
      platform_output TEXT,
      UNIQUE(counter,job_name)
      );
      ''')
    self.create_index_query = textwrap.dedent('''
      CREATE INDEX IF NOT EXISTS ID_JOB_NAME ON job_data(job_name);
      ''')

  def _set_schema_changes(self):
    """ Creates the list of schema changes"""
    self.version_schema_changes = [
      "ALTER TABLE job_data ADD COLUMN nnodes INTEGER NOT NULL DEFAULT 0",
      "ALTER TABLE job_data ADD COLUMN run_id INTEGER"
    ]
    # Version 15
    self.version_schema_changes.extend([
      "ALTER TABLE job_data ADD COLUMN MaxRSS REAL NOT NULL DEFAULT 0.0",
      "ALTER TABLE job_data ADD COLUMN AveRSS REAL NOT NULL DEFAULT 0.0",
      "ALTER TABLE job_data ADD COLUMN out TEXT NOT NULL DEFAULT ''",
      "ALTER TABLE job_data ADD COLUMN err TEXT NOT NULL DEFAULT ''",
      "ALTER TABLE job_data ADD COLUMN rowstatus INTEGER NOT NULL DEFAULT 0",
      "ALTER TABLE experiment_run ADD COLUMN suspended INTEGER NOT NULL DEFAULT 0",
      "ALTER TABLE experiment_run ADD COLUMN metadata TEXT"
    ])
    # Version 16
    self.version_schema_changes.extend([
      "ALTER TABLE experiment_run ADD COLUMN modified TEXT"
    ])
    # Version 17
    self.version_schema_changes.extend([
      "ALTER TABLE job_data ADD COLUMN children TEXT",
      "ALTER TABLE job_data ADD COLUMN platform_output TEXT"
    ])

  def create_historical_database(self):
    """ Creates the historical database with the latest changes. """
    self.execute_statement_on_dbfile(self.historicaldb_file_path, self.create_table_header_query)
    self.execute_statement_on_dbfile(self.historicaldb_file_path, self.create_table_query)
    self.execute_statement_on_dbfile(self.historicaldb_file_path, self.create_index_query)
    self._set_historical_pragma_version(Models.DatabaseVersion.CURRENT_DB_VERSION.value)

  def update_historical_database(self):
    """ Updates the historical database with the latest changes IF necessary. """
    self.execute_many_statements_on_dbfile(self.historicaldb_file_path, self.version_schema_changes)
    self.execute_statement_on_dbfile(self.historicaldb_file_path, self.create_index_query)
    self.execute_statement_on_dbfile(self.historicaldb_file_path, self.create_table_header_query)
    self._set_historical_pragma_version(Models.DatabaseVersion.CURRENT_DB_VERSION.value)

  def get_experiment_run_dc_with_max_id(self):
    """ Get Current (latest) ExperimentRun data class. """
    return ExperimentRun.from_model(self._get_experiment_run_with_max_id())

  def _get_experiment_run_with_max_id(self):
    """ Get Models.ExperimentRunRow for the maximum id run. """
    statement = self.get_built_select_statement("experiment_run", "run_id > 0 ORDER BY run_id DESC LIMIT 0, 1")
    max_experiment_run = self.get_from_statement(self.historicaldb_file_path, statement)
    if len(max_experiment_run) == 0:
      raise Exception("No Experiment Runs registered.")
    return self.experiment_run_row_model(*max_experiment_run[0])

  def get_experiment_run_by_id(self, run_id: int) -> Optional[ExperimentRun]:
    if run_id:
      return ExperimentRun.from_model(self._get_experiment_run_by_id(run_id))
    return None

  def _get_experiment_run_by_id(self, run_id: int) -> namedtuple:
    statement = self.get_built_select_statement("experiment_run", "run_id=?")
    arguments = (run_id,)
    experiment_run = self.get_from_statement_with_arguments(self.historicaldb_file_path, statement, arguments)
    if len(experiment_run) == 0:
      raise Exception("Experiment run {0} for experiment {1} does not exists.".format(run_id, self.expid))
    return self.experiment_run_row_model(*experiment_run[0])

  def get_experiment_runs_dcs(self) -> List[ExperimentRun]:
    experiment_run_rows = self._get_experiment_runs()
    return [ExperimentRun.from_model(row) for row in experiment_run_rows]

  def _get_experiment_runs(self) -> List[namedtuple]:
    statement = self.get_built_select_statement("experiment_run")
    experiment_runs = self.get_from_statement(self.historicaldb_file_path, statement)
    return [self.experiment_run_row_model(*row) for row in experiment_runs]

  def get_job_data_dcs_all(self) -> List[JobData]:
    """ Gets all content from job_data ordered by id (from table). """
    return [JobData.from_model(row) for row in self.get_job_data_all()]

  def get_job_data_all(self):
    """ Gets all content from job_data as list of Models.JobDataRow from database. """
    statement = self.get_built_select_statement("job_data", "id > 0 ORDER BY id")
    job_data_rows = self.get_from_statement(self.historicaldb_file_path, statement)
    return [self.job_data_row_model(*row) for row in job_data_rows]

  def get_job_data_dc_COMPLETED_by_wrapper_run_id(self, package_code: int, run_id: int) -> List[JobData]:
    if not run_id or package_code <= Models.RowType.NORMAL:
      return []
    job_data_rows = self._get_job_data_dc_COMPLETED_by_wrapper_run_id(package_code, run_id)
    if len(job_data_rows) == 0:
      return []
    return [JobData.from_model(row) for row in job_data_rows]

  def _get_job_data_dc_COMPLETED_by_wrapper_run_id(self, package_code: int, run_id: int) -> List[namedtuple]:
    statement = self.get_built_select_statement("job_data", "run_id=? and rowtype=? and status=? ORDER BY id")
    arguments = (run_id, package_code, "COMPLETED")
    job_data_rows = self.get_from_statement_with_arguments(self.historicaldb_file_path, statement, arguments)
    return [self.job_data_row_model(*row) for row in job_data_rows]

  def get_job_data_dcs_COMPLETED_by_section(self, section: str) -> List[JobData]:
    # arguments = {"status": "COMPLETED", "section": section}
    job_data_rows = self._get_job_data_COMPLETD_by_section(section)
    return [JobData.from_model(row) for row in job_data_rows]

  def _get_job_data_COMPLETD_by_section(self, section):
    statement = self.get_built_select_statement("job_data", "status=? and (section=? or member=?) ORDER BY id")
    arguments = ("COMPLETED", section, section)
    job_data_rows = self.get_from_statement_with_arguments(self.historicaldb_file_path, statement, arguments)
    return [self.job_data_row_model(*row) for row in job_data_rows]

  def get_all_last_job_data_dcs(self):
    """ Gets JobData data classes in job_data for last=1. """
    job_data_rows = self._get_all_last_job_data_rows()
    return [JobData.from_model(row) for row in job_data_rows]

  def _get_all_last_job_data_rows(self):
    """ Get List of Models.JobDataRow for last=1. """
    statement = self.get_built_select_statement("job_data", "last=1 and rowtype >= 2")
    job_data_rows = self.get_from_statement(self.historicaldb_file_path, statement)
    return [self.job_data_row_model(*row) for row in job_data_rows]

  def get_job_data_dcs_by_name(self, job_name: str) -> List[JobData]:
    job_data_rows = self._get_job_data_by_name(job_name)
    return [JobData.from_model(row) for row in job_data_rows]

  def _get_job_data_by_name(self, job_name: str) -> List[namedtuple]:
    """ Get List of Models.JobDataRow for job_name """
    statement = self.get_built_select_statement("job_data", "job_name=? ORDER BY counter DESC")
    arguments = (job_name,)
    job_data_rows = self.get_from_statement_with_arguments(self.historicaldb_file_path, statement, arguments)
    return [self.job_data_row_model(*row) for row in job_data_rows]

  def _set_historical_pragma_version(self, version=10):
    """ Sets the pragma version. """
    statement = "pragma user_version={v:d};".format(v=version)
    self.execute_statement_on_dbfile(self.historicaldb_file_path, statement)

  def _get_pragma_version(self) -> int:
    """ Gets current pragma version as int. """
    statement = "pragma user_version;"
    pragma_result = self.get_from_statement(self.historicaldb_file_path, statement)
    if len(pragma_result) <= 0:
      raise Exception("Error while getting the pragma version. This might be a signal of a deeper problem. Review previous errors.")
    return int(Models.PragmaVersion(*pragma_result[0]).version)
