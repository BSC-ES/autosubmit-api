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

try:
    # noinspection PyCompatibility
    from configparser import SafeConfigParser
except ImportError:
    # noinspection PyCompatibility
    from ConfigParser import SafeConfigParser

import os
import time
import random
from autosubmitAPIwu.job.job_common import Status
from bscearth.utils.log import Log
from autosubmitAPIwu.job.job_exceptions import WrongTemplateException
from autosubmitAPIwu.job.job import Job
from bscearth.utils.date import sum_str_hours


class JobPackageBase(object):
    """
    Class to manage the package of jobs to be submitted by autosubmit
    """

    def __init__(self, jobs):
        self._jobs = jobs
        self._expid = jobs[0].expid
        try:
            self._tmp_path = jobs[0]._tmp_path
            self._platform = jobs[0].platform
            self._custom_directives = set()
            for job in jobs:
                if job.platform != self._platform or job.platform is None:
                    raise Exception('Only one valid platform per package')
        except IndexError:
            raise Exception('No jobs given')

    def __len__(self):
        return self._jobs.__len__()

    @property
    def jobs(self):
        """
        Returns the jobs

        :return: jobs
        :rtype: List[Job]
        """
        return self._jobs

    @property
    def platform(self):
        """
        Returns the platform

        :return: platform
        :rtype: Platform
        """
        return self._platform

    def submit(self, configuration, parameters,only_generate=False):
        exit=False
        for job in self.jobs:
            if job.check.lower() == Job.CHECK_ON_SUBMISSION:
                if only_generate:
                    exit=True
                    break
                if not job.check_script(configuration, parameters,show_logs=False):
                    raise WrongTemplateException(job.name)
            job.update_parameters(configuration, parameters)
            # looking for directives on jobs
            self._custom_directives = self._custom_directives | set(job.custom_directives)

        if only_generate:
            if not exit:
                self._create_scripts(configuration)
        else:
            self._create_scripts(configuration)
            self._send_files()
            self._do_submission()


    def _create_scripts(self, configuration):
        raise Exception('Not implemented')

    def _send_files(self):
        raise Exception('Not implemented')

    def _do_submission(self):
        raise Exception('Not implemented')



class JobPackageSimple(JobPackageBase):
    """
    Class to manage a group of simple jobs, not packaged, to be submitted by autosubmit
    """

    def __init__(self, jobs):
        super(JobPackageSimple, self).__init__(jobs)
        self._job_scripts = {}

    def _create_scripts(self, configuration):
        for job in self.jobs:
            self._job_scripts[job.name] = job.create_script(configuration)

    def _send_files(self):
        for job in self.jobs:
            self.platform.send_file(self._job_scripts[job.name])

    def _do_submission(self, job_scripts=None):
        if job_scripts is None:
            job_scripts = self._job_scripts
        for job in self.jobs:
            self.platform.remove_stat_file(job.name)
            self.platform.remove_completed_file(job.name)
            job.id = self.platform.submit_job(job, job_scripts[job.name])
            if job.id is None:
                continue
            Log.info("{0} submitted", job.name)
            job.status = Status.SUBMITTED
            job.write_submit_time()


class JobPackageSimpleWrapped(JobPackageSimple):
    """
    Class to manage a group of simple wrapped jobs, not packaged, to be submitted by autosubmit
    """

    def __init__(self, jobs):
        super(JobPackageSimpleWrapped, self).__init__(jobs)
        self._job_wrapped_scripts = {}

    def _create_scripts(self, configuration):
        super(JobPackageSimpleWrapped, self)._create_scripts(configuration)
        for job in self.jobs:
            self._job_wrapped_scripts[job.name] = job.create_wrapped_script(configuration)

    def _send_files(self):
        super(JobPackageSimpleWrapped, self)._send_files()
        for job in self.jobs:
            self.platform.send_file(self._job_wrapped_scripts[job.name])

    def _do_submission(self, job_scripts=None):
        if job_scripts is None:
            job_scripts = self._job_wrapped_scripts
        super(JobPackageSimpleWrapped, self)._do_submission(job_scripts)


class JobPackageArray(JobPackageBase):
    """
    Class to manage an array-based package of jobs to be submitted by autosubmit
    """

    def __init__(self, jobs):
        self._job_inputs = {}
        self._job_scripts = {}
        self._common_script = None
        self._array_size_id = "[1-" + str(len(jobs)) + "]"
        self._wallclock = '00:00'
        self._num_processors = '1'
        for job in jobs:
            if job.wallclock > self._wallclock:
                self._wallclock = job.wallclock
            if job.processors > self._num_processors:
                self._num_processors = job.processors
        super(JobPackageArray, self).__init__(jobs)

    def _create_scripts(self, configuration):
        timestamp = str(int(time.time()))
        for i in range(1, len(self.jobs) + 1):
            self._job_scripts[self.jobs[i - 1].name] = self.jobs[i - 1].create_script(configuration)
            self._job_inputs[self.jobs[i - 1].name] = self._create_i_input(timestamp, i)
            self.jobs[i - 1].remote_logs = (timestamp + ".{0}.out".format(i), timestamp + ".{0}.err".format(i))
        self._common_script = self._create_common_script(timestamp)

    def _create_i_input(self, filename, index):
        filename += '.{0}'.format(index)
        input_content = self._job_scripts[self.jobs[index - 1].name]
        open(os.path.join(self._tmp_path, filename), 'w').write(input_content)
        os.chmod(os.path.join(self._tmp_path, filename), 0o775)
        return filename

    def _create_common_script(self, filename):
        script_content = self.platform.header.array_header(filename, self._array_size_id, self._wallclock,
                                                           self._num_processors,
                                                           directives=self.platform.custom_directives)
        filename += '.cmd'
        open(os.path.join(self._tmp_path, filename), 'w').write(script_content)
        os.chmod(os.path.join(self._tmp_path, filename), 0o775)
        return filename

    def _send_files(self):
        for job in self.jobs:
            self.platform.send_file(self._job_scripts[job.name])
            self.platform.send_file(self._job_inputs[job.name])
        self.platform.send_file(self._common_script)

    def _do_submission(self):
        for job in self.jobs:
            self.platform.remove_stat_file(job.name)
            self.platform.remove_completed_file(job.name)

        package_id = self.platform.submit_job(None, self._common_script)

        if package_id is None:
            return

        for i in range(1, len(self.jobs) + 1):
            Log.info("{0} submitted", self.jobs[i - 1].name)
            self.jobs[i - 1].id = str(package_id) + '[{0}]'.format(i)
            self.jobs[i - 1].status = Status.SUBMITTED
            self.jobs[i - 1].write_submit_time()


class JobPackageThread(JobPackageBase):
    """
    Class to manage a thread-based package of jobs to be submitted by autosubmit
    """
    FILE_PREFIX = 'ASThread'

    def __init__(self, jobs, dependency=None, jobs_resources=dict()):
        super(JobPackageThread, self).__init__(jobs)
        self._job_scripts = {}
        self._job_dependency = dependency
        self._common_script = None
        self._wallclock = '00:00'
        self._num_processors = '0'
        self._jobs_resources = jobs_resources
        self._wrapper_factory = self.platform.wrapper

    @property
    def name(self):
        return self._name

    @property
    def _jobs_scripts(self):
        self._jobs_resources['PROCESSORS_PER_NODE'] = self.platform.processors_per_node

        jobs_scripts = []
        for job in self.jobs:
            if job.section not in self._jobs_resources:
                self._jobs_resources[job.section] = dict()
                self._jobs_resources[job.section]['PROCESSORS'] = job.processors
                self._jobs_resources[job.section]['TASKS'] = job.tasks
            jobs_scripts.append(self._job_scripts[job.name])
        return jobs_scripts

    @property
    def _queue(self):
        if str(self._num_processors) == '1':
            return self.platform.serial_platform.serial_queue
        else:
            return self.platform.queue

    @property
    def _project(self):
        return self._platform.project

    def set_job_dependency(self, dependency):
        self._job_dependency = dependency

    def _create_scripts(self, configuration):
        for i in range(1, len(self.jobs) + 1):
            self._job_scripts[self.jobs[i - 1].name] = self.jobs[i - 1].create_script(configuration)
            self.jobs[i - 1].remote_logs = (
                self._job_scripts[self.jobs[i - 1].name] + ".{0}.out".format(i - 1),
                self._job_scripts[self.jobs[i - 1].name] + ".{0}.err".format(i - 1)
            )
        self._common_script = self._create_common_script()

    def _create_common_script(self):
        script_content = self._common_script_content()
        script_file = self.name + '.cmd'
        open(os.path.join(self._tmp_path, script_file), 'w').write(script_content)
        os.chmod(os.path.join(self._tmp_path, script_file), 0o775)
        return script_file

    def _send_files(self):
        self.platform.check_remote_log_dir()
        if callable(getattr(self.platform, 'remove_multiple_files')):
            filenames = str()
            for job in self.jobs:
                filenames += " " + self.platform.remote_log_dir + "/" + job.name + ".cmd"
            self.platform.remove_multiple_files(filenames)
        for job in self.jobs:
            self.platform.send_file(self._job_scripts[job.name], check=False)
        self.platform.send_file(self._common_script)

    def _do_submission(self):
        if callable(getattr(self.platform, 'remove_multiple_files')):
            filenames = str()
            for job in self.jobs:
                filenames += " " + self.platform.remote_log_dir + "/" + job.name + "_STAT " + \
                             self.platform.remote_log_dir + "/" + job.name + "_COMPLETED"
            self.platform.remove_multiple_files(filenames)
        else:
            for job in self.jobs:
                self.platform.remove_stat_file(job.name)
                self.platform.remove_completed_file(job.name)

        package_id = self.platform.submit_job(None, self._common_script)

        if package_id is None:
            return

        for i in range(1, len(self.jobs) + 1):
            Log.info("{0} submitted", self.jobs[i - 1].name)
            self.jobs[i - 1].id = str(package_id)
            self.jobs[i - 1].status = Status.SUBMITTED
            self.jobs[i - 1].write_submit_time()

    def _common_script_content(self):
        pass


class JobPackageThreadWrapped(JobPackageThread):
    """
    Class to manage a thread-based package of jobs to be submitted by autosubmit
    """
    FILE_PREFIX = 'ASThread'

    def __init__(self, jobs, dependency=None):
        super(JobPackageThreadWrapped, self).__init__(jobs)
        self._job_scripts = {}
        self._job_dependency = dependency
        self._common_script = None
        self._wallclock = '00:00'
        self._num_processors = '0'

    @property
    def name(self):
        return self._name

    @property
    def _jobs_scripts(self):
        jobs_scripts = []
        for job in self.jobs:
            jobs_scripts.append(self._job_scripts[job.name])
        return jobs_scripts

    @property
    def _queue(self):
        if str(self._num_processors) == '1':
            return self.platform.serial_platform.serial_queue
        else:
            return self.platform.queue

    @property
    def _project(self):
        return self._platform.project

    def _create_scripts(self, configuration):
        for i in range(1, len(self.jobs) + 1):
            self._job_scripts[self.jobs[i - 1].name] = self.jobs[i - 1].create_script(configuration)
            self.jobs[i - 1].remote_logs = (
                self._job_scripts[self.jobs[i - 1].name] + ".{0}.out".format(i - 1),
                self._job_scripts[self.jobs[i - 1].name] + ".{0}.err".format(i - 1)
            )
        self._common_script = self._create_common_script()

    def _create_common_script(self):
        script_content = self._common_script_content()
        script_file = self.name + '.cmd'
        open(os.path.join(self._tmp_path, script_file), 'w').write(script_content)
        os.chmod(os.path.join(self._tmp_path, script_file), 0o775)
        return script_file

    def _send_files(self):
        for job in self.jobs:
            self.platform.send_file(self._job_scripts[job.name])
        self.platform.send_file(self._common_script)

    def _do_submission(self):
        for job in self.jobs:
            self.platform.remove_stat_file(job.name)
            self.platform.remove_completed_file(job.name)

        package_id = self.platform.submit_job(None, self._common_script)

        if package_id is None:
            raise Exception('Submission failed')

        for i in range(1, len(self.jobs) + 1):
            Log.info("{0} submitted", self.jobs[i - 1].name)
            self.jobs[i - 1].id = str(package_id)
            self.jobs[i - 1].status = Status.SUBMITTED
            self.jobs[i - 1].write_submit_time()


class JobPackageVertical(JobPackageThread):
    """
    Class to manage a vertical thread-based package of jobs to be submitted by autosubmit
    """

    def __init__(self, jobs, dependency=None):
        super(JobPackageVertical, self).__init__(jobs, dependency)
        #TODO unit or regression test of the wrappers, it will fail as in issue 280
        for job in jobs:
            if job.processors > self._num_processors:
                self._num_processors = job.processors
            self._wallclock = sum_str_hours(self._wallclock, job.wallclock)
        self._name = self._expid + '_' + self.FILE_PREFIX + "_{0}_{1}_{2}".format(str(int(time.time())) +
                                                                                  str(random.randint(1, 10000)),
                                                                                  self._num_processors,
                                                                                  len(self._jobs))

    def _common_script_content(self):
        return self._wrapper_factory.get_wrapper(self._wrapper_factory.vertical_wrapper, name=self._name,
                                                 queue=self._queue, project=self._project, wallclock=self._wallclock,
                                                 num_processors=self._num_processors, jobs_scripts=self._jobs_scripts,
                                                 dependency=self._job_dependency, jobs_resources=self._jobs_resources,
                                                 expid=self._expid, rootdir=self.platform.root_dir,
                                                 directives=self._custom_directives)


class JobPackageHorizontal(JobPackageThread):
    """
    Class to manage a horizontal thread-based package of jobs to be submitted by autosubmit
    """

    def __init__(self, jobs, dependency=None, jobs_resources=dict()):
        super(JobPackageHorizontal, self).__init__(jobs, dependency, jobs_resources)
        for job in jobs:
            if job.wallclock > self._wallclock:
                self._wallclock = job.wallclock
            self._num_processors = str(int(self._num_processors) + int(job.processors))
        self._name = self._expid + '_' + self.FILE_PREFIX + "_{0}_{1}_{2}".format(str(int(time.time())) +
                                                                                  str(random.randint(1, 10000)),
                                                                                  self._num_processors,
                                                                                  len(self._jobs))
        self._jobs_resources = jobs_resources

    def _common_script_content(self):
        return self._wrapper_factory.get_wrapper(self._wrapper_factory.horizontal_wrapper, name=self._name,
                                                 queue=self._queue, project=self._project, wallclock=self._wallclock,
                                                 num_processors=self._num_processors, jobs_scripts=self._jobs_scripts,
                                                 dependency=self._job_dependency, jobs_resources=self._jobs_resources,
                                                 expid=self._expid, rootdir=self.platform.root_dir,
                                                 directives=self._custom_directives)

class JobPackageHybrid(JobPackageThread):
    """
        Class to manage a hybrid (horizontal and vertical) thread-based package of jobs to be submitted by autosubmit
        """

    def __init__(self, jobs, num_processors, total_wallclock, dependency=None, jobs_resources=dict()):
        all_jobs = [item for sublist in jobs for item in sublist] #flatten list
        super(JobPackageHybrid, self).__init__(all_jobs, dependency, jobs_resources)
        self.jobs_lists = jobs
        self._num_processors = int(num_processors)
        self._wallclock = total_wallclock
        self._name = self._expid + '_' + self.FILE_PREFIX + "_{0}_{1}_{2}".format(str(int(time.time())) +
                                                                                  str(random.randint(1, 10000)),
                                                                                  self._num_processors,
                                                                                  len(self._jobs))

    @property
    def _jobs_scripts(self):
        self._jobs_resources['PROCESSORS_PER_NODE'] = self.platform.processors_per_node

        jobs_scripts = []
        for job_list in self.jobs_lists:
            inner_jobs = list()
            for job in job_list:
                inner_jobs.append(job.name + '.cmd')
                if job.section not in self._jobs_resources:
                    self._jobs_resources[job.section] = dict()
                    self._jobs_resources[job.section]['PROCESSORS'] = job.processors
                    self._jobs_resources[job.section]['TASKS'] = job.tasks
            jobs_scripts.append(inner_jobs)
        return jobs_scripts


class JobPackageVerticalHorizontal(JobPackageHybrid):

    def _common_script_content(self):
        return self._wrapper_factory.get_wrapper(self._wrapper_factory.hybrid_wrapper_vertical_horizontal,
                                                 name=self._name, queue=self._queue, project=self._project,
                                                 wallclock=self._wallclock, num_processors=self._num_processors,
                                                 jobs_scripts=self._jobs_scripts, dependency=self._job_dependency,
                                                 jobs_resources=self._jobs_resources, expid=self._expid,
                                                 rootdir=self.platform.root_dir, directives=self._custom_directives)


class JobPackageHorizontalVertical(JobPackageHybrid):

    def _common_script_content(self):
        return self._wrapper_factory.get_wrapper(self._wrapper_factory.hybrid_wrapper_horizontal_vertical,
                                                 name=self._name, queue=self._queue, project=self._project,
                                                 wallclock=self._wallclock, num_processors=self._num_processors,
                                                 jobs_scripts=self._jobs_scripts, dependency=self._job_dependency,
                                                 jobs_resources=self._jobs_resources, expid=self._expid,
                                                 rootdir=self.platform.root_dir, directives=self._custom_directives)
