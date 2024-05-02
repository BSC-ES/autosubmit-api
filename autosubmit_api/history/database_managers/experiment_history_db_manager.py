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
from typing import Any, Dict, List, Optional

from autosubmit_api.database.repositories import ExperimentRunDbRepository, JobDataDbRepository
from autosubmit_api.persistance.experiment import ExperimentPaths
from autosubmit_api.history.database_managers import database_models as Models
from autosubmit_api.history.data_classes.job_data import JobData
from autosubmit_api.history.data_classes.experiment_run import ExperimentRun


class ExperimentHistoryDbManager:
    """Manages history DDBB actions directly on the database."""

    def __init__(self, expid: str):
        """Requires expid"""
        self.expid = expid
        self.run_db = ExperimentRunDbRepository(expid)
        self.job_data_db = JobDataDbRepository(expid)
        self.historicaldb_file_path = ExperimentPaths(expid).job_data_db

    def my_database_exists(self) -> bool:
        return os.path.exists(self.historicaldb_file_path)

    def get_experiment_run_dc_with_max_id(self) -> ExperimentRun:
        """Get Current (latest) ExperimentRun data class."""
        return ExperimentRun.from_model(self._get_experiment_run_with_max_id())

    def _get_experiment_run_with_max_id(self) -> Dict[str, Any]:
        """Get Models.ExperimentRunRow for the maximum id run."""
        max_experiment_run = self.run_db.get_last_run()
        if not max_experiment_run:
            raise Exception("No Experiment Runs registered.")
        return max_experiment_run

    def get_experiment_run_by_id(self, run_id: int) -> Optional[ExperimentRun]:
        if run_id:
            return ExperimentRun.from_model(self._get_experiment_run_by_id(run_id))
        return None

    def _get_experiment_run_by_id(self, run_id: int) -> Dict[str, Any]:
        experiment_run = self.run_db.get_run_by_id(run_id)
        if not experiment_run:
            raise Exception(
                "Experiment run {0} for experiment {1} does not exists.".format(
                    run_id, self.expid
                )
            )
        return experiment_run

    def get_experiment_runs_dcs(self) -> List[ExperimentRun]:
        experiment_run_rows = self._get_experiment_runs()
        return [ExperimentRun.from_model(row) for row in experiment_run_rows]

    def _get_experiment_runs(self):
        experiment_runs = self.run_db.get_all()
        return experiment_runs

    def get_job_data_dcs_all(self) -> List[JobData]:
        """Gets all content from job_data ordered by id (from table)."""
        return [JobData.from_model(row) for row in self.get_job_data_all()]

    def get_job_data_all(self):
        """Gets all content from job_data as list of Models.JobDataRow from database."""
        job_data_rows = self.job_data_db.get_all()
        return job_data_rows

    def get_job_data_dc_COMPLETED_by_wrapper_run_id(
        self, package_code: int, run_id: int
    ) -> List[JobData]:
        if not run_id or package_code <= Models.RowType.NORMAL:
            return []
        job_data_rows = self._get_job_data_dc_COMPLETED_by_wrapper_run_id(
            package_code, run_id
        )
        if len(job_data_rows) == 0:
            return []
        return [JobData.from_model(row) for row in job_data_rows]

    def _get_job_data_dc_COMPLETED_by_wrapper_run_id(
        self, package_code: int, run_id: int
    ) -> List[Dict[str, Any]]:
        job_data_rows = self.job_data_db.get_job_data_COMPLETED_by_rowtype_run_id(
            rowtype=package_code, run_id=run_id
        )
        return job_data_rows

    def get_job_data_dcs_COMPLETED_by_section(self, section: str) -> List[JobData]:
        job_data_rows = self._get_job_data_COMPLETD_by_section(section)
        return [JobData.from_model(row) for row in job_data_rows]

    def _get_job_data_COMPLETD_by_section(self, section: str) -> List[Dict[str, Any]]:
        job_data_rows = self.job_data_db.get_job_data_COMPLETD_by_section(section)
        return job_data_rows

    def get_all_last_job_data_dcs(self):
        """Gets JobData data classes in job_data for last=1."""
        job_data_rows = self._get_all_last_job_data_rows()
        return [JobData.from_model(row) for row in job_data_rows]

    def _get_all_last_job_data_rows(self):
        """Get List of Models.JobDataRow for last=1."""
        job_data_rows = self.job_data_db.get_last_job_data()
        return job_data_rows

    def get_job_data_dcs_by_name(self, job_name: str) -> List[JobData]:
        job_data_rows = self._get_job_data_by_name(job_name)
        return [JobData.from_model(row) for row in job_data_rows]

    def _get_job_data_by_name(self, job_name: str) -> List[Dict[str, Any]]:
        """Get List of Models.JobDataRow for job_name"""
        job_data_rows = self.job_data_db.get_jobs_by_name(job_name)
        return job_data_rows
