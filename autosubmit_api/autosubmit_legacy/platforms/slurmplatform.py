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

from autosubmitAPIwu.platforms.paramiko_platform import ParamikoPlatform
from autosubmitAPIwu.platforms.headers.slurm_header import SlurmHeader
from autosubmitAPIwu.platforms.wrappers.wrapper_factory import SlurmWrapperFactory
from autosubmitAPIwu.config.basicConfig import BasicConfig


class SlurmPlatform(ParamikoPlatform):
    """
    Class to manage jobs to host using SLURM scheduler

    :param expid: experiment's identifier
    :type expid: str
    """

    def __init__(self, expid, name, config):
        ParamikoPlatform.__init__(self, expid, name, config)
        self._header = SlurmHeader()
        self._wrapper = SlurmWrapperFactory(self)
        self.job_status = dict()
        self.job_status['COMPLETED'] = ['COMPLETED']
        self.job_status['RUNNING'] = ['RUNNING']
        self.job_status['QUEUING'] = ['PENDING', 'CONFIGURING', 'RESIZING']
        self.job_status['FAILED'] = ['FAILED', 'CANCELLED', 'NODE_FAIL', 'PREEMPTED',
                                     'SUSPENDED', 'TIMEOUT', 'OUT_OF_MEMORY', 'OUT_OF_ME+', 'OUT_OF_ME']
        self._pathdir = "\$HOME/LOG_" + self.expid
        self._allow_arrays = False
        self._allow_wrappers = True
        self.update_cmds()

        exp_id_path = os.path.join(BasicConfig.LOCAL_ROOT_DIR, self.expid)
        tmp_path = os.path.join(exp_id_path, "tmp")
        self._submit_script_path = os.path.join(
            tmp_path, BasicConfig.LOCAL_ASLOG_DIR, "submit_" + self.name + ".sh")
        # No need to write from API
        # self._submit_script_file = open(self._submit_script_path, 'w').close()

    def open_submit_script(self):
        # No need to write from API
        pass
        #self._submit_script_file = open(self._submit_script_path, 'w').close()
        #self._submit_script_file = open(self._submit_script_path, 'a')

    def get_submit_script(self):
        # No need to write from API
        pass
        # self._submit_script_file.close()
        # os.chmod(self._submit_script_path, 0o750)
        # return os.path.join(BasicConfig.LOCAL_ASLOG_DIR,os.path.basename(self._submit_script_path))

    def submit_Script(self):
        """
        Sends a SubmitfileScript, execute it  in the platform and retrieves the Jobs_ID of all jobs at once.

        :param job: job object
        :type job: autosubmit.job.job.Job
        :return: job id for  submitted jobs
        :rtype: list(int)
        """

        self.send_file(self.get_submit_script(), False)

        #cmd = '(cd '+self.get_files_path()+';'+' ./'+os.path.basename(self._submit_script_path)+')'

        cmd = os.path.join(self.get_files_path(),
                           os.path.basename(self._submit_script_path))
        if self.send_command(cmd):
            jobs_id = self.get_submitted_job_id(self.get_ssh_output())
            return jobs_id
        else:

            return None

    def update_cmds(self):
        """
        Updates commands for platforms
        """
        self.root_dir = os.path.join(
            self.scratch, self.project, self.user, self.expid)
        self.remote_log_dir = os.path.join(self.root_dir, "LOG_" + self.expid)
        self.cancel_cmd = "scancel"
        self._checkhost_cmd = "echo 1"
        self._submit_cmd = 'sbatch -D {1} {1}/'.format(
            self.host, self.remote_log_dir)
        self.put_cmd = "scp"
        self.get_cmd = "scp"
        self.mkdir_cmd = "mkdir -p " + self.remote_log_dir

    def get_checkhost_cmd(self):
        return self._checkhost_cmd

    def get_mkdir_cmd(self):
        return self.mkdir_cmd

    def get_remote_log_dir(self):
        return self.remote_log_dir

    def parse_job_output(self, output):
        return output.strip().split(' ')[0].strip()

    def parse_Alljobs_output(self, output, job_id):
        status = [x.split()[1] for x in output.splitlines()
                  if x.split()[0] == str(job_id)]
        if len(status) == 0:
            return status
        return status[0]

    def get_submitted_job_id(self, outputlines):
        if outputlines.find("failed") != -1:
            raise Exception(outputlines)
        jobs_id = []
        for output in outputlines.splitlines():
            jobs_id.append(int(output.split(' ')[3]))
        return jobs_id

    def jobs_in_queue(self):
        dom = parseString('')
        jobs_xml = dom.getElementsByTagName("JB_job_number")
        return [int(element.firstChild.nodeValue) for element in jobs_xml]

    def get_submit_cmd(self, job_script, job):
        self._submit_script_file.write(self._submit_cmd + job_script + "\n")

    def get_checkjob_cmd(self, job_id):
        return 'sacct -n -j {1} -o "State"'.format(self.host, job_id)

    def get_checkAlljobs_cmd(self, jobs_id):
        return "sacct -n -X -j  {1} -o 'jobid,State'".format(self.host, jobs_id)

    def get_queue_status_cmd(self, job_id):
        return 'squeue -j {0} -o %A,%R'.format(job_id)

    def parse_queue_reason(self, output, job_id):
        reason = [x.split(',')[1] for x in output.splitlines()
                  if x.split(',')[0] == str(job_id)]
        if len(reason) > 0:
            return reason[0]
        return reason
        # output = output.split('\n')
        # if len(output) > 1:
        #     return output[1]
        # else:
        #     return output

    @staticmethod
    def wrapper_header(filename, queue, project, wallclock, num_procs, dependency, directives):
        return """\
        #!/usr/bin/env python
        ###############################################################################
        #              {0}
        ###############################################################################
        #
        #SBATCH -J {0}
        {1}
        #SBATCH -A {2}
        #SBATCH --output={0}.out
        #SBATCH --error={0}.err
        #SBATCH -t {3}:00
        #SBATCH -n {4}
        {5}
        {6}
        #
        ###############################################################################
        """.format(filename, queue, project, wallclock, num_procs, dependency,
                   '\n'.ljust(13).join(str(s) for s in directives))

    @staticmethod
    def allocated_nodes():
        return """os.system("scontrol show hostnames $SLURM_JOB_NODELIST > node_list")"""
