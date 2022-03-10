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
import subprocess

from autosubmitAPIwu.platforms.paramiko_platform import ParamikoPlatform, ParamikoPlatformException
from bscearth.utils.log import Log

from autosubmitAPIwu.platforms.headers.ec_header import EcHeader
from autosubmitAPIwu.platforms.headers.ec_cca_header import EcCcaHeader
from autosubmitAPIwu.platforms.headers.slurm_header import SlurmHeader
from autosubmitAPIwu.platforms.wrappers.wrapper_factory import EcWrapperFactory


class EcPlatform(ParamikoPlatform):
    """
    Class to manage queues with ecaccess

    :param expid: experiment's identifier
    :type expid: str
    :param scheduler: scheduler to use
    :type scheduler: str (pbs, loadleveler)
    """

    def __init__(self, expid, name, config, scheduler):
        ParamikoPlatform.__init__(self, expid, name, config)
        if scheduler == 'pbs':
            self._header = EcCcaHeader()
        elif scheduler == 'loadleveler':
            self._header = EcHeader()
        elif scheduler == 'slurm':
            self._header = SlurmHeader()
        else:
            raise ParamikoPlatformException(
                'ecaccess scheduler {0} not supported'.format(scheduler))
        self._wrapper = EcWrapperFactory(self)
        self.job_status = dict()
        self.job_status['COMPLETED'] = ['DONE']
        self.job_status['RUNNING'] = ['EXEC']
        self.job_status['QUEUING'] = ['INIT', 'RETR', 'STDBY', 'WAIT']
        self.job_status['FAILED'] = ['STOP']
        self._pathdir = "\$HOME/LOG_" + self.expid
        self._allow_arrays = False
        self._allow_wrappers = True
        self._allow_python_jobs = False
        # No need to write from API
        # self.update_cmds()

    def update_cmds(self):
        """
        Updates commands for platforms
        """
        self.root_dir = os.path.join(
            self.scratch, self.project, self.user, self.expid)
        self.remote_log_dir = os.path.join(self.root_dir, "LOG_" + self.expid)
        self.cancel_cmd = "eceaccess-job-delete"
        self._checkjob_cmd = "ecaccess-job-list "
        self._checkhost_cmd = "ecaccess-certificate-list"
        self._submit_cmd = ("ecaccess-job-submit -distant -queueName " + self.host + " " + self.host + ":" +
                            self.remote_log_dir + "/")
        self.put_cmd = "ecaccess-file-put"
        self.get_cmd = "ecaccess-file-get"
        self.del_cmd = "ecaccess-file-delete"
        self.mkdir_cmd = ("ecaccess-file-mkdir " + self.host + ":" + self.scratch + "/" + self.project + "/" +
                          self.user + "/" + self.expid + "; " + "ecaccess-file-mkdir " + self.host + ":" +
                          self.remote_log_dir)

    def get_checkhost_cmd(self):
        return self._checkhost_cmd

    def get_remote_log_dir(self):
        return self.remote_log_dir

    def get_mkdir_cmd(self):
        return self.mkdir_cmd

    def parse_job_output(self, output):
        job_state = output.split('\n')
        if len(job_state) > 7:
            job_state = job_state[7].split()
            if len(job_state) > 1:
                return job_state[1]
        return 'DONE'

    def get_submitted_job_id(self, output):
        return output

    def jobs_in_queue(self):
        """
        Returns empty list because ecacces does not support this command

        :return: empty list
        :rtype: list
        """
        return ''.split()

    def get_checkjob_cmd(self, job_id):
        return self._checkjob_cmd + str(job_id)

    def get_submit_cmd(self, job_script, job):
        return self._submit_cmd + job_script

    def connect(self):
        """
        In this case, it does nothing because connection is established foe each command

        :return: True
        :rtype: bool
        """
        return True

    def send_command(self, command, ignore_log=False):
        try:
            output = subprocess.check_output(command, shell=True)
        except subprocess.CalledProcessError as e:
            if not ignore_log:
                Log.error('Could not execute command {0} on {1}'.format(
                    e.cmd, self.host))
            return False
        self._ssh_output = output
        return True

    def send_file(self, filename, check=True):
        self.check_remote_log_dir()
        self.delete_file(filename)
        command = '{0} {1} {3}:{2}'.format(self.put_cmd, os.path.join(self.tmp_path, filename),
                                           os.path.join(self.get_files_path(), filename), self.host)
        try:
            subprocess.check_call(command, shell=True)
        except subprocess.CalledProcessError:
            Log.error('Could not send file {0} to {1}'.format(os.path.join(self.tmp_path, filename),
                                                              os.path.join(self.get_files_path(), filename)))
            raise
        return True

    def get_file(self, filename, must_exist=True, relative_path=''):
        local_path = os.path.join(self.tmp_path, relative_path)
        if not os.path.exists(local_path):
            os.makedirs(local_path)

        file_path = os.path.join(local_path, filename)
        if os.path.exists(file_path):
            os.remove(file_path)

        command = '{0} {3}:{2} {1}'.format(self.get_cmd, file_path, os.path.join(self.get_files_path(), filename),
                                           self.host)
        try:
            process = subprocess.Popen(
                command, shell=True, stdout=subprocess.PIPE)
            out, _ = process.communicate()
            process_ok = False if 'No such file' in out or process.returncode != 0 else True
        except Exception:
            process_ok = False

        if not process_ok and must_exist:
            raise Exception('File {0} does not exists'.format(filename))
        return process_ok

    def delete_file(self, filename):
        command = '{0} {1}:{2}'.format(
            self.del_cmd, self.host, os.path.join(self.get_files_path(), filename))
        try:
            subprocess.check_call(command, stdout=open(
                os.devnull, 'w'), shell=True)
        except subprocess.CalledProcessError:
            Log.debug('Could not remove file {0}'.format(
                os.path.join(self.get_files_path(), filename)))
            return False
        return True

    def get_ssh_output(self):
        return self._ssh_output

    @staticmethod
    def wrapper_header(filename, queue, project, wallclock, num_procs, expid, dependency, rootdir, directives):
        return """\
        #!/bin/bash
        ###############################################################################
        #              {0}
        ###############################################################################
        #
        #PBS -N {0}
        #PBS -q {1}
        #PBS -l EC_billing_account={2}
        #PBS -o {7}/LOG_{5}/{0}.out
        #PBS -e {7}/LOG_{5}/{0}.err
        #PBS -l walltime={3}:00
        #PBS -l EC_total_tasks={4}
        #PBS -l EC_hyperthreads=1
        {6}
        {8}
        #
        ###############################################################################
        """.format(filename, queue, project, wallclock, num_procs, expid, dependency, rootdir,
                   '\n'.ljust(13).join(str(s) for s in directives))
