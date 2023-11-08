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
from configparser import SafeConfigParser
from autosubmitconfigparser.config.basicconfig import BasicConfig
import os
# from log.log import Log, AutosubmitError, AutosubmitCritical


class APIBasicConfig(BasicConfig):
    """
    Extended class to manage configuration for Autosubmit path, database and default values for new experiments in the Autosubmit API
    """

    GRAPHDATA_DIR = os.path.join(os.path.expanduser('~'), 'autosubmit', 'as_metadata', 'graph')
    FILE_STATUS_DIR = os.path.join(os.path.expanduser('~'), 'autosubmit', 'as_metadata', 'test')
    FILE_STATUS_DB = 'status.db'
    ALLOWED_CLIENTS = set([])

    @staticmethod
    def __read_file_config(file_path):
        # WARNING: Is unsafe to call this method directly. Doing APIBasicConfig.__read_file_config doesn't run BasicConfig.__read_file_config

        if not os.path.isfile(file_path):
            return
        #Log.debug('Reading config from ' + file_path)
        parser = SafeConfigParser()
        parser.optionxform = str
        parser.read(file_path)

        if parser.has_option('graph', 'path'):
            APIBasicConfig.GRAPHDATA_DIR = parser.get('graph', 'path')
        if parser.has_option('statusdb', 'path'):
            APIBasicConfig.FILE_STATUS_DIR = parser.get('statusdb', 'path')
        if parser.has_option('statusdb', 'filename'):
            APIBasicConfig.FILE_STATUS_DB = parser.get('statusdb', 'filename')
        if parser.has_option('clients', 'authorized'):
            APIBasicConfig.ALLOWED_CLIENTS = set(parser.get('clients', 'authorized').split())


    @staticmethod
    def read():
        BasicConfig.read() # This is done to run BasicConfig.__read_file_config indirectly

        filename = 'autosubmitrc'
        if 'AUTOSUBMIT_CONFIGURATION' in os.environ and os.path.exists(os.environ['AUTOSUBMIT_CONFIGURATION']):
            config_file_path = os.environ['AUTOSUBMIT_CONFIGURATION']
            # Call read_file_config with the value of the environment variable
            APIBasicConfig.__read_file_config(config_file_path)
        else:
            if os.path.exists(os.path.join('', '.' + filename)):
                APIBasicConfig.__read_file_config(os.path.join('', '.' + filename))
            elif os.path.exists(os.path.join(os.path.expanduser('~'), '.' + filename)):
                APIBasicConfig.__read_file_config(os.path.join(
                    os.path.expanduser('~'), '.' + filename))
            else:
                APIBasicConfig.__read_file_config(os.path.join('/etc', filename))

            # Check if the environment variable is defined

        APIBasicConfig._update_config()
        return