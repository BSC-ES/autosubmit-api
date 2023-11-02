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

"""
Main module for autosubmit. Only contains an interface class to all functionality implemented on autosubmit
"""
import os
import re
import time
import json
import datetime
from collections import OrderedDict
#from bscearth.utils.config_parser import ConfigParserFactory

from ...monitor.monitor import Monitor
from .job_common import Status, Type
from ...config.basicConfig import APIBasicConfig
from .job_common import StatisticsSnippetBash, StatisticsSnippetPython
from .job_common import StatisticsSnippetR, StatisticsSnippetEmpty
#from autosubmitAPIwu.config.config_common import AutosubmitConfig
from bscearth.utils.date import date2str, parse_date, previous_day, chunk_end_date, chunk_start_date, Log, subs_dates
from functools import reduce


class Job(object):
    """
    Class to handle all the tasks with Jobs at HPC.
    A job is created by default with a name, a jobid, a status and a type.
    It can have children and parents. The inheritance reflects the dependency between jobs.
    If Job2 must wait until Job1 is completed then Job2 is a child of Job1. Inversely Job1 is a parent of Job2

    :param name: job's name
    :type name: str
    :param jobid: job's identifier
    :type jobid: int
    :param status: job initial status
    :type status: Status
    :param priority: job's priority
    :type priority: int
    """

    CHECK_ON_SUBMISSION = 'on_submission'

    def __str__(self):
        return "{0} STATUS: {1}".format(self.name, self.status)

    def __init__(self, name, job_id, status, priority):
        self._platform = None
        self._queue = None
        self.platform_name = None
        self.section = None
        self.wallclock = None
        self.tasks = '0'
        self.threads = '1'
        self.processors = '1'
        self.memory = ''
        self.memory_per_task = ''
        self.chunk = None
        self.member = None
        self.date = None
        self.name = name
        self.split = None
        self.delay = None
        self.synchronize = None

        self._long_name = None
        self.long_name = name
        self.date_format = ''
        self.type = Type.BASH
        self.scratch_free_space = None
        self.custom_directives = []
        self.undefined_variables = None
        self.level = 0
        self.h_order = 0
        self.barycentric_value = 0
        self.id = job_id
        self.file = None
        self._local_logs = ('', '')
        self._remote_logs = ('', '')
        self.out = 'NA'
        self.err = 'NA'
        self.status = status
        self.new_status = status
        self.priority = priority
        self._parents = set()
        self._children = set()
        self.fail_count = 0
        self.expid = name.split('_')[0]
        self.parameters = dict()
        self._tmp_path = os.path.join(
            APIBasicConfig.LOCAL_ROOT_DIR, self.expid, APIBasicConfig.LOCAL_TMP_DIR)
        self.write_start = False
        self._platform = None
        self.check = 'True'
        self.packed = False
        self.status_color = Monitor.color_status(self.status)
        self.status_text = str(Status.VALUE_TO_KEY[self.status])
        self.title = Job.getTitle(
            self.name, self.status_color, self.status_text)
        self.tree_parent = list()
        self._wrapper_queue = None

    @staticmethod
    def getTitle(job_name, status_color, status_text):
        return job_name + " <span class='badge' style='background-color: " + status_color + "'>#" + status_text + "</span>"

    def toJSON(self):
        return {
            'platform_name': self.platform_name,
            'date': self.date,
            'section': self.section,
            'member': self.member,
            'wallclock': self.wallclock,
            'status_code': self.status,
        }

    def __getstate__(self):
        odict = self.__dict__
        if '_platform' in odict:
            odict = odict.copy()  # copy the dict since we change it
            del odict['_platform']  # remove filehandle entry
        return odict

    def print_job(self):
        """
        Prints debug information about the job
        """
        Log.debug('NAME: {0}', self.name)
        Log.debug('JOBID: {0}', self.id)
        Log.debug('STATUS: {0}', self.status)
        Log.debug('TYPE: {0}', self.priority)
        Log.debug('PARENTS: {0}', [p.name for p in self.parents])
        Log.debug('CHILDREN: {0}', [c.name for c in self.children])
        Log.debug('FAIL_COUNT: {0}', self.fail_count)
        Log.debug('EXPID: {0}', self.expid)

    @property
    def parents(self):
        """
        Returns parent jobs list

        :return: parent jobs
        :rtype: set
        """
        return self._parents

    @parents.setter
    def parents(self, parents):
        """
        Sets the parents job list
        """
        self._parents = parents

    @property
    def is_serial(self):
        return str(self.processors) == '1'

    @property
    def platform(self):
        """
        Returns the platform to be used by the job. Chooses between serial and parallel platforms

        :return HPCPlatform object for the job to use
        :rtype: HPCPlatform
        """
        if self.is_serial:
            return self._platform.serial_platform
        else:
            return self._platform

    @platform.setter
    def platform(self, value):
        """
        Sets the HPC platforms to be used by the job.

        :param value: platforms to set
        :type value: HPCPlatform
        """
        self._platform = value

    @property
    def queue(self):
        """
        Returns the queue to be used by the job. Chooses between serial and parallel platforms

        :return HPCPlatform object for the job to use
        :rtype: HPCPlatform
        """
        if self._queue is not None:
            return self._queue
        if self.is_serial:
            return self._platform.serial_platform.serial_queue
        else:
            return self._platform.queue

    @queue.setter
    def queue(self, value):
        """
        Sets the queue to be used by the job.

        :param value: queue to set
        :type value: HPCPlatform
        """
        self._queue = value

    @property
    def children(self):
        """
        Returns a list containing all children of the job

        :return: child jobs
        :rtype: set
        """
        return self._children

    @children.setter
    def children(self, children):
        """
        Sets the children job list
        """
        self._children = children

    @property
    def long_name(self):
        """
        Job's long name. If not setted, returns name

        :return: long name
        :rtype: str
        """
        if hasattr(self, '_long_name'):
            return self._long_name
        else:
            return self.name

    @long_name.setter
    def long_name(self, value):
        """
        Sets long name for the job

        :param value: long name to set
        :type value: str
        """
        self._long_name = value

    @property
    def local_logs(self):
        return self._local_logs

    @local_logs.setter
    def local_logs(self, value):
        self._local_logs = value
        self._remote_logs = value

    @property
    def remote_logs(self):
        return self._remote_logs

    @remote_logs.setter
    def remote_logs(self, value):
        self._remote_logs = value

    @property
    def total_processors(self):
        if ':' in self.processors:
            return reduce(lambda x, y: int(x) + int(y), self.processors.split(':'))
        return int(self.processors)

    @property
    def total_wallclock(self):
        if self.wallclock:
            hours, minutes = self.wallclock.split(':')
            return float(minutes) / 60 + float(hours)
        return 0

    def log_job(self):
        """
        Prints job information in log
        """
        Log.info("{0}\t{1}\t{2}", "Job Name", "Job Id", "Job Status")
        Log.info("{0}\t\t{1}\t{2}", self.name, self.id, self.status)

    def print_parameters(self):
        """
        Print sjob parameters in log
        """
        Log.info(self.parameters)

    def inc_fail_count(self):
        """
        Increments fail count
        """
        self.fail_count += 1

    # Maybe should be renamed to the plural?
    def add_parent(self, *parents):
        """
        Add parents for the job. It also adds current job as a child for all the new parents

        :param parents: job's parents to add
        :type parents: *Job
        """
        for parent in parents:
            num_parents = 1
            if isinstance(parent, list):
                num_parents = len(parent)
            for i in range(num_parents):
                new_parent = parent[i] if isinstance(parent, list) else parent
                self._parents.add(new_parent)
                new_parent.__add_child(self)

    def __add_child(self, new_child):
        """
        Adds a new child to the job

        :param new_child: new child to add
        :type new_child: Job
        """
        self.children.add(new_child)

    def delete_parent(self, parent):
        """
        Remove a parent from the job

        :param parent: parent to remove
        :type parent: Job
        """
        self.parents.remove(parent)

    def delete_child(self, child):
        """
        Removes a child from the job

        :param child: child to remove
        :type child: Job
        """
        # careful it is only possible to remove one child at a time
        self.children.remove(child)

    def has_children(self):
        """
        Returns true if job has any children, else return false

        :return: true if job has any children, otherwise return false
        :rtype: bool
        """
        return self.children.__len__()

    def has_parents(self):
        """
        Returns true if job has any parents, else return false

        :return: true if job has any parent, otherwise return false
        :rtype: bool
        """
        return self.parents.__len__()

    def compare_by_status(self, other):
        """
        Compare jobs by status value

        :param other: job to compare
        :type other: Job
        :return: comparison result
        :rtype: bool
        """
        return self.status < other.status

    def compare_by_id(self, other):
        """
        Compare jobs by ID

        :param other: job to compare
        :type other: Job
        :return: comparison result
        :rtype: bool
        """
        return self.id < other.id

    def compare_by_name(self, other):
        """
        Compare jobs by name

        :param other: job to compare
        :type other: Job
        :return: comparison result
        :rtype: bool
        """
        return self.name < other.name

    def _get_from_stat(self, index):
        """
        Returns value from given row index position in STAT file associated to job

        :param index: row position to retrieve
        :type index: int
        :return: value in index position
        :rtype: int
        """
        logname = os.path.join(self._tmp_path, self.name + '_STAT')
        if os.path.exists(logname):
            lines = open(logname).readlines()
            if len(lines) >= index + 1:
                return int(lines[index])
            else:
                return 0
        else:
            return 0

    def _get_from_total_stats(self, index):
        """
        Returns list of values from given column index position in TOTAL_STATS file associated to job

        :param index: column position to retrieve
        :type index: int
        :return: list of values in column index position
        :rtype: list[datetime.datetime]
        """
        log_name = os.path.join(self._tmp_path, self.name + '_TOTAL_STATS')
        lst = []
        if os.path.exists(log_name):
            f = open(log_name)
            lines = f.readlines()
            for line in lines:
                fields = line.split()
                if len(fields) >= index + 1:
                    lst.append(parse_date(fields[index]))
        return lst

    def check_end_time(self):
        """
        Returns end time from stat file

        :return: date and time
        :rtype: str
        """
        return self._get_from_stat(1)

    def check_start_time(self):
        """
        Returns job's start time

        :return: start time
        :rtype: str
        """
        return self._get_from_stat(0)

    def check_retrials_submit_time(self):
        """
        Returns list of submit datetime for retrials from total stats file

        :return: date and time
        :rtype: list[int]
        """
        return self._get_from_total_stats(0)

    def check_retrials_end_time(self):
        """
        Returns list of end datetime for retrials from total stats file

        :return: date and time
        :rtype: list[int]
        """
        return self._get_from_total_stats(2)

    def check_retrials_start_time(self):
        """
        Returns list of start datetime for retrials from total stats file

        :return: date and time
        :rtype: list[int]
        """
        return self._get_from_total_stats(1)

    def get_last_retrials(self):
        log_name = os.path.join(self._tmp_path, self.name + '_TOTAL_STATS')
        retrials_list = []
        if os.path.exists(log_name):
            already_completed = False
            for retrial in reversed(open(log_name).readlines()):
                retrial_fields = retrial.split()
                if Job.is_a_completed_retrial(retrial_fields):
                    if already_completed:
                        break
                    already_completed = True
                retrial_dates = [parse_date(y) if y != 'COMPLETED' and y != 'FAILED' else y for y in retrial_fields]
                retrials_list.insert(0, retrial_dates)
        return retrials_list

    def update_status(self, copy_remote_logs=False, iswrapper=False):
        """
        Updates job status, checking COMPLETED file if needed

        :param new_status: job status retrieved from the platform
        :param copy_remote_logs: should copy remote logs when finished?
        :type: Status
        """
        previous_status = self.status
        new_status = self.new_status
        if new_status == Status.COMPLETED:
            Log.debug("This job seems to have completed: checking...")
            self.platform.get_completed_files(self.name)
            self.check_completion()
        else:
            self.status = new_status
        if self.status is Status.QUEUING:
            if iswrapper:
                reason = str()
                if self.platform.type == 'slurm':
                    self.platform.send_command(
                        self.platform.get_queue_status_cmd(self.id))
                    reason = self.platform.parse_queue_reason(
                        self.platform._ssh_output)
                    if self._queuing_reason_cancel(reason):
                        Log.error(
                            "Job {0} will be cancelled and set to FAILED as it was queuing due to {1}", self.name, reason)
                        self.platform.send_command(
                            self.platform.cancel_cmd + " {0}".format(self.id))
                        self.new_status = Status.FAILED
                        self.update_status(copy_remote_logs, True)
                        return
                Log.info("Job {0} is QUEUING {1}", self.name, reason)
        elif self.status is Status.RUNNING:
            Log.info("Job {0} is RUNNING", self.name)
        elif self.status is Status.COMPLETED:
            Log.result("Job {0} is COMPLETED", self.name)
        elif self.status is Status.FAILED:
            Log.user_warning(
                "Job {0} is FAILED. Checking completed files to confirm the failure...", self.name)
            self.platform.get_completed_files(self.name)
            self.check_completion()
            if self.status is Status.COMPLETED:
                Log.warning(
                    'Job {0} seems to have failed but there is a COMPLETED file', self.name)
                Log.result("Job {0} is COMPLETED", self.name)
            else:
                self.update_children_status()
        elif self.status is Status.UNKNOWN:
            Log.debug(
                "Job {0} in UNKNOWN status. Checking completed files...", self.name)
            self.platform.get_completed_files(self.name)
            self.check_completion(Status.UNKNOWN)
            if self.status is Status.UNKNOWN:
                Log.warning('Job {0} in UNKNOWN status', self.name)
            elif self.status is Status.COMPLETED:
                Log.result("Job {0} is COMPLETED", self.name)
        elif self.status is Status.SUBMITTED:
            # after checking the jobs , no job should have the status "submitted"
            Log.warning(
                'Job {0} in SUBMITTED status after checking.', self.name)

        if previous_status != Status.RUNNING and self.status in [Status.COMPLETED, Status.FAILED, Status.UNKNOWN,
                                                                 Status.RUNNING]:
            self.write_start_time()

        if self.status in [Status.COMPLETED, Status.FAILED, Status.UNKNOWN]:
            self.write_end_time(self.status == Status.COMPLETED)
            if self.local_logs != self.remote_logs:
                self.synchronize_logs()  # unifying names for log files
            if copy_remote_logs:
                self.platform.get_logs_files(self.expid, self.remote_logs)
        return self.status

    def update_children_status(self):
        children = list(self.children)
        for child in children:
            if child.status in [Status.SUBMITTED, Status.RUNNING, Status.QUEUING, Status.UNKNOWN]:
                child.status = Status.FAILED
                children += list(child.children)

    def check_completion(self, default_status=Status.FAILED):
        """
        Check the presence of *COMPLETED* file.
        Change status to COMPLETED if *COMPLETED* file exists and to FAILED otherwise.
        :param default_status: status to set if job is not completed. By default is FAILED
        :type default_status: Status
        """
        log_name = os.path.join(self._tmp_path, self.name + '_COMPLETED')
        if os.path.exists(log_name):
            self.status = Status.COMPLETED
        else:
            Log.warning(
                "Job {0} completion check failed. There is no COMPLETED file", self.name)
            self.status = default_status

    def update_parameters(self, as_conf, parameters,
                          default_parameters={'d': '%d%', 'd_': '%d_%', 'Y': '%Y%', 'Y_': '%Y_%',
                                              'M': '%M%', 'M_': '%M_%', 'm': '%m%', 'm_': '%m_%'}):
        """
        Refresh parameters value

        :param default_parameters:
        :type default_parameters: dict
        :param as_conf:
        :type as_conf: AutosubmitConfig
        :param parameters:
        :type parameters: dict
        """

        parameters = parameters.copy()
        parameters.update(default_parameters)
        parameters['JOBNAME'] = self.name
        parameters['FAIL_COUNT'] = str(self.fail_count)

        parameters['SDATE'] = date2str(self.date, self.date_format)
        parameters['MEMBER'] = self.member

        if hasattr(self, 'retrials'):
            parameters['RETRIALS'] = self.retrials

        if self.date is not None:
            if self.chunk is None:
                chunk = 1
            else:
                chunk = self.chunk

            parameters['CHUNK'] = chunk
            parameters['SPLIT'] = self.split
            parameters['DELAY'] = self.delay
            parameters['SYNCHRONIZE'] = self.synchronize
            total_chunk = int(parameters['NUMCHUNKS'])
            chunk_length = int(parameters['CHUNKSIZE'])
            chunk_unit = parameters['CHUNKSIZEUNIT'].lower()
            cal = parameters['CALENDAR'].lower()
            chunk_start = chunk_start_date(
                self.date, chunk, chunk_length, chunk_unit, cal)
            chunk_end = chunk_end_date(
                chunk_start, chunk_length, chunk_unit, cal)
            chunk_end_1 = previous_day(chunk_end, cal)

            parameters['DAY_BEFORE'] = date2str(
                previous_day(self.date, cal), self.date_format)

            parameters['RUN_DAYS'] = str(
                subs_dates(chunk_start, chunk_end, cal))
            parameters['Chunk_End_IN_DAYS'] = str(
                subs_dates(self.date, chunk_end, cal))

            parameters['Chunk_START_DATE'] = date2str(
                chunk_start, self.date_format)
            parameters['Chunk_START_YEAR'] = str(chunk_start.year)
            parameters['Chunk_START_MONTH'] = str(chunk_start.month).zfill(2)
            parameters['Chunk_START_DAY'] = str(chunk_start.day).zfill(2)
            parameters['Chunk_START_HOUR'] = str(chunk_start.hour).zfill(2)

            parameters['Chunk_END_DATE'] = date2str(
                chunk_end_1, self.date_format)
            parameters['Chunk_END_YEAR'] = str(chunk_end_1.year)
            parameters['Chunk_END_MONTH'] = str(chunk_end_1.month).zfill(2)
            parameters['Chunk_END_DAY'] = str(chunk_end_1.day).zfill(2)
            parameters['Chunk_END_HOUR'] = str(chunk_end_1.hour).zfill(2)

            parameters['PREV'] = str(subs_dates(self.date, chunk_start, cal))

            if chunk == 1:
                parameters['Chunk_FIRST'] = 'TRUE'
            else:
                parameters['Chunk_FIRST'] = 'FALSE'

            if total_chunk == chunk:
                parameters['Chunk_LAST'] = 'TRUE'
            else:
                parameters['Chunk_LAST'] = 'FALSE'

        job_platform = self.platform
        self.processors = as_conf.get_processors(self.section)
        self.threads = as_conf.get_threads(self.section)
        self.tasks = as_conf.get_tasks(self.section)
        if self.tasks == '0' and job_platform.processors_per_node:
            self.tasks = job_platform.processors_per_node
        self.memory = as_conf.get_memory(self.section)
        self.memory_per_task = as_conf.get_memory_per_task(self.section)
        self.wallclock = as_conf.get_wallclock(self.section)

        self.scratch_free_space = as_conf.get_scratch_free_space(self.section)
        if self.scratch_free_space == 0:
            self.scratch_free_space = job_platform.scratch_free_space
        self.custom_directives = as_conf.get_custom_directives(self.section)
        if self.custom_directives != '':
            self.custom_directives = json.loads(
                as_conf.get_custom_directives(self.section))
            if job_platform.custom_directives:
                self.custom_directives = self.custom_directives + \
                    json.loads(job_platform.custom_directives)
        elif job_platform.custom_directives:
            self.custom_directives = json.loads(job_platform.custom_directives)
        elif self.custom_directives == '':
            self.custom_directives = []

        parameters['NUMPROC'] = self.processors
        parameters['MEMORY'] = self.memory
        parameters['MEMORY_PER_TASK'] = self.memory_per_task
        parameters['NUMTHREADS'] = self.threads
        parameters['NUMTASK'] = self.tasks
        parameters['WALLCLOCK'] = self.wallclock
        parameters['TASKTYPE'] = self.section
        parameters['SCRATCH_FREE_SPACE'] = self.scratch_free_space
        parameters['CUSTOM_DIRECTIVES'] = self.custom_directives

        parameters['CURRENT_ARCH'] = job_platform.name
        parameters['CURRENT_HOST'] = job_platform.host
        parameters['CURRENT_QUEUE'] = self.queue
        parameters['CURRENT_USER'] = job_platform.user
        parameters['CURRENT_PROJ'] = job_platform.project
        parameters['CURRENT_BUDG'] = job_platform.budget
        parameters['CURRENT_RESERVATION'] = job_platform.reservation
        parameters['CURRENT_EXCLUSIVITY'] = job_platform.exclusivity
        parameters['CURRENT_HYPERTHREADING'] = job_platform.hyperthreading
        parameters['CURRENT_TYPE'] = job_platform.type
        parameters['CURRENT_SCRATCH_DIR'] = job_platform.scratch
        parameters['CURRENT_ROOTDIR'] = job_platform.root_dir
        parameters['CURRENT_LOGDIR'] = job_platform.get_files_path()

        parameters['ROOTDIR'] = os.path.join(
            APIBasicConfig.LOCAL_ROOT_DIR, self.expid)
        parameters['PROJDIR'] = as_conf.get_project_dir()

        parameters['NUMMEMBERS'] = len(as_conf.get_member_list())
        parameters['WRAPPER'] = as_conf.get_wrapper_type()

        self.parameters = parameters

        return parameters

    def update_content(self, as_conf):
        """
        Create the script content to be run for the job

        :param as_conf: config
        :type as_conf: config
        :return: script code
        :rtype: str
        """
        if self.parameters['PROJECT_TYPE'].lower() != "none":
            template_file = open(os.path.join(
                as_conf.get_project_dir(), self.file), 'r')
            template = template_file.read()
        else:
            if self.type == Type.BASH:
                template = 'sleep 5'
            elif self.type == Type.PYTHON:
                template = 'time.sleep(5)'
            elif self.type == Type.R:
                template = 'Sys.sleep(5)'
            else:
                template = ''

        if self.type == Type.BASH:
            snippet = StatisticsSnippetBash
        elif self.type == Type.PYTHON:
            snippet = StatisticsSnippetPython
        elif self.type == Type.R:
            snippet = StatisticsSnippetR
        else:
            raise Exception('Job type {0} not supported'.format(self.type))

        template_content = self._get_template_content(
            as_conf, snippet, template)

        return template_content

    def get_wrapped_content(self, as_conf):
        snippet = StatisticsSnippetEmpty
        template = 'python $SCRATCH/{1}/LOG_{1}/{0}.cmd'.format(
            self.name, self.expid)
        template_content = self._get_template_content(
            as_conf, snippet, template)
        return template_content

    def _get_template_content(self, as_conf, snippet, template):
        communications_library = as_conf.get_communications_library()
        if communications_library == 'saga':
            return self._get_saga_template(snippet, template)
        elif communications_library == 'paramiko':
            return self._get_paramiko_template(snippet, template)
        else:
            Log.error('You have to define a template on Job class')
            raise Exception('Job template content not found')

    def _get_saga_template(self, snippet, template):
        return ''.join([snippet.as_header(''),
                        template,
                        snippet.as_tailer()])

    def _get_paramiko_template(self, snippet, template):
        current_platform = self.platform
        return ''.join([snippet.as_header(current_platform.get_header(self)),
                        template,
                        snippet.as_tailer()])

    def queuing_reason_cancel(self, reason):
        try:
            if len(reason.split('(', 1)) > 1:
                reason = reason.split('(', 1)[1].split(')')[0]
                if 'Invalid' in reason or reason in ['AssociationJobLimit', 'AssociationResourceLimit', 'AssociationTimeLimit',
                                                     'BadConstraints', 'QOSMaxCpuMinutesPerJobLimit', 'QOSMaxWallDurationPerJobLimit',
                                                     'QOSMaxNodePerJobLimit', 'DependencyNeverSatisfied', 'QOSMaxMemoryPerJob',
                                                     'QOSMaxMemoryPerNode', 'QOSMaxMemoryMinutesPerJob', 'QOSMaxNodeMinutesPerJob',
                                                     'InactiveLimit', 'JobLaunchFailure', 'NonZeroExitCode', 'PartitionNodeLimit',
                                                     'PartitionTimeLimit', 'SystemFailure', 'TimeLimit', 'QOSUsageThreshold']:
                    return True
            return False
        except:
            return False

    @staticmethod
    def is_a_completed_retrial(fields):
        if len(fields) == 4:
            if isinstance(fields[0], type(datetime.timedelta())) and isinstance(fields[1], type(datetime.timedelta())) and isinstance(fields[2], type(datetime.timedelta())):
                return False
            if fields[3] == 'COMPLETED':
                return True
        return False

    def create_script(self, as_conf):
        """
        Creates script file to be run for the job

        :param as_conf: configuration object
        :type as_conf: AutosubmitConfig
        :return: script's filename
        :rtype: str
        """
        parameters = self.parameters
        template_content = self.update_content(as_conf)
        for key, value in list(parameters.items()):
            template_content = re.sub(
                '%(?<!%%)' + key + '%(?!%%)', str(parameters[key]), template_content)
        if self.undefined_variables:
            for variable in self.undefined_variables:
                template_content = re.sub(
                    '%(?<!%%)' + variable + '%(?!%%)', '', template_content)
        template_content = template_content.replace("%%", "%")
        script_name = '{0}.cmd'.format(self.name)
        open(os.path.join(self._tmp_path, script_name),
             'w').write(template_content)
        os.chmod(os.path.join(self._tmp_path, script_name), 0o775)
        return script_name

    def create_wrapped_script(self, as_conf, wrapper_tag='wrapped'):
        parameters = self.parameters
        template_content = self.get_wrapped_content(as_conf)
        for key, value in list(parameters.items()):
            template_content = re.sub(
                '%(?<!%%)' + key + '%(?!%%)', str(parameters[key]), template_content)
        if self.undefined_variables:
            for variable in self.undefined_variables:
                template_content = re.sub(
                    '%(?<!%%)' + variable + '%(?!%%)', '', template_content)
        template_content = template_content.replace("%%", "%")
        script_name = '{0}.{1}.cmd'.format(self.name, wrapper_tag)
        open(os.path.join(self._tmp_path, script_name),
             'w').write(template_content)
        os.chmod(os.path.join(self._tmp_path, script_name), 0o775)
        return script_name

    def check_script(self, as_conf, parameters, show_logs=False):
        """
        Checks if script is well formed

        :param parameters: script parameters
        :type parameters: dict
        :param as_conf: configuration file
        :type as_conf: AutosubmitConfig
        :param show_logs: Display output
        :type show_logs: Bool
        :return: true if not problem has been detected, false otherwise
        :rtype: bool
        """

        out = False
        parameters = self.update_parameters(as_conf, parameters)
        template_content = self.update_content(as_conf)
        if template_content is not False:

            variables = re.findall('%(?<!%%)\w+%(?!%%)', template_content)
            variables = [variable[1:-1] for variable in variables]
            out = set(parameters).issuperset(set(variables))

            # Check if the variables in the templates are defined in the configurations
            if not out:
                self.undefined_variables = set(variables) - set(parameters)
                if show_logs:
                    Log.warning("The following set of variables to be substituted in template script is not part of "
                                "parameters set, and will be replaced by a blank value: {0}", str(self.undefined_variables))

            # Check which variables in the proj.conf are not being used in the templates
            if show_logs:
                if not set(variables).issuperset(set(parameters)):
                    Log.debug("The following set of variables are not being used in the templates: {0}",
                              str(set(parameters) - set(variables)))
        return out

    def write_submit_time(self):
        """
        Writes submit date and time to TOTAL_STATS file
        """
        path = os.path.join(self._tmp_path, self.name + '_TOTAL_STATS')
        if os.path.exists(path):
            f = open(path, 'a')
            f.write('\n')
        else:
            f = open(path, 'w')
        f.write(date2str(datetime.datetime.now(), 'S'))

    def write_start_time(self):
        """
        Writes start date and time to TOTAL_STATS file
        :return: True if succesful, False otherwise
        :rtype: bool
        """
        if self.platform.get_stat_file(self.name, retries=0):
            start_time = self.check_start_time()
        else:
            Log.warning(
                'Could not get start time for {0}. Using current time as an approximation', self.name)
            start_time = time.time()

        path = os.path.join(self._tmp_path, self.name + '_TOTAL_STATS')
        f = open(path, 'a')
        f.write(' ')
        # noinspection PyTypeChecker
        f.write(date2str(datetime.datetime.fromtimestamp(start_time), 'S'))
        return True

    def write_end_time(self, completed):
        """
        Writes ends date and time to TOTAL_STATS file
        :param completed: True if job was completed successfully, False otherwise
        :type completed: bool
        """
        self.platform.get_stat_file(self.name, retries=0)
        end_time = self.check_end_time()
        path = os.path.join(self._tmp_path, self.name + '_TOTAL_STATS')
        f = open(path, 'a')
        f.write(' ')
        if end_time > 0:
            # noinspection PyTypeChecker
            f.write(date2str(datetime.datetime.fromtimestamp(end_time), 'S'))
        else:
            f.write(date2str(datetime.datetime.now(), 'S'))
        f.write(' ')
        if completed:
            f.write('COMPLETED')
        else:
            f.write('FAILED')

    def check_started_after(self, date_limit):
        """
        Checks if the job started after the given date
        :param date_limit: reference date
        :type date_limit: datetime.datetime
        :return: True if job started after the given date, false otherwise
        :rtype: bool
        """
        if any(parse_date(str(date_retrial)) > date_limit for date_retrial in self.check_retrials_start_time()):
            return True
        else:
            return False

    def check_running_after(self, date_limit):
        """
        Checks if the job was running after the given date
        :param date_limit: reference date
        :type date_limit: datetime.datetime
        :return: True if job was running after the given date, false otherwise
        :rtype: bool
        """
        if any(parse_date(str(date_end)) > date_limit for date_end in self.check_retrials_end_time()):
            return True
        else:
            return False

    def is_parent(self, job):
        """
        Check if the given job is a parent
        :param job: job to be checked if is a parent
        :return: True if job is a parent, false otherwise
        :rtype bool
        """
        return job in self.parents

    def is_ancestor(self, job):
        """
        Check if the given job is an ancestor
        :param job: job to be checked if is an ancestor
        :return: True if job is an ancestor, false otherwise
        :rtype bool
        """
        for parent in list(self.parents):
            if parent.is_parent(job):
                return True
            elif parent.is_ancestor(job):
                return True
        return False

    def remove_redundant_parents(self):
        """
        Checks if a parent is also an ancestor, if true, removes the link in both directions.
        Useful to remove redundant dependencies.
        """
        for parent in list(self.parents):
            if self.is_ancestor(parent):
                parent.children.remove(self)
                self.parents.remove(parent)

    def synchronize_logs(self):
        self.platform.move_file(
            self.remote_logs[0], self.local_logs[0])  # .out
        self.platform.move_file(
            self.remote_logs[1], self.local_logs[1])  # .err
        self.remote_logs = self.local_logs


class WrapperJob(Job):

    def __init__(self, name, job_id, status, priority, job_list, total_wallclock, num_processors, platform, as_config):
        super(WrapperJob, self).__init__(name, job_id, status, priority)
        self.job_list = job_list
        # divide jobs in dictionary by state?
        self.wallclock = total_wallclock
        self.num_processors = num_processors
        self.running_jobs_start = OrderedDict()
        self.platform = platform
        self.as_config = as_config
        # save start time, wallclock and processors?!
        self.checked_time = datetime.datetime.now()

    def _queuing_reason_cancel(self, reason):
        try:
            if len(reason.split('(', 1)) > 1:
                reason = reason.split('(', 1)[1].split(')')[0]
                if 'Invalid' in reason or reason in ['AssociationJobLimit', 'AssociationResourceLimit', 'AssociationTimeLimit',
                                                     'BadConstraints', 'QOSMaxCpuMinutesPerJobLimit', 'QOSMaxWallDurationPerJobLimit',
                                                     'QOSMaxNodePerJobLimit', 'DependencyNeverSatisfied', 'QOSMaxMemoryPerJob',
                                                     'QOSMaxMemoryPerNode', 'QOSMaxMemoryMinutesPerJob', 'QOSMaxNodeMinutesPerJob',
                                                     'InactiveLimit', 'JobLaunchFailure', 'NonZeroExitCode', 'PartitionNodeLimit',
                                                     'PartitionTimeLimit', 'SystemFailure', 'TimeLimit', 'QOSUsageThreshold']:
                    return True
            return False
        except:
            return False

    def check_status(self, status):
        if status != self.status:
            if status == Status.QUEUING:
                reason = str()
                if self.platform.type == 'slurm':
                    self.platform.send_command(
                        self.platform.get_queue_status_cmd(self.id))
                    reason = self.platform.parse_queue_reason(
                        self.platform._ssh_output, self.id)

                    if self._queuing_reason_cancel(reason):
                        Log.error("Job {0} will be cancelled and set to FAILED as it was queuing due to {1}", self.name,
                                  reason)
                        self.cancel_failed_wrapper_job()
                        return
                    Log.info("Job {0} is QUEUING {1}", self.name, reason)
            self.status = status
        if status in [Status.FAILED, Status.UNKNOWN]:
            self.cancel_failed_wrapper_job()
            self.update_failed_jobs()
        elif status == Status.COMPLETED:
            self.check_inner_jobs_completed(self.job_list)
        elif status == Status.RUNNING:
            time.sleep(3)
            Log.debug('Checking inner jobs status')
            self.check_inner_job_status()

    def check_inner_job_status(self):
        self._check_running_jobs()
        self.check_inner_jobs_completed(list(self.running_jobs_start.keys()))
        self._check_wrapper_status()

    def check_inner_jobs_completed(self, jobs):
        not_completed_jobs = [
            job for job in jobs if job.status != Status.COMPLETED]
        not_completed_job_names = [job.name for job in not_completed_jobs]
        job_names = ' '.join(not_completed_job_names)

        if job_names:
            completed_files = self.platform.check_completed_files(job_names)

            completed_jobs = []
            for job in not_completed_jobs:
                if completed_files and len(completed_files) > 0:
                    if job.name in completed_files:
                        completed_jobs.append(job)
                        job.new_status = Status.COMPLETED
                        job.update_status(
                            self.as_config.get_copy_remote_logs() == 'true', True)
                if job.status != Status.COMPLETED and job in self.running_jobs_start:
                    self._check_inner_job_wallclock(job)
            for job in completed_jobs:
                self.running_jobs_start.pop(job, None)

            if self.status == Status.COMPLETED:
                not_completed_jobs = list(
                    set(not_completed_jobs) - set(completed_jobs))
                for job in not_completed_jobs:
                    self._check_finished_job(job)

    def _check_inner_job_wallclock(self, job):
        start_time = self.running_jobs_start[job]
        if self._is_over_wallclock(start_time, job.wallclock):
            if self.as_config.get_wrapper_type() in ['vertical', 'horizontal']:
                Log.error("Job {0} inside wrapper {1} is running for longer than its wallclock! Cancelling...".format(
                    job.name, self.name))
                self.cancel_failed_wrapper_job()
            else:
                Log.error("Job {0} inside wrapper {1} is running for longer than its wallclock! Setting to FAILED...".format(
                    job.name, self.name))
            self._check_finished_job(job)

    def _check_running_jobs(self):
        not_finished_jobs = [job for job in self.job_list if job.status not in [
            Status.COMPLETED, Status.FAILED]]
        if not_finished_jobs:
            not_finished_jobs_dict = OrderedDict()
            for job in not_finished_jobs:
                not_finished_jobs_dict[job.name] = job

            not_finished_jobs_names = ' '.join(list(not_finished_jobs_dict.keys()))

            remote_log_dir = self.platform.get_remote_log_dir()
            command = 'cd ' + remote_log_dir + '; for job in ' + \
                not_finished_jobs_names + \
                '; do echo ${job} $(head ${job}_STAT); done'
            output = self.platform.send_command(command, ignore_log=True)

            if output:
                content = self.platform._ssh_output
                for line in content.split('\n'):
                    out = line.split()
                    if out:
                        jobname = out[0]
                        job = not_finished_jobs_dict[jobname]
                        if len(out) > 1:
                            if job not in self.running_jobs_start:
                                start_time = self._check_time(out, 1)
                                Log.info("Job {0} started at {1}".format(
                                    jobname, str(parse_date(start_time))))
                                self.running_jobs_start[job] = start_time
                                job.new_status = Status.RUNNING
                                job.update_status(
                                    self.as_config.get_copy_remote_logs() == 'true', True)
                            elif len(out) == 2:
                                Log.info("Job {0} is RUNNING".format(jobname))
                            else:
                                end_time = self._check_time(out, 2)
                                Log.info("Job {0} finished at {1}".format(
                                    jobname, str(parse_date(end_time))))
                                self._check_finished_job(job)
                        else:
                            Log.debug(
                                "Job {0} is SUBMITTED and waiting for dependencies".format(jobname))

    def _check_finished_job(self, job):
        if self.platform.check_completed_files(job.name):
            job.new_status = Status.COMPLETED
            job.update_status(
                self.as_config.get_copy_remote_logs() == 'true', True)
        else:
            Log.info(
                "No completed filed found, setting {0} to FAILED...".format(job.name))
            job.new_status = Status.FAILED
            job.update_status(
                self.as_config.get_copy_remote_logs() == 'true', True)
        self.running_jobs_start.pop(job, None)

    def update_failed_jobs(self):
        not_finished_jobs = [job for job in self.job_list if job.status not in [
            Status.FAILED, Status.COMPLETED]]
        for job in not_finished_jobs:
            self._check_finished_job(job)

    def _check_wrapper_status(self):
        not_finished_jobs = [job for job in self.job_list if job.status not in [
            Status.FAILED, Status.COMPLETED]]
        if not self.running_jobs_start and not_finished_jobs:
            self.status = self.platform.check_job(self)
            if self.status == Status.RUNNING:
                self._check_running_jobs()
                if not self.running_jobs_start:
                    Log.error(
                        "It seems there are no inner jobs running in the wrapper. Cancelling...")
                    self.cancel_failed_wrapper_job()
            elif self.status == Status.COMPLETED:
                Log.info(
                    "Wrapper job {0} COMPLETED. Setting all jobs to COMPLETED...".format(self.name))
                self._update_completed_jobs()

    def cancel_failed_wrapper_job(self):
        Log.info("Cancelling job with id {0}".format(self.id))
        self.platform.send_command(
            self.platform.cancel_cmd + " " + str(self.id))

    def _update_completed_jobs(self):
        for job in self.job_list:
            if job.status == Status.RUNNING:
                self.running_jobs_start.pop(job, None)
                Log.debug('Setting job {0} to COMPLETED'.format(job.name))
                job.new_status = Status.COMPLETED
                job.update_status(
                    self.as_config.get_copy_remote_logs() == 'true', True)

    def _is_over_wallclock(self, start_time, wallclock):
        elapsed = datetime.datetime.now() - parse_date(start_time)
        wallclock = datetime.datetime.strptime(wallclock, '%H:%M')
        wallclock_delta = datetime.timedelta(hours=wallclock.hour, minutes=wallclock.minute,
                                             seconds=wallclock.second)
        if elapsed > wallclock_delta:
            return True
        return False

    def _parse_timestamp(self, timestamp):
        value = datetime.datetime.fromtimestamp(timestamp)
        time = value.strftime('%Y-%m-%d %H:%M:%S')
        return time

    def _check_time(self, output, index):
        time = int(output[index])
        time = self._parse_timestamp(time)
        return time
