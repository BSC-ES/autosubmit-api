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

import os
from xml.dom.minidom import parseString
import subprocess

from autosubmitAPIwu.platforms.paramiko_platform import ParamikoPlatform
from autosubmitAPIwu.platforms.headers.local_header import LocalHeader

from autosubmitAPIwu.config.basicConfig import BasicConfig
from bscearth.utils.log import Log


class LocalPlatform(ParamikoPlatform):
    """
    Class to manage jobs to localhost

    :param expid: experiment's identifier
    :type expid: str
    """

    def __init__(self, expid, name, config):
        ParamikoPlatform.__init__(self, expid, name, config)
        self.type = 'local'
        self._header = LocalHeader()
        self.job_status = dict()
        self.job_status['COMPLETED'] = ['1']
        self.job_status['RUNNING'] = ['0']
        self.job_status['QUEUING'] = []
        self.job_status['FAILED'] = []
        # No need to write from API
        # self.update_cmds()

    def update_cmds(self):
        """
        Updates commands for platforms
        """
        self.root_dir = os.path.join(BasicConfig.LOCAL_ROOT_DIR, self.expid)
        self.remote_log_dir = os.path.join(
            self.root_dir, "tmp", 'LOG_' + self.expid)
        self.cancel_cmd = "kill -SIGINT"
        self._checkhost_cmd = "echo 1"
        self.put_cmd = "cp -p"
        self.get_cmd = "cp"
        self.del_cmd = "rm -f"
        self.mkdir_cmd = "mkdir -p " + self.remote_log_dir

    def get_checkhost_cmd(self):
        return self._checkhost_cmd

    def get_remote_log_dir(self):
        return self.remote_log_dir

    def get_mkdir_cmd(self):
        return self.mkdir_cmd

    def parse_job_output(self, output):
        return output[0]

    def get_submitted_job_id(self, output):
        return output

    def jobs_in_queue(self):
        dom = parseString('')
        jobs_xml = dom.getElementsByTagName("JB_job_number")
        return [int(element.firstChild.nodeValue) for element in jobs_xml]

    def get_submit_cmd(self, job_script, job):
        return self.get_call(job_script, job)

    def get_checkjob_cmd(self, job_id):
        return self.get_pscall(job_id)

    def connect(self):
        return True

    def send_command(self, command, ignore_log=False):
        try:
            output = subprocess.check_output(command, shell=True)
        except subprocess.CalledProcessError as e:
            if not ignore_log:
                Log.error('Could not execute command {0} on {1}'.format(
                    e.cmd, self.host))
            return False
        Log.debug("Command '{0}': {1}", command, output)
        self._ssh_output = output
        return True

    def send_file(self, filename):
        self.check_remote_log_dir()
        self.delete_file(filename)
        command = '{0} {1} {2}'.format(self.put_cmd, os.path.join(self.tmp_path, filename),
                                       os.path.join(self.tmp_path, 'LOG_' + self.expid, filename))
        try:
            subprocess.check_call(command, shell=True)
        except subprocess.CalledProcessError:
            Log.error('Could not send file {0} to {1}'.format(os.path.join(self.tmp_path, filename),
                                                              os.path.join(self.tmp_path, 'LOG_' + self.expid,
                                                                           filename)))
            raise
        return True

    def get_file(self, filename, must_exist=True, relative_path=''):
        local_path = os.path.join(self.tmp_path, relative_path)
        if not os.path.exists(local_path):
            os.makedirs(local_path)

        file_path = os.path.join(local_path, filename)
        if os.path.exists(file_path):
            os.remove(file_path)

        command = '{0} {1} {2}'.format(self.get_cmd, os.path.join(self.tmp_path, 'LOG_' + self.expid, filename),
                                       file_path)
        try:
            subprocess.check_call(command, stdout=open(
                os.devnull, 'w'), stderr=open(os.devnull, 'w'), shell=True)
        except subprocess.CalledProcessError:
            if must_exist:
                raise Exception('File {0} does not exists'.format(filename))
            return False
        return True

    def delete_file(self, filename):
        command = '{0} {1}'.format(self.del_cmd, os.path.join(
            self.tmp_path, 'LOG_' + self.expid, filename))
        try:
            subprocess.check_call(command, shell=True)
        except subprocess.CalledProcessError:
            Log.debug('Could not remove file {0}'.format(
                os.path.join(self.tmp_path, 'LOG_' + self.expid, filename)))
            return False
        return True

    def get_ssh_output(self):
        return self._ssh_output

    def get_logs_files(self, exp_id, remote_logs):
        """
        Overriding the parent's implementation.
        Do nothing because the log files are already in the local platform (redundancy).

        :param exp_id: experiment id
        :type exp_id: str
        :param remote_logs: names of the log files
        :type remote_logs: (str, str)
        """
        return
