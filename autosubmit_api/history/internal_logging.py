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
import utils as HUtils
# from database_managers.database_manager import DEFAULT_LOCAL_ROOT_DIR, DEFAULT_HISTORICAL_LOGS_DIR
from autosubmit_api.config.basicConfig import BasicConfig

class Logging():
  def __init__(self, expid, basic_config):
    # type: (str, BasicConfig) -> None
    self.expid = expid
    self.historiclog_dir_path = basic_config.HISTORICAL_LOG_DIR
    self._make_log_directory_if_not_exists()  

  def log(self, main_msg, traceback_msg=""):
    try:
      log_path = self.get_log_file_path()
      HUtils.get_current_datetime()
      if not os.path.exists(log_path):
        HUtils.create_file_with_full_permissions(log_path)
      with open(log_path, "a") as exp_log:
        exp_log.write(self.build_message(main_msg, traceback_msg))
    except Exception as exp:
      print(exp)
      print("Logging failed. Please report it to the developers.")  
    
  def build_message(self, main_msg, traceback_msg):
    return "{0} :: {1} :: {2}\n".format(HUtils.get_current_datetime(), main_msg, traceback_msg)

  def _make_log_directory_if_not_exists(self):
    if not os.path.exists(self.historiclog_dir_path):
      os.makedirs(self.historiclog_dir_path)

  def get_log_file_path(self):     
    return os.path.join(self.historiclog_dir_path,"{}_log.txt".format(self.expid))