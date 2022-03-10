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

import pickle
from sys import setrecursionlimit

import os

from bscearth.utils.log import Log
from autosubmitAPIwu.database.db_manager import DbManager


class JobListPersistence(object):
    """
    Class to manage the persistence of the job lists

    """

    def save(self, persistence_path, persistence_file, job_list):
        """
        Persists a job list
        :param job_list: JobList
        :param persistence_file: str
        :param persistence_path: str

        """
        raise NotImplementedError

    def load(self, persistence_path, persistence_file):
        """
        Loads a job list from persistence
        :param persistence_file: str
        :param persistence_path: str

        """
        raise NotImplementedError


class JobListPersistencePkl(JobListPersistence):
    """
    Class to manage the pickle persistence of the job lists

    """

    EXT = '.pkl'

    def load(self, persistence_path, persistence_file):
        """
        Loads a job list from a pkl file
        :param persistence_file: str
        :param persistence_path: str

        """
        path = os.path.join(persistence_path, persistence_file + '.pkl')
        if os.path.exists(path):
            file_size = os.stat(path).st_size
            # print("{} size {}".format(path, file_size))
            if file_size <= 6:
                raise AssertionError(
                    "Your pkl file seems to be empty. Make sure that you are running Autosubmit. See the FAQ tab for more information.")
            fd = open(path, 'r')
            return pickle.load(fd)
        else:
            raise AssertionError(
                "The pkl file of your experiment does not exist. Make sure that you are running Autosubmit. Try again, if the error keeps happening see the FAQ tab for more information.")
            # Log.critical('File {0} does not exist'.format(path))
            return list()

    def save(self, persistence_path, persistence_file, job_list):
        """
        Persists a job list in a pkl file
        :param job_list: JobList
        :param persistence_file: str
        :param persistence_path: str

        """
        # The API does not save
        pass
        # path = os.path.join(persistence_path, persistence_file + '.pkl')
        # fd = open(path, 'w')
        # setrecursionlimit(50000)
        # Log.debug("Saving JobList: " + path)
        # jobs_data = [(job.name, job.id, job.status,
        #               job.priority, job.section, job.date,
        #               job.member, job.chunk,
        #               job.local_logs[0], job.local_logs[1],
        #               job.remote_logs[0], job.remote_logs[1]) for job in job_list]
        # pickle.dump(jobs_data, fd)
        # Log.debug('Job list saved')


class JobListPersistenceDb(JobListPersistence):
    """
    Class to manage the database persistence of the job lists

    """

    VERSION = 3
    JOB_LIST_TABLE = 'job_list'
    TABLE_FIELDS = ['name', 'id', 'status', 'priority',
                    'section', 'date', 'member', 'chunk',
                    'local_out', 'local_err',
                    'remote_out', 'remote_err']

    def __init__(self, persistence_path, persistence_file):
        self.db_manager = DbManager(
            persistence_path, persistence_file, self.VERSION)

    def load(self, persistence_path, persistence_file):
        """
        Loads a job list from a database
        :param persistence_file: str
        :param persistence_path: str

        """
        return self.db_manager.select_all(self.JOB_LIST_TABLE)

    def save(self, persistence_path, persistence_file, job_list):
        """
        Persists a job list in a database
        :param job_list: JobList
        :param persistence_file: str
        :param persistence_path: str

        """
        self._reset_table()
        jobs_data = [(job.name, job.id, job.status,
                      job.priority, job.section, job.date,
                      job.member, job.chunk,
                      job.local_logs[0], job.local_logs[1],
                      job.remote_logs[0], job.remote_logs[1]) for job in job_list]
        self.db_manager.insertMany(self.JOB_LIST_TABLE, jobs_data)

    def _reset_table(self):
        """
        Drops and recreates the database

        """
        self.db_manager.drop_table(self.JOB_LIST_TABLE)
        self.db_manager.create_table(self.JOB_LIST_TABLE, self.TABLE_FIELDS)
