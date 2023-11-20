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

from typing import Any
from autosubmitconfigparser.config.configcommon import AutosubmitConfig as Autosubmit4Config
from autosubmit_api.logger import logger
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.config.IConfigStrategy import IConfigStrategy


class ymlConfigStrategy(IConfigStrategy):
    """
    Class to handle experiment configuration coming from file or database

    :param expid: experiment identifier
    :type expid: str
    """
    def __init__(self, expid, basic_config = APIBasicConfig, parser_factory = None, extension=".yml"):
        # logger.info("Creating AS4 Parser !!!!!")
        self._conf_parser = Autosubmit4Config(expid, basic_config)
        self._conf_parser.reload(True)

    def jobs_parser(self):
        logger.error("Not yet implemented")
        pass

    #TODO: at the end of the implementation, check which methods can be moved to the top class for avoid code duplication
    @property
    def experiment_file(self):
        """
        Returns experiment's config file name
        """
        return self._exp_parser_file

    def platforms_parser(self):
        logger.error("OBSOLOTED - Not yet implemented")
        pass

    @property
    def platforms_file(self):
        """
        Returns experiment's platforms config file name

        :return: platforms config file's name
        :rtype: str
        """
        return self._platforms_parser_file

    @property
    def project_file(self):
        """
        Returns project's config file name
        """
        return self._proj_parser_file

    @property
    def jobs_file(self):
        """
        Returns project's jobs file name
        """
        return self._jobs_parser_file

    def get_full_config_as_dict(self) -> dict:
        """
        Returns full configuration as json object
        """
        return self._conf_parser.experiment_data
    
    def _get_platform_config(self, platform: str) -> dict:
        return self._conf_parser.experiment_data.get("PLATFORMS", {}).get(platform, {})

    def _get_from_job_or_platform(self, section: str, config_key: str, default_value = None) -> Any:
        """
        Helper function to get a value from a JOB section of its related PLATFORM
        """
        # Check in job
        logger.debug("Checking " + config_key + " in JOBS")
        value = self._conf_parser.jobs_data.get(section, {}).get(config_key)
        if value:
            return value

        # Check in job platform
        logger.debug("Checking " + config_key + " in PLATFORMS " + self.get_job_platform(section))
        value = self._get_platform_config(self.get_job_platform(section)).get(config_key)
        if value:
            return value
        else:
            return default_value

    def get_full_config_as_json(self):
        return self._conf_parser.get_full_config_as_json()

    def get_project_dir(self):
        return self._conf_parser.get_project_dir()

    def get_queue(self, section: str) -> str:
        return self._conf_parser.jobs_data[section].get('QUEUE', "")

    def get_job_platform(self, section: str) -> str:
        # return the JOBS.<section>.PLATFORM or DEFAULT.HPCARCH
        return self._conf_parser.jobs_data.get(section, {}).get("PLATFORM", self.get_platform())

    def get_platform_queue(self, platform: str) -> str:
        logger.debug("get_platform_queue")
        return self._get_platform_config(platform).get("QUEUE")

    def get_platform_serial_queue(self, platform: str) -> str:
        logger.debug("get_platform_serial_queue")
        return self._get_platform_config(platform).get("SERIAL_QUEUE")

    def get_platform_project(self, platform: str) -> str:
        logger.debug("get_platform_project")
        return self._get_platform_config(platform).get("PROJECT")

    def get_platform_wallclock(self, platform: str) -> str:
        logger.debug("get_platform_wallclock")
        return self._get_platform_config(platform).get('MAX_WALLCLOCK', "")

    def get_wallclock(self, section: str) -> str:
        return self._conf_parser.jobs_data[section].get('WALLCLOCK', '')

    def get_synchronize(self, section: str) -> str:
        # return self._conf_parser.get_synchronize(section)
        return self._get_from_job_or_platform(section, "SYNCHRONIZE", "")

    def get_processors(self, section: str) -> str:
        # return self._conf_parser.get_processors()
        return self._get_from_job_or_platform(section, "PROCESSORS", "1")

    def get_threads(self, section: str) -> str:
        # return self._conf_parser.get_threads(section)
        return self._get_from_job_or_platform(section, "THREADS", "1")

    def get_tasks(self, section: str) -> str:
        # return self._conf_parser.get_tasks(section)
        return self._get_from_job_or_platform(section, "TASKS", "")
    
    def get_nodes(self, section: str) -> str:
        return self._get_from_job_or_platform(section, "NODES", "")

    def get_processors_per_node(self, section: str) -> str:
        return self._get_from_job_or_platform(section, "PROCESSORS_PER_NODE", "")

    def get_scratch_free_space(self, section: str) -> str:
        # return self._conf_parser.get_scratch_free_space(section)
        return self._get_from_job_or_platform(section, "SCRATCH_FREE_SPACE", "")

    def get_memory(self, section: str) -> str:
        # return self._conf_parser.get_memory(section)
        return self._get_from_job_or_platform(section, "MEMORY", "")

    def get_memory_per_task(self, section: str) -> str:
        # return self._conf_parser.get_memory_per_task(section)
        return self._get_from_job_or_platform(section, "MEMORY_PER_TASK", "")

    def get_migrate_user_to(self, section):
        """
        Returns the user to change to from platform config file.
        :return: migrate user to
        :rtype: str
        """
        return self._conf_parser.get_migrate_user_to(section)

    def get_current_user(self, section):
        return self._conf_parser.get_current_user(section)

    def get_current_project(self, section):
        return self._conf_parser.get_current_project(section)

    def set_new_user(self, section, new_user):
        self._conf_parser.set_new_user(section, new_user)

    def get_migrate_project_to(self, section):
        return self._conf_parser.get_migrate_project_to(section)

    def set_new_project(self, section, new_project):
        self._conf_parser.set_new_project(section, new_project)

    def get_custom_directives(self, section):
        """
        Gets custom directives needed for the given job type
        :param section: job type
        :type section: str
        :return: custom directives needed
        :rtype: str
        """
        return str(self._conf_parser.jobs_data.get(section, {}).get('CUSTOM_DIRECTIVES', ""))


    def check_conf_files(self):
        return self._conf_parser.check_conf_files()

    def check_autosubmit_conf(self):
        return self._conf_parser.check_autosubmit_conf()

    def check_platforms_conf(self):
        return self._conf_parser.check_platforms_conf()

    def check_jobs_conf(self):
        return self._conf_parser.check_jobs_conf()

    def check_expdef_conf(self):
        return self._conf_parser.check_expdef_conf()

    def check_proj(self):
        return self._conf_parser.check_proj()

    def check_wrapper_conf(self):
        self._conf_parser.check_wrapper_conf()

    def reload(self):
        self._conf_parser.reload()

    def load_parameters(self):
        return self._conf_parser.load_parameters()

    def load_project_parameters(self):
        return self._conf_parser.load_project_parameters()

    def set_expid(self, exp_id):
        self._conf_parser.set_expid(exp_id)

    def get_project_type(self):
        return self._conf_parser.get_project_type()

    def get_file_project_conf(self):
        return self._conf_parser.get_file_project_conf()

    def get_file_jobs_conf(self):
        return self._conf_parser.get_file_jobs_conf()

    def get_git_project_origin(self):
        return self._conf_parser.get_git_project_origin()

    def get_git_project_branch(self):
        return self._conf_parser.get_git_project_branch()

    def get_git_project_commit(self):
        return self._conf_parser.get_git_project_commit()

    def get_submodules_list(self):
        return self._conf_parser.get_submodules_list()

    def get_project_destination(self):
        return self._conf_parser.get_project_destination()

    def set_git_project_commit(self, as_conf):
        self._conf_parser.set_git_project_commit(as_conf)

    def get_svn_project_url(self):
        return self._conf_parser.get_svn_project_url()

    def get_svn_project_revision(self):
        return self._conf_parser.get_svn_project_revision()

    def get_local_project_path(self):
        return self._conf_parser.get_local_project_path()

    def get_date_list(self):
        return self._conf_parser.get_date_list()

    def get_num_chunks(self):
        return self._conf_parser.get_num_chunks()

    def get_chunk_ini(self, default=1):
        return self._conf_parser.get_chunk_ini(default)

    def get_chunk_size_unit(self):
        """
        Unit for the chunk length

        :return: Unit for the chunk length  Options: {hour, day, month, year}
        :rtype: str
        """
        return self._conf_parser.get_chunk_size_unit()


    def get_chunk_size(self, default=1):
        try:
            chunk_size = self._conf_parser.get_chunk_size(default)
        except Exception as exp:
            print(exp)
            chunk_size = ''
            pass
        if chunk_size == '':
            return default
        return int(chunk_size)

    def get_member_list(self, run_only=False):
        #return self._conf_parser.get_member_list(run_only)
        """
        Returns members list from experiment's config file

        :return: experiment's members
        :rtype: list
        """
        return self._conf_parser.get_member_list(run_only)

    def get_rerun(self):
        return self._conf_parser.get_rerun()

    def get_chunk_list(self):
        return self._conf_parser.get_chunk_list()

    def get_platform(self) -> str:
        try:
            # return DEFAULT.HPCARCH
            return self._conf_parser.get_platform()
        except:
            return ""

    def set_platform(self, hpc):
        self._conf_parser.set_platform(hpc)

    def set_version(self, autosubmit_version):
        self._conf_parser.set_version(autosubmit_version)

    def get_version(self):
        return self._conf_parser.get_version()

    def get_total_jobs(self):
        return self._conf_parser.get_total_jobs()

    def get_max_wallclock(self):
        return self._conf_parser.get_max_wallclock()

    def get_max_processors(self):
        return self._conf_parser.get_max_processors()

    def get_max_waiting_jobs(self):
        return self._conf_parser.get_max_waiting_jobs()

    def get_default_job_type(self):
        return self._conf_parser.get_default_job_type()

    def get_safetysleeptime(self):
        return self._conf_parser.get_safetysleeptime()

    def set_safetysleeptime(self, sleep_time):
        self._conf_parser.set_safetysleeptime(sleep_time)

    def get_retrials(self):
        return self._conf_parser.get_retrials()

    def get_notifications(self):
        return self._conf_parser.get_notifications()

    def get_remote_dependencies(self):
        return self._conf_parser.get_remote_dependencies()

    def get_wrapper_type(self):
        return self._conf_parser.get_wrapper_type()

    def get_wrapper_jobs(self):
        return self._conf_parser.get_wrapper_jobs()

    def get_max_wrapped_jobs(self):
        return self._conf_parser.get_max_wrapped_jobs()

    def get_wrapper_check_time(self):
        return self._conf_parser.get_wrapper_check_time()

    def get_wrapper_machinefiles(self):
        return self._conf_parser.get_wrapper_machinefiles()

    def get_wrapper_queue(self):
        return self._conf_parser.get_wrapper_queue()

    def get_jobs_sections(self):
        return self._conf_parser.get_jobs_sections()

    def get_copy_remote_logs(self):
        return self._conf_parser.get_copy_remote_logs()

    def get_mails_to(self):
        return self._conf_parser.get_mails_to()

    def get_communications_library(self):
        return self._conf_parser.get_communications_library()

    def get_storage_type(self):
        return self._conf_parser.get_storage_type()

    @staticmethod
    def is_valid_mail_address(mail_address: str) -> bool:
        return Autosubmit4Config.is_valid_mail_address(mail_address)

    def is_valid_communications_library(self):
        return self._conf_parser.is_valid_communications_library()

    def is_valid_storage_type(self):
        return self._conf_parser.is_valid_storage_type()

    def is_valid_jobs_in_wrapper(self):
        self._conf_parser.is_valid_jobs_in_wrapper()

    def is_valid_git_repository(self):
        self._conf_parser.is_valid_git_repository()

    @staticmethod
    def get_parser(parser_factory, file_path):
        return Autosubmit4Config.get_parser(parser_factory, file_path)


