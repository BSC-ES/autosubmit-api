#!/usr/bin/env python

# Copyright 2017 Earth Sciences Department, BSC-CNS

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
from bscearth.utils.date import date2str, parse_date
from autosubmitAPIwu.autosubmit import Autosubmit
import autosubmitAPIwu.experiment.common_requests as ExperimentUtils
from autosubmitAPIwu.database.db_jobdata import JobDataStructure
from config.config_common import AutosubmitConfig
from config.basicConfig import BasicConfig
from autosubmitAPIwu.job.job_list import JobList
import autosubmitAPIwu.database.db_common as DbUtils
import autosubmitAPIwu.experiment.common_db_requests as DbRequests
import inspect
import cProfile
import sys
import time
import pickle
import os
import time
import datetime
sys.path.insert(0, os.path.abspath('.'))


def test_time_retrieval():
    submit, start, finish, status = JobList._job_running_check(
        5, 't0c0_19900101_fc0_2_SIM', '/esarchive/autosubmit/t0c0/tmp')
    print(submit)
    print(start)
    print(finish)
    print(status)
    print("\n")
    print(int(time.mktime(submit.timetuple())))
    print(int(time.mktime(start.timetuple())))
    print(int(time.mktime(finish.timetuple())))
    print((int(time.mktime(start.timetuple())) -
           int(time.mktime(submit.timetuple()))) / 60)
    print((int(time.mktime(finish.timetuple())) -
           int(time.mktime(start.timetuple()))) / 60)


def test_process_current_run(expid):
    BasicConfig.read()
    path_local_root = BasicConfig.LOCAL_ROOT_DIR
    path_structure = BasicConfig.STRUCTURES_DIR
    db_file = os.path.join(path_local_root, "ecearth.db")
    conn = DbRequests.create_connection(db_file)

    job_times = DbRequests.get_times_detail_by_expid(
        conn, expid)
    job_data, warning_messages = JobDataStructure(
        expid).process_current_run_collection(job_times, )

    for warning in warning_messages:
        print(warning)


def test_pickle():
    data = None
    with open('/esarchive/autosubmit/a29z/pkl/job_list_a29z.pkl', 'rb') as f:
        data = pickle.load(f)
    print(data[0])


def main():
    # ExperimentUtils.test_esarchive_status()
    # test_pickle()
    ExperimentUtils.get_experiment_tree_structured('a3jc')
    # cProfile.run(
    #     "ExperimentUtils.get_experiment_tree_structured('a2t4')", 'stats.dat')
    # result = ExperimentUtils.get_job_log(
    #     "/esarchive/autosubmit/a34n/tmp/LOG_a34n/a34n_19931101_fc0_1_SIM.20210121182125.out")
    # print(result)


if __name__ == "__main__":
    main()
