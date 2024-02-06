

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


from autosubmit_api.database.db_manager import DbManager


class JobPackagePersistence(object):

    VERSION = 1
    JOB_PACKAGES_TABLE = 'job_package'
    WRAPPER_JOB_PACKAGES_TABLE = 'wrapper_job_package'
    TABLE_FIELDS = ['exp_id', 'package_name', 'job_name']

    def __init__(self, persistence_path, persistence_file):
        self.db_manager = DbManager(persistence_path, persistence_file, self.VERSION)
        # self.db_manager.create_table(self.JOB_PACKAGES_TABLE, self.TABLE_FIELDS)
        # self.db_manager.create_table(self.WRAPPER_JOB_PACKAGES_TABLE, self.TABLE_FIELDS)
    def load(self,wrapper=False):
        """
        Loads package of jobs from a database
        :param persistence_file: str
        :param persistence_path: str

        """
        if not wrapper:
            return self.db_manager.select_all(self.JOB_PACKAGES_TABLE)
        else:
            return self.db_manager.select_all(self.WRAPPER_JOB_PACKAGES_TABLE)
    def reset(self):
        """
        Loads package of jobs from a database
        :param persistence_file: str
        :param persistence_path: str

        """
        self.db_manager.drop_table(self.WRAPPER_JOB_PACKAGES_TABLE)
        self.db_manager.create_table(self.WRAPPER_JOB_PACKAGES_TABLE, self.TABLE_FIELDS)
