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

from autosubmit_api.history.database_managers import database_models as Models
from autosubmit_api.history.data_classes.job_data import JobData
from autosubmit_api.history.data_classes.experiment_run import ExperimentRun
from autosubmit_api.config.basicConfig import APIBasicConfig
from typing import List, Optional
from collections import namedtuple

from autosubmit_api.repositories.experiment_run import create_experiment_run_repository
from autosubmit_api.repositories.job_data import create_experiment_job_data_repository

class ExperimentHistoryDbManager:
  """ Manages actions directly on the database.
  """
  def __init__(self, expid: str, basic_config: APIBasicConfig):
    """ Requires expid """
    self.expid = expid
    self.set_db_version_models()

    self.runs_repo = create_experiment_run_repository(expid)
    self.jobs_repo = create_experiment_job_data_repository(expid)

  def set_db_version_models(self):
    # From version 3.13.0 of Autosubmit, latest model is used.
    self.experiment_run_row_model = Models.ExperimentRunRow
    self.job_data_row_model = Models.JobDataRow

  def get_experiment_run_dc_with_max_id(self):
    """ Get Current (latest) ExperimentRun data class. """
    return ExperimentRun.from_model(self._get_experiment_run_with_max_id())

  def _get_experiment_run_with_max_id(self):
    """ Get Models.ExperimentRunRow for the maximum id run. """
    max_experiment_run = self.runs_repo.get_last_run()
    return self.experiment_run_row_model(**(max_experiment_run.model_dump()))

  def get_experiment_run_by_id(self, run_id: int) -> Optional[ExperimentRun]:
    if run_id:
      return ExperimentRun.from_model(self._get_experiment_run_by_id(run_id))
    return None

  def _get_experiment_run_by_id(self, run_id: int) -> namedtuple:
    experiment_run = self.runs_repo.get_run_by_id(run_id)
    return self.experiment_run_row_model(**(experiment_run.model_dump()))

  def get_experiment_runs_dcs(self) -> List[ExperimentRun]:
    experiment_run_rows = self._get_experiment_runs()
    return [ExperimentRun.from_model(row) for row in experiment_run_rows]

  def _get_experiment_runs(self) -> List[namedtuple]:
    experiment_runs = self.runs_repo.get_all()
    return [
      self.experiment_run_row_model(**(run.model_dump()))
      for run in experiment_runs
    ]

  def get_job_data_dcs_all(self) -> List[JobData]:
    """ Gets all content from job_data ordered by id (from table). """
    return [JobData.from_model(row) for row in self._get_job_data_all()]

  def _get_job_data_all(self):
    """ Gets all content from job_data as list of Models.JobDataRow from database. """
    job_data_rows = self.jobs_repo.get_all()
    return [
      self.job_data_row_model(**(job_data.model_dump()))
      for job_data in job_data_rows
    ]

  def get_job_data_dc_COMPLETED_by_wrapper_run_id(self, package_code: int, run_id: int) -> List[JobData]:
    if not run_id or package_code <= Models.RowType.NORMAL:
      return []
    job_data_rows = self._get_job_data_dc_COMPLETED_by_wrapper_run_id(package_code, run_id)
    if len(job_data_rows) == 0:
      return []
    return [JobData.from_model(row) for row in job_data_rows]

  def _get_job_data_dc_COMPLETED_by_wrapper_run_id(self, package_code: int, run_id: int) -> List[namedtuple]:
    job_data_rows = self.jobs_repo.get_job_data_COMPLETED_by_rowtype_run_id(package_code, run_id)
    return [
      self.job_data_row_model(**(job_data.model_dump()))
      for job_data in job_data_rows
    ]

  def get_job_data_dcs_COMPLETED_by_section(self, section: str) -> List[JobData]:
    # arguments = {"status": "COMPLETED", "section": section}
    job_data_rows = self._get_job_data_COMPLETD_by_section(section)
    return [JobData.from_model(row) for row in job_data_rows]

  def _get_job_data_COMPLETD_by_section(self, section):
    job_data_rows = self.jobs_repo.get_job_data_COMPLETD_by_section(section)
    return [
      self.job_data_row_model(**(job_data.model_dump()))
      for job_data in job_data_rows
    ]

  def get_all_last_job_data_dcs(self):
    """ Gets JobData data classes in job_data for last=1. """
    job_data_rows = self._get_all_last_job_data_rows()
    return [JobData.from_model(row) for row in job_data_rows]

  def _get_all_last_job_data_rows(self):
    """ Get List of Models.JobDataRow for last=1. """
    job_data_rows = self.jobs_repo.get_last_job_data()
    return [
      self.job_data_row_model(**(job_data.model_dump()))
      for job_data in job_data_rows
    ]

  def get_job_data_dcs_by_name(self, job_name: str) -> List[JobData]:
    job_data_rows = self._get_job_data_by_name(job_name)
    return [JobData.from_model(row) for row in job_data_rows]

  def _get_job_data_by_name(self, job_name: str) -> List[namedtuple]:
    """ Get List of Models.JobDataRow for job_name """
    job_data_rows = self.jobs_repo.get_jobs_by_name(job_name)
    return [
      self.job_data_row_model(**(job_data.model_dump()))
      for job_data in job_data_rows
    ]
