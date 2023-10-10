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
import time
import subprocess
from .experiment_status import ExperimentStatus
from ..config.basicConfig import BasicConfig
from ..experiment.common_requests import _is_exp_running
from ..common.utils import get_experiments_from_folder
from typing import Dict, Set
from .utils import SAFE_TIME_LIMIT_STATUS
from . import utils as HUtils



class ExperimentStatusManager(object):
  """ Manages the update of the status table. """
  def __init__(self):
    BasicConfig.read()
    self._basic_config = BasicConfig
    self._experiments_updated = set()
    self._local_root_path = self._basic_config.LOCAL_ROOT_DIR
    self._base_experiment_status = ExperimentStatus("0000")
    self._base_experiment_status.validate_database()
    self._validate_configuration()
    self._creation_timestamp = int(time.time())

  def _validate_configuration(self):
    # type: () -> None
    if not os.path.exists(self._local_root_path):
      raise Exception("Experiment Status Manager: LOCAL ROOT DIR not found.")

  def update_running_experiments(self, time_condition=600):
    # type: (int) -> None
    """
    Tests if an experiment is running and updates database as_times.db accordingly.\n
    :return: Nothing
    """

    # start_reading_folders = int(time.time())
    # currentDirectories = subprocess.Popen(['ls', '-t', self._local_root_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    # stdOut, _ = currentDirectories.communicate()
    # readingpkl = stdOut.split()
    # time_reading_folders = int(time.time()) - start_reading_folders
    readingpkl = get_experiments_from_folder(self._local_root_path)
    # Update those that are RUNNING
    for expid in readingpkl:
      pkl_path = os.path.join(self._local_root_path, str(expid), "pkl", "job_list_{0}.pkl".format(str(expid)))
      if not len(expid) == 4 or not os.path.exists(pkl_path):
        continue
      time_spent = int(time.time()) - self._creation_timestamp
      if time_spent > SAFE_TIME_LIMIT_STATUS:
        raise Exception(
            "Time limit reached {0} seconds on update_running_experiments while processing {1}. \
            Time spent on reading data {2} seconds.".format(time_spent, expid, time_reading_folders))
      time_diff = int(time.time()) - int(os.stat(pkl_path).st_mtime)
      if (time_diff < time_condition):
        self._experiments_updated.add(ExperimentStatus(expid).set_as_running().exp_id)
      elif (time_diff <= 3600):
        _, _ , is_running, _, _ = _is_exp_running(expid) # Exhaustive validation
        if is_running == True:
          self._experiments_updated.add(ExperimentStatus(expid).set_as_running().exp_id)
    # Update those that were RUNNING
    self._detect_and_delete_not_running()

  def _detect_and_delete_not_running(self):
    # type: () -> None
    current_rows = self._base_experiment_status.get_current_table_content()
    for experiment_status_row in current_rows:
      if experiment_status_row.status == "RUNNING" and experiment_status_row.exp_id not in self._experiments_updated:
        _, _, is_running, _, _ = _is_exp_running(experiment_status_row.name) # Exhaustive validation
        if is_running == False:
          ExperimentStatus(experiment_status_row.name).set_as_not_running()