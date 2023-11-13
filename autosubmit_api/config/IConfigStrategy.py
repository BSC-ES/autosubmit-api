#!/usr/bin/env python

# Copyright 2015 Earth Sciences Department, BSC-CNS

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

try:
    # noinspection PyCompatibility
    from configparser import SafeConfigParser
    from autosubmitconfigparser.config.configcommon import AutosubmitConfig as Autosubmit4Config
except ImportError:
    # noinspection PyCompatibility
    from configparser import SafeConfigParser


import os
import re
import subprocess
import json
import logging
import locale

from pyparsing import nestedExpr
from bscearth.utils.config_parser import ConfigParserFactory, ConfigParser
from bscearth.utils.date import parse_date
from bscearth.utils.log import Log
from ..config.basicConfig import APIBasicConfig
from abc import ABC, abstractmethod


class IConfigStrategy(ABC):
    """
    Public interface for Autosubmit config files

    :param expid: experiment identifier
    :type expid: str
    """

    @abstractmethod
    def jobs_parser(self):
        raise NotImplementedError

    @abstractmethod
    def experiment_file(self):
        """
        Returns experiment's config file name
        """
        return self._exp_parser_file

    @abstractmethod
    def platforms_parser(self):
        """
        Returns experiment's platforms parser object

        :return: platforms config parser object
        :rtype: SafeConfigParser
        """
        pass

    @abstractmethod
    def platforms_file(self):
        """
        Returns experiment's platforms config file name

        :return: platforms config file's name
        :rtype: str
        """
        pass

    @abstractmethod
    def project_file(self):
        """
        Returns project's config file name
        """
        pass

    @abstractmethod
    def jobs_file(self):
        """
        Returns project's jobs file name
        """
        pass

    @abstractmethod
    def get_full_config_as_dict(self):
        """
        Returns full configuration as json object
        """
        pass

    @abstractmethod
    def get_project_dir(self):
        """
        Returns experiment's project directory

        :return: experiment's project directory
        :rtype: str
        """
        pass

    @abstractmethod
    def get_queue(self, section):
        """
        Get queue for the given job type
        :param section: job type
        :type section: str
        :return: queue
        :rtype: str
        """
        pass

    @abstractmethod
    def get_job_platform(self, section: str) -> str:
        """
        Gets wallclock for the given job type
        :param section: job type
        :return: wallclock time
        """
        pass

    @abstractmethod
    def get_platform_queue(self, platform):
        pass

    @abstractmethod
    def get_platform_serial_queue(self, platform):
        pass

    @abstractmethod
    def get_platform_project(self, platform):
        pass

    @abstractmethod
    def get_platform_wallclock(self, platform):
        pass

    def get_wallclock(self, section):
        """
        Gets wallclock for the given job type
        :param section: job type
        :type section: str
        :return: wallclock time
        :rtype: str
        """
        pass

    def get_synchronize(self, section):
        """
        Gets wallclock for the given job type
        :param section: job type
        :type section: str
        :return: wallclock time
        :rtype: str
        """
        pass

    def get_processors(self, section: str) -> str:
        """
        Gets processors needed for the given job type
        :param section: job type
        :return: wallclock time
        """
        pass

    def get_threads(self, section):
        """
        Gets threads needed for the given job type
        :param section: job type
        :type section: str
        :return: threads needed
        :rtype: str
        """
        pass

    def get_tasks(self, section):
        """
        Gets tasks needed for the given job type
        :param section: job type
        :type section: str
        :return: tasks (processes) per host
        :rtype: str
        """
        pass

    def get_scratch_free_space(self, section):
        """
        Gets scratch free space needed for the given job type
        :param section: job type
        :type section: str
        :return: percentage of scratch free space needed
        :rtype: int
        """
        pass

    def get_memory(self, section):
        """
        Gets memory needed for the given job type
        :param section: job type
        :type section: str
        :return: memory needed
        :rtype: str
        """
        pass

    def get_memory_per_task(self, section):
        """
        Gets memory per task needed for the given job type
        :param section: job type
        :type section: str
        :return: memory per task needed
        :rtype: str
        """
        pass

    def get_migrate_user_to(self, section):
        """
        Returns the user to change to from platform config file.

        :return: migrate user to
        :rtype: str
        """
        #return self._platforms_parser.get_option(section, 'USER_TO', '').lower()
        pass

    def get_current_user(self, section):
        """
        Returns the user to be changed from platform config file.

        :return: migrate user to
        :rtype: str
        """
        pass

    def get_current_project(self, section):
        """
        Returns the project to be changed from platform config file.

        :return: migrate user to
        :rtype: str
        """
        return str(self._platforms_data[section]["USER"]).lower()

    def set_new_user(self, section, new_user):
        """
        Sets new user for given platform
        :param new_user:
        :param section: platform name
        :type: str
        """
        pass

    def get_migrate_project_to(self, section):
        """
        Returns the project to change to from platform config file.

        :return: migrate project to
        :rtype: str
        """
        pass



    def set_new_project(self, section, new_project):
        """
        Sets new project for given platform
        :param new_project:
        :param section: platform name
        :type: str
        """
        pass


    def get_custom_directives(self, section):
        """
        Gets custom directives needed for the given job type
        :param section: job type
        :type section: str
        :return: custom directives needed
        :rtype: str
        """
        pass


    def check_conf_files(self):
        """
        Checks configuration files (autosubmit, experiment jobs and platforms), looking for invalid values, missing
        required options. Prints results in log

        :return: True if everything is correct, False if it finds any error
        :rtype: bool
        """
        pass

    def check_autosubmit_conf(self):
        """
        Checks experiment's autosubmit configuration file.

        :return: True if everything is correct, False if it founds any error
        :rtype: bool
        """
        pass

    def check_platforms_conf(self):
        """
        Checks experiment's queues configuration file.

        :return: True if everything is correct, False if it founds any error
        :rtype: bool
        """


    def check_jobs_conf(self):
        """
        Checks experiment's jobs configuration file.

        :return: True if everything is correct, False if it founds any error
        :rtype: bool
        """
        pass


    def check_expdef_conf(self):
        """
        Checks experiment's experiment configuration file.

        :return: True if everything is correct, False if it founds any error
        :rtype: bool
        """
        pass


    def check_proj(self):
        """
        Checks project config file

        :return: True if everything is correct, False if it founds any error
        :rtype: bool
        """
        pass


    def check_wrapper_conf(self):
        pass


    def reload(self):
        """
        Creates parser objects for configuration files
        """
        pass

    def load_parameters(self):
        """
        Load parameters from experiment and autosubmit config files. If experiment's type is not none,
        also load parameters from model's config file

        :return: a dictionary containing tuples [parameter_name, parameter_value]
        :rtype: dict
        """


    def load_project_parameters(self):
        """
        Loads parameters from model config file

        :return: dictionary containing tuples [parameter_name, parameter_value]
        :rtype: dict
        """
        pass


    def set_expid(self, exp_id):
        """
        Set experiment identifier in autosubmit and experiment config files

        :param exp_id: experiment identifier to store
        :type exp_id: str
        """


    def get_project_type(self):
        """
        Returns project type from experiment config file

        :return: project type
        :rtype: str
        """
        pass

    def get_file_project_conf(self):
        """
        Returns path to project config file from experiment config file

        :return: path to project config file
        :rtype: str
        """
        pass

    def get_file_jobs_conf(self):
        """
        Returns path to project config file from experiment config file

        :return: path to project config file
        :rtype: str
        """


    def get_git_project_origin(self):
        """
        Returns git origin from experiment config file

        :return: git origin
        :rtype: str
        """

    def get_git_project_branch(self):
        """
        Returns git branch  from experiment's config file

        :return: git branch
        :rtype: str
        """

    def get_git_project_commit(self):
        """
        Returns git commit from experiment's config file

        :return: git commit
        :rtype: str
        """

    def get_submodules_list(self):
        """
        Returns submodules list from experiment's config file
        Default is --recursive
        :return: submodules to load
        :rtype: list
        """

    def get_project_destination(self):
        """
        Returns git commit from experiment's config file

        :return: git commit
        :rtype: str
        """


    def set_git_project_commit(self, as_conf):
        """
        Function to register in the configuration the commit SHA of the git project version.
        :param as_conf: Configuration class for exteriment
        :type as_conf: AutosubmitConfig
        """

    def get_svn_project_url(self):
        """
        Gets subversion project url

        :return: subversion project url
        :rtype: str
        """

    def get_svn_project_revision(self):
        """
        Get revision for subversion project

        :return: revision for subversion project
        :rtype: str
        """

    def get_local_project_path(self):
        """
        Gets path to origin for local project

        :return: path to local project
        :rtype: str
        """

    def get_date_list(self):
        """
        Returns startdates list from experiment's config file

        :return: experiment's startdates
        :rtype: list
        """


    def get_num_chunks(self):
        """
        Returns number of chunks to run for each member

        :return: number of chunks
        :rtype: int
        """

    def get_chunk_ini(self, default=1):
        """
        Returns the first chunk from where the experiment will start

        :param default:
        :return: initial chunk
        :rtype: int
        """


    def get_chunk_size_unit(self):
        # type: () -> str
        """
        Unit for the chunk length

        :return: Unit for the chunk length  Options: {hour, day, month, year}
        :rtype: str
        """

        pass

    def get_chunk_size(self, default=1):
        # type: (int) -> int
        """
        Chunk Size as defined in the expdef file.

        :return: Chunksize, 1 as default.
        :rtype: int
        """
        pass

    def get_member_list(self, run_only=False):
        """
        Returns members list from experiment's config file

        :return: experiment's members
        :rtype: list
        """
        pass

    def get_rerun(self):
        """
        Returns startdates list from experiment's config file

        :return: rerurn value
        :rtype: list
        """

        pass

    def get_chunk_list(self):
        """
        Returns chunk list from experiment's config file

        :return: experiment's chunks
        :rtype: list
        """
        pass

    def get_platform(self):
        """
        Returns main platforms from experiment's config file

        :return: main platforms
        :rtype: str
        """
        pass

    def set_platform(self, hpc):
        """
        Sets main platforms in experiment's config file

        :param hpc: main platforms
        :type: str
        """
        pass

    def set_version(self, autosubmit_version):
        """
        Sets autosubmit's version in autosubmit's config file

        :param autosubmit_version: autosubmit's version
        :type autosubmit_version: str
        """
        pass

    def get_version(self):
        """
        Returns version number of the current experiment from autosubmit's config file

        :return: version
        :rtype: str
        """
        pass

    def get_total_jobs(self):
        """
        Returns max number of running jobs  from autosubmit's config file

        :return: max number of running jobs
        :rtype: int
        """
        pass

    def get_max_wallclock(self):
        """
        Returns max wallclock

        :rtype: str
        """
        pass

    def get_max_processors(self):
        """
        Returns max processors from autosubmit's config file

        :rtype: str
        """
        pass

    def get_max_waiting_jobs(self):
        """
        Returns max number of waiting jobs from autosubmit's config file

        :return: main platforms
        :rtype: int
        """
        pass

    def get_default_job_type(self):
        """
        Returns the default job type from experiment's config file

        :return: default type such as bash, python, r..
        :rtype: str
        """
        pass

    def get_safetysleeptime(self):
        """
        Returns safety sleep time from autosubmit's config file

        :return: safety sleep time
        :rtype: int
        """
        pass

    def set_safetysleeptime(self, sleep_time):
        """
        Sets autosubmit's version in autosubmit's config file

        :param sleep_time: value to set
        :type sleep_time: int
        """
        pass

    def get_retrials(self):
        """
        Returns max number of retrials for job from autosubmit's config file

        :return: safety sleep time
        :rtype: int
        """
        pass

    def get_notifications(self):
        """
        Returns if the user has enabled the notifications from autosubmit's config file

        :return: if notifications
        :rtype: string
        """
        pass

    def get_remote_dependencies(self):
        """
        Returns if the user has enabled the remote dependencies from autosubmit's config file

        :return: if remote dependencies
        :rtype: bool
        """
        pass

    def get_wrapper_type(self):
        """
        Returns what kind of wrapper (VERTICAL, MIXED-VERTICAL, HORIZONTAL, HYBRID, NONE) the user has configured in the autosubmit's config

        :return: wrapper type (or none)
        :rtype: string
        """
        pass

    def get_wrapper_jobs(self):
        """
        Returns the jobs that should be wrapped, configured in the autosubmit's config

        :return: expression (or none)
        :rtype: string
        """
        pass

    def get_max_wrapped_jobs(self):
        """
         Returns the maximum number of jobs that can be wrapped together as configured in autosubmit's config file

         :return: maximum number of jobs (or total jobs)
         :rtype: string
         """
        # return int(self._conf_parser.get_option('wrapper', 'MAXWRAPPEDJOBS', self.get_total_jobs()))

        pass

    def get_wrapper_check_time(self):
         """
         Returns time to check the status of jobs in the wrapper

         :return: wrapper check time
         :rtype: int
         """
         pass

    def get_wrapper_machinefiles(self):
        """
        Returns the strategy for creating the machinefiles in wrapper jobs

        :return: machinefiles function to use
        :rtype: string
        """
        pass

    def get_wrapper_queue(self):
        """
        Returns the wrapper queue if not defined, will be the one of the first job wrapped

        :return: expression (or none)
        :rtype: string
        """
        pass

    def get_jobs_sections(self):
        """
        Returns the list of sections defined in the jobs config file

        :return: sections
        :rtype: list
        """
        return self._jobs_parser.sections()

    def get_copy_remote_logs(self):
        """
        Returns if the user has enabled the logs local copy from autosubmit's config file

        :return: if logs local copy
        :rtype: bool
        """
        pass

    def get_mails_to(self):
        """
        Returns the address where notifications will be sent from autosubmit's config file

        :return: mail address
        :rtype: [str]
        """
        pass

    def get_communications_library(self):
        """
        Returns the communications library from autosubmit's config file. Paramiko by default.

        :return: communications library
        :rtype: str
        """
        pass

    def get_storage_type(self):
        """
        Returns the communications library from autosubmit's config file. Paramiko by default.

        :return: communications library
        :rtype: str
        """
        pass

    @staticmethod
    def is_valid_mail_address(mail_address):
        if re.match('^[_a-z0-9-]+(\.[_a-z0-9-]+)*@[a-z0-9-]+(\.[a-z0-9-]+)*(\.[a-z]{2,4})$', mail_address):
            return True
        else:
            return False
    
    def is_valid_communications_library(self):
        library = self.get_communications_library()
        return library in ['paramiko', 'saga']

    def is_valid_storage_type(self):
        storage_type = self.get_storage_type()
        return storage_type in ['pkl', 'db']


    def is_valid_jobs_in_wrapper(self):
        pass

    def is_valid_git_repository(self):
       pass

    @staticmethod
    def get_parser(parser_factory, file_path):
        # type: (ConfigParserFactory, str) -> ConfigParser
        pass