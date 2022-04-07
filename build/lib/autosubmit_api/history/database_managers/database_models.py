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

import collections
from enum import Enum

class DatabaseVersion(Enum):
  CURRENT_DB_VERSION = 18
  EXPERIMENT_HEADER_PLATFORM_ADDED = 17
  EXPERIMENT_HEADER_SCHEMA_CHANGES = 14
  JOB_DATA_CHANGES = 12
  DEFAULT_DB_VERSION = 10
  NO_DATABASE = -1

JobDataRow = collections.namedtuple('JobDataRow', ['id', 'counter', 'job_name', 'created', 'modified', 'submit', 'start', 'finish', 
                                                  'status', 'rowtype', 'ncpus', 'wallclock', 'qos', 'energy', 'date', 'section', 'member', 
                                                  'chunk', 'last', 'platform', 'job_id', 'extra_data', 'nnodes', 'run_id', 'MaxRSS', 'AveRSS', 
                                                  'out', 'err', 'rowstatus', 'children', 'platform_output'])

JobDataRow10 = collections.namedtuple('JobItem', ['id', 'counter', 'job_name', 'created', 'modified', 'submit', 'start', 'finish',
                                                'status', 'rowtype', 'ncpus', 'wallclock', 'qos', 'energy', 'date', 'section', 'member', 'chunk', 'last', 'platform', 'job_id', 'extra_data'])
JobDataRow12 = collections.namedtuple('JobItem', ['id', 'counter', 'job_name', 'created', 'modified', 'submit', 'start', 'finish',
                                                'status', 'rowtype', 'ncpus', 'wallclock', 'qos', 'energy', 'date', 'section', 'member', 'chunk', 'last', 'platform', 'job_id', 'extra_data', 'nnodes', 'run_id'])
JobDataRow15 = collections.namedtuple('JobItem', ['id', 'counter', 'job_name', 'created', 'modified', 'submit', 'start', 'finish',
                                                'status', 'rowtype', 'ncpus', 'wallclock', 'qos', 'energy', 'date', 'section', 'member', 'chunk', 'last', 'platform', 'job_id', 'extra_data', 'nnodes', 'run_id', 'MaxRSS', 'AveRSS', 'out', 'err', 'rowstatus'])

ExperimentRunRow = collections.namedtuple('ExperimentRunRow', [
                                           'run_id', 'created', 'modified', 'start', 'finish', 'chunk_unit', 'chunk_size', 'completed', 'total', 'failed', 'queuing', 'running', 'submitted', 'suspended', 'metadata'])

ExperimentRunRow14 = collections.namedtuple('ExperimentRunRow', ['run_id', 'created', 'start', 'finish', 'chunk_unit', 'chunk_size', 'completed', 'total', 'failed', 'queuing', 'running', 'submitted', 'suspended', 'metadata'])

ExperimentRunRowBase = collections.namedtuple('ExperimentRunRow', ['run_id', 'created', 'start', 'finish', 'chunk_unit', 'chunk_size', 'completed', 'total', 'failed', 'queuing', 'running', 'submitted'])

ExperimentStatusRow = collections.namedtuple('ExperimentStatusRow', ['exp_id', 'name', 'status', 'seconds_diff', 'modified'])




def get_experiment_row_model(db_version):
  # type: (int) -> collections.namedtuple
  if db_version >= DatabaseVersion.EXPERIMENT_HEADER_PLATFORM_ADDED.value:    
    return ExperimentRunRow
  elif db_version >= DatabaseVersion.EXPERIMENT_HEADER_SCHEMA_CHANGES.value:    
    return ExperimentRunRow14
  else:    
    return ExperimentRunRowBase

def get_job_data_row_model(db_version):
  # type: (int) -> collections.namedtuple
  if db_version >= DatabaseVersion.EXPERIMENT_HEADER_PLATFORM_ADDED.value:
    return JobDataRow
  elif db_version >= DatabaseVersion.EXPERIMENT_HEADER_SCHEMA_CHANGES.value:
    return JobDataRow15
  elif db_version >= DatabaseVersion.JOB_DATA_CHANGES.value:
    return JobDataRow12
  else:
    return JobDataRow10



ExperimentRow = collections.namedtuple('ExperimentRow', ["id", "name", "autosubmit_version", "description"])

PragmaVersion = collections.namedtuple('PragmaVersion', ['version'])
MaxCounterRow = collections.namedtuple('MaxCounter', ['maxcounter'])

class RunningStatus:
  RUNNING = "RUNNING"
  NOT_RUNNING = "NOT RUNNING"

class RowType:
    NORMAL = 2
    #PACKED = 2

class RowStatus:
    INITIAL = 0
    COMPLETED = 1    
    PROCESSED = 2
    FAULTY = 3
    CHANGED = 4
    PENDING_PROCESS = 5

table_name_to_model = {
  "experiment" : ExperimentRow,
  "experiment_status" : ExperimentStatusRow,
  "job_data" : JobDataRow,
  "experiment_run" : ExperimentRunRow,
  "pragma_version" : PragmaVersion
}

def get_correct_model_for_table_and_version(table_name, db_version=0):
  # type: (str, int) -> collections.namedtuple
  if table_name == "experiment_run":
    return get_experiment_row_model(db_version)
  elif table_name == "job_data":
    return get_job_data_row_model(db_version)
  else:
    return table_name_to_model[table_name]
