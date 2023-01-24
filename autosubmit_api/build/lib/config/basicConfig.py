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
try:
    # noinspection PyCompatibility
    from configparser import SafeConfigParser
except ImportError:
    # noinspection PyCompatibility
    from configparser import SafeConfigParser
import os
import re
# from log.log import Log, AutosubmitError, AutosubmitCritical


class BasicConfig:
    """
    Class to manage configuration for Autosubmit path, database and default values for new experiments
    """

    def __init__(self):
        pass

    DB_DIR = os.path.join(os.path.expanduser('~'), 'debug', 'autosubmit')
    STRUCTURES_DIR = os.path.join('/esarchive', 'autosubmit', 'as_metadata', 'structures')
    GRAPHDATA_DIR = os.path.join('/esarchive', 'autosubmit', 'as_metadata', 'graph')
    GLOBAL_LOG_DIR = os.path.join('/esarchive', 'autosubmit', 'Aslogs')
    JOBDATA_DIR = os.path.join('/esarchive', 'autosubmit', 'as_metadata', 'data')
    HISTORICAL_LOG_DIR = os.path.join('/esarchive', 'autosubmit', 'as_metadata', 'logs')
    FILE_STATUS_DIR = os.path.join('/esarchive', 'autosubmit', 'as_metadata', 'test')
    AUTOSUBMIT_API_URL = "http://192.168.11.91:8081"
    DB_FILE = 'autosubmit.db'
    AS_TIMES_DB = 'as_times.db'
    FILE_STATUS_DB = 'status.db'
    DB_PATH = os.path.join(DB_DIR, DB_FILE)
    ALLOWED_CLIENTS = set(['https://earth.bsc.es/'])
    LOCAL_ROOT_DIR = DB_DIR
    LOCAL_TMP_DIR = 'tmp'
    LOCAL_ASLOG_DIR = 'ASLOGS'
    LOCAL_PROJ_DIR = 'proj'
    DEFAULT_PLATFORMS_CONF = ''
    CUSTOM_PLATFORMS_PATH = ''
    DEFAULT_JOBS_CONF = ''
    SMTP_SERVER = ''
    MAIL_FROM = ''
    ALLOWED_HOSTS = ''
    DENIED_HOSTS = ''
    @staticmethod
    def _update_config():
        """
        Updates commonly used composed paths
        """
        # Just one needed for the moment.
        BasicConfig.DB_PATH = os.path.join(
            BasicConfig.DB_DIR, BasicConfig.DB_FILE)

    @staticmethod
    def __read_file_config(file_path):
        """
        Reads configuration file. If configuration file dos not exist in given path,
        no error is raised. Configuration options also are not required to exist

        :param file_path: configuration file to read
        :type file_path: str
        """
        if not os.path.isfile(file_path):
            return
        #Log.debug('Reading config from ' + file_path)
        parser = SafeConfigParser()
        parser.optionxform = str
        parser.read(file_path)

        if parser.has_option('database', 'path'):
            BasicConfig.DB_DIR = parser.get('database', 'path')
        if parser.has_option('database', 'filename'):
            BasicConfig.DB_FILE = parser.get('database', 'filename')
        if parser.has_option('local', 'path'):
            BasicConfig.LOCAL_ROOT_DIR = parser.get('local', 'path')
        if parser.has_option('conf', 'platforms'):
            BasicConfig.DEFAULT_PLATFORMS_CONF = parser.get(
                'conf', 'platforms')
        if parser.has_option('conf', 'custom_platforms'):
            BasicConfig.CUSTOM_PLATFORMS_PATH = parser.get(
                'conf', 'custom_platforms')
        if parser.has_option('conf', 'jobs'):
            BasicConfig.DEFAULT_JOBS_CONF = parser.get('conf', 'jobs')
        if parser.has_option('mail', 'smtp_server'):
            BasicConfig.SMTP_SERVER = parser.get('mail', 'smtp_server')
        if parser.has_option('mail', 'mail_from'):
            BasicConfig.MAIL_FROM = parser.get('mail', 'mail_from')
        if parser.has_option('hosts', 'authorized'):
            list_command_allowed = parser.get('hosts', 'authorized')

            list_command_allowed = list_command_allowed.split('] ')
            i=0
            for command in list_command_allowed:
                list_command_allowed[i] = list_command_allowed[i].strip('[]')
                i=i+1
            restrictions = dict()
            for command_unparsed in list_command_allowed:
                command_allowed = command_unparsed.split(' ')
                if ',' in command_allowed[0]:
                   for command in command_allowed[0].split(','):
                       if ',' in command_allowed[1]:
                           restrictions[command] = command_allowed[1].split(',')
                       else:
                           restrictions[command] = [command_allowed[1]]
                else:
                        if ',' in command_allowed[1]:
                            restrictions[command_allowed[0]] = command_allowed[1].split(',')
                        else:
                            restrictions[command_allowed[0]] = [command_allowed[1]]
            BasicConfig.ALLOWED_HOSTS = restrictions
        if parser.has_option('hosts', 'forbidden'):
            list_command_allowed = parser.get('hosts', 'forbidden')
            list_command_allowed = list_command_allowed.split('] ')
            i=0
            for command in list_command_allowed:
                list_command_allowed[i] = list_command_allowed[i].strip('[]')
                i=i+1
            restrictions = dict()
            for command_unparsed in list_command_allowed:
                command_allowed = command_unparsed.split(' ')
                if ',' in command_allowed[0]:
                   for command in command_allowed[0].split(','):
                       if ',' in command_allowed[1]:
                           restrictions[command] = command_allowed[1].split(',')
                       else:
                           restrictions[command] = [command_allowed[1]]
                else:
                        if ',' in command_allowed[1]:
                            restrictions[command_allowed[0]] = command_allowed[1].split(',')
                        else:
                            restrictions[command_allowed[0]] = [command_allowed[1]]
            BasicConfig.DENIED_HOSTS = restrictions
        if parser.has_option('structures', 'path'):
            BasicConfig.STRUCTURES_DIR = parser.get('structures', 'path')
        if parser.has_option('graph', 'path'):
            BasicConfig.GRAPHDATA_DIR = parser.get('graph', 'path')
        if parser.has_option('globallogs', 'path'):
            BasicConfig.GLOBAL_LOG_DIR = parser.get('globallogs', 'path')
        if parser.has_option('historicdb', 'path'):
            BasicConfig.JOBDATA_DIR = parser.get('historicdb', 'path')
        if parser.has_option('historiclog', 'path'):
            BasicConfig.HISTORICAL_LOG_DIR = parser.get('historiclog', 'path')
        if parser.has_option('autosubmitapi', 'url'):
            BasicConfig.AUTOSUBMIT_API_URL = parser.get('autosubmitapi', 'url')
        if parser.has_option('clients', 'authorized'):
            BasicConfig.ALLOWED_CLIENTS = set(parser.get('clients', 'authorized').split())
        if parser.has_option('statusdb', 'path'):
            BasicConfig.FILE_STATUS_DIR = parser.get('statusdb', 'path')
        if parser.has_option('statusdb', 'filename'):
            BasicConfig.FILE_STATUS_DB = parser.get('statusdb', 'filename')

    @staticmethod
    def read():
        """
        Reads configuration from autosubmitrc files, first from /etc, then for user
        directory and last for current path.
        """
        filename = 'autosubmitrc'

        BasicConfig.__read_file_config(os.path.join('/etc', filename))
        BasicConfig.__read_file_config(os.path.join(
            os.path.expanduser('~'), '.' + filename))
        BasicConfig.__read_file_config(os.path.join('.', '.' + filename))

        BasicConfig._update_config()
        return
