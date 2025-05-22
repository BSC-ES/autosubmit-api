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

import json
from autosubmit_api.common import utils as common_utils
from autosubmit_api.history.utils import get_current_datetime_if_none
from autosubmit_api.history.data_classes.job_data import JobData
from autosubmit_api.components.jobs.job_factory import SimJob
from typing import List, Dict, Tuple


class DatabaseCorruptedException(Exception):
    """Exception raised when the database is corrupted or present issues in its schema.

    Attributes:
        databaseName -- nameID
        tableName -- TableID
        message -- error description
        sourceException -- original exception
    """

    def __init__(self, db, table, exp,
                 msg = "Database file seems corrupted or with wrong schema, please contact Autosubmit support team"):
        self.databaseName = db
        self.tableName = table
        self.sourceException = exp
        self.message = msg
        super().__init__(self.message)


class ExperimentRun(object):
    """
  Class that represents an experiment run
  """

    def __init__(self, run_id, created=None, modified=None, start=0, finish=0, chunk_unit="NA", chunk_size=0,
                 completed=0, total=0, failed=0, queuing=0, running=0, submitted=0, suspended=0, metadata=""):
        self.run_id = run_id
        self.created = get_current_datetime_if_none(created)
        self.modified = get_current_datetime_if_none(modified)  # Added on DB 16
        self.start = start
        self.finish = finish
        self.chunk_unit: str = chunk_unit
        self.chunk_size: int = chunk_size
        self.submitted: int = submitted
        self.queuing: int = queuing
        self.running: int = running
        self.completed: int = completed
        self.failed: int = failed
        self.total: int = total
        self.suspended: int = suspended
        self.metadata = metadata

    @property
    def created_timestamp(self):
        return common_utils.tostamp(self.created)

    @property
    def modified_timestamp(self):
        return common_utils.tostamp(self.modified)

    def get_wrapper_type(self):
        if self.metadata:
            data = json.loads(self.metadata)
            wrapper_section = data["conf"].get("wrapper", None)
            if wrapper_section:
                wrapper_type = wrapper_section.get("TYPE", None)
                if wrapper_type:
                    return wrapper_type
        return None

    def getSYPD(self, job_list: List[JobData]) -> float:
        outlier_free_list = []
        if job_list:
            performance_jobs = [SimJob.from_job_data_dc(job_data_dc) for job_data_dc in job_list]
            outlier_free_list = common_utils.get_jobs_with_no_outliers(performance_jobs)
        # print("{} -> {}".format(self.run_id, len(outlier_free_list)))
        if len(outlier_free_list) > 0:
            years_per_sim = common_utils.datechunk_to_year(self.chunk_unit, self.chunk_size)
            # print(self.run_id)
            # print(years_per_sim)
            seconds_per_day = 86400
            number_SIM = len(outlier_free_list)
            # print(len(job_list))
            total_run_time = sum(job.run_time for job in outlier_free_list)
            # print("run {3} yps {0} n {1} run_time {2}".format(years_per_sim, number_SIM, total_run_time, self.run_id))
            if total_run_time > 0:
                return round((years_per_sim * number_SIM * seconds_per_day) / total_run_time, 2)
        return None

    def getPSYPD(self, job_sim_list: List[JobData], job_post_list: List[JobData], run_id_wrapper_code_to_job_dcs: Dict[Tuple[int, int], List[JobData]]) -> float:
        try:
            SIM_no_outlier_list = []
            if job_sim_list and len(job_sim_list) > 0:
                performance_jobs = [SimJob.from_job_data_dc(job_data_dc) for job_data_dc in job_sim_list]
                SIM_no_outlier_list = common_utils.get_jobs_with_no_outliers(performance_jobs)
                valid_names = set([job.name for job in SIM_no_outlier_list])
                job_sim_list = [job for job in job_sim_list if job.job_name in valid_names]

            if job_sim_list and len(job_sim_list) > 0 and job_post_list and len(job_post_list) > 0:
                years_per_sim = common_utils.datechunk_to_year(self.chunk_unit, self.chunk_size)
                seconds_per_day = 86400
                number_SIM = len(job_sim_list)
                number_POST = len(job_post_list)
                average_POST = round(sum(job.queuing_time_considering_package(
                    run_id_wrapper_code_to_job_dcs.get((job.run_id, job.rowtype), [])) + job.running_time for job in
                                         job_post_list) / number_POST, 2)

                sum_SIM = round(sum(job.queuing_time_considering_package(
                    run_id_wrapper_code_to_job_dcs.get((job.run_id, job.rowtype), [])) + job.running_time for job in
                                    job_sim_list), 2)
                if (sum_SIM + average_POST) > 0:
                    return round((years_per_sim * number_SIM * seconds_per_day) / (sum_SIM + average_POST), 2)
            return None

        except Exception as exp:
            dbexception = DatabaseCorruptedException("job_list_XXX.db", "experiment_run", exp)
            raise dbexception

    @classmethod
    def from_model(cls, row):
        """ Build ExperimentRun from ExperimentRunRow """
        try:
            row_dict = row._asdict()
            experiment_run = cls(0)
            experiment_run.run_id = row_dict.get('run_id', 0)
            experiment_run.created = get_current_datetime_if_none(row_dict.get('created', None))
            experiment_run.modified = get_current_datetime_if_none(row_dict.get('modified', None))
            experiment_run.start = int(row_dict.get('start', 0))
            experiment_run.finish = int(row_dict.get('finish', 0))
            experiment_run.chunk_unit = row_dict.get('chunk_unit', None)
            experiment_run.chunk_size = row_dict.get('chunk_size', None)
            experiment_run.completed = int(row_dict.get('completed', 0))
            experiment_run.total = row_dict.get('total', 0)
            experiment_run.failed = row_dict.get('failed', 0)
            experiment_run.queuing = row_dict.get('queuing', 0)
            experiment_run.running = row_dict.get('running', 0)
            experiment_run.submitted = row_dict.get('submitted', 0)
            experiment_run.suspended = int(row_dict.get('suspended', 0))
            experiment_run.metadata = row_dict.get('metadata', "")
            return experiment_run
        except Exception as exp:
            dbexception = DatabaseCorruptedException("job_list_XXX.db", "experiment_run", exp)
            raise dbexception
