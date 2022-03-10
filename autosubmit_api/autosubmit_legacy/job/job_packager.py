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

from bscearth.utils.log import Log
from autosubmitAPIwu.job.job_common import Status, Type
from bscearth.utils.date import sum_str_hours
from autosubmitAPIwu.job.job_packages import JobPackageSimple, JobPackageVertical, JobPackageHorizontal, \
    JobPackageSimpleWrapped, JobPackageHorizontalVertical, JobPackageVerticalHorizontal
from operator import attrgetter
from math import ceil


class JobPackager(object):
    """
    The main responsibility of this class is to manage the packages of jobs that have to be submitted.
    """

    def __init__(self, as_config, platform, jobs_list):
        self._as_config = as_config
        self._platform = platform
        self._jobs_list = jobs_list

        waiting_jobs = len(jobs_list.get_submitted(platform) + jobs_list.get_queuing(platform))
        self._max_wait_jobs_to_submit = platform.max_waiting_jobs - waiting_jobs
        self._max_jobs_to_submit = platform.total_jobs - len(jobs_list.get_in_queue(platform))
        self.max_jobs = min(self._max_wait_jobs_to_submit, self._max_jobs_to_submit)

        self.wrapper_type = self._as_config.get_wrapper_type()
        self.remote_dependencies = self._as_config.get_remote_dependencies()
        self.jobs_in_wrapper = self._as_config.get_wrapper_jobs()

        Log.debug("Number of jobs ready: {0}", len(jobs_list.get_ready(platform)))
        Log.debug("Number of jobs available: {0}", self._max_wait_jobs_to_submit)
        if len(jobs_list.get_ready(platform)) > 0:
            Log.info("Jobs ready for {0}: {1}", self._platform.name, len(jobs_list.get_ready(platform)))
        self._maxTotalProcessors = 0

    def build_packages(self,only_generate=False, jobs_filtered=[]):
        """
        Returns the list of the built packages to be submitted

        :return: list of packages
        :rtype list
        """
        packages_to_submit = list()
        remote_dependencies_dict = dict()

        if only_generate:
            jobs_to_submit = jobs_filtered
        else:
            jobs_ready = self._jobs_list.get_ready(self._platform)
            if jobs_ready == 0:
                return packages_to_submit, remote_dependencies_dict
            if not (self._max_wait_jobs_to_submit > 0 and self._max_jobs_to_submit > 0):
                return packages_to_submit, remote_dependencies_dict

            available_sorted = sorted(jobs_ready, key=lambda k: k.long_name.split('_')[1][:6])
            list_of_available = sorted(available_sorted, key=lambda k: k.priority, reverse=True)
            num_jobs_to_submit = min(self._max_wait_jobs_to_submit, len(jobs_ready), self._max_jobs_to_submit)
            jobs_to_submit = list_of_available[0:num_jobs_to_submit]

        jobs_to_submit_by_section = self._divide_list_by_section(jobs_to_submit)

        for section in jobs_to_submit_by_section:
            if self._platform.allow_wrappers and self.wrapper_type in ['horizontal', 'vertical', 'vertical-mixed',
                                                                       'vertical-horizontal', 'horizontal-vertical'] \
            and (self.jobs_in_wrapper == 'None' or section in self.jobs_in_wrapper):

                max_wrapped_jobs = int(self._as_config.jobs_parser.get_option(section, "MAX_WRAPPED", self._as_config.get_max_wrapped_jobs()))

                if self.wrapper_type in ['vertical', 'vertical-mixed']:
                    built_packages, remote_dependencies_dict = self._build_vertical_packages(jobs_to_submit_by_section[section],
                                                                                    max_wrapped_jobs)
                    packages_to_submit += built_packages
                elif self.wrapper_type == 'horizontal':
                    built_packages, remote_dependencies_dict = self._build_horizontal_packages(jobs_to_submit_by_section[section],
                                                                                    max_wrapped_jobs, section)
                    packages_to_submit += built_packages

                elif self.wrapper_type in ['vertical-horizontal', 'horizontal-vertical']:
                    built_packages = self._build_hybrid_package(jobs_to_submit_by_section[section], max_wrapped_jobs, section)
                    packages_to_submit.append(built_packages)
            else:
                # No wrapper allowed / well-configured
                for job in jobs_to_submit_by_section[section]:
                    if job.type == Type.PYTHON and not self._platform.allow_python_jobs:
                        package = JobPackageSimpleWrapped([job])
                    else:
                        package = JobPackageSimple([job])
                    packages_to_submit.append(package)

        return packages_to_submit, remote_dependencies_dict

    def _divide_list_by_section(self, jobs_list):
        """
        Returns a dict() with as many keys as 'jobs_list' different sections
        The value for each key is a list() with all the jobs with the key section.

        :param jobs_list: list of jobs to be divided
        :rtype: dict
        """
        sections_split = self.jobs_in_wrapper.split()

        jobs_section = dict()
        for job in jobs_list:
            section = next((s for s in sections_split if job.section in s and '&' in s), None)
            if section is None:
                section = job.section
            if section not in jobs_section:
                jobs_section[section] = list()
            jobs_section[section].append(job)
        return jobs_section

    def _build_horizontal_packages(self, section_list, max_wrapped_jobs, section):
        packages = []
        remote_dependencies_dict = dict()

        horizontal_packager = JobPackagerHorizontal(section_list, self._platform.max_processors, max_wrapped_jobs,
                                                    self.max_jobs, self._platform.processors_per_node)

        package_jobs = horizontal_packager.build_horizontal_package()

        jobs_resources = dict()

        current_package = None
        if package_jobs:
            machinefile_function = self._as_config.get_wrapper_machinefiles()
            if machinefile_function == 'COMPONENTS':
                jobs_resources = horizontal_packager.components_dict
            jobs_resources['MACHINEFILES'] = machinefile_function
            current_package = JobPackageHorizontal(package_jobs, jobs_resources=jobs_resources)
            packages.append(current_package)

        if self.remote_dependencies and current_package:
            remote_dependencies_dict['name_to_id'] = dict()
            remote_dependencies_dict['dependencies'] = dict()
            packages += horizontal_packager.get_next_packages(section, potential_dependency=current_package.name,
                                                              remote_dependencies_dict=remote_dependencies_dict)

        return packages, remote_dependencies_dict

    def _build_vertical_packages(self, section_list, max_wrapped_jobs):
        packages = []
        potential_dependency = None
        remote_dependencies_dict = dict()
        if self.remote_dependencies:
            remote_dependencies_dict['name_to_id'] = dict()
            remote_dependencies_dict['dependencies'] = dict()

        for job in section_list:
            if self.max_jobs > 0:
                if job.packed is False:
                    job.packed = True

                    if self.wrapper_type == 'vertical-mixed':
                        dict_jobs = self._jobs_list.get_ordered_jobs_by_date_member()
                        job_vertical_packager = JobPackagerVerticalMixed(dict_jobs, job, [job], job.wallclock, self.max_jobs,
                                                                                       max_wrapped_jobs, self._platform.max_wallclock)
                    else:
                        job_vertical_packager = JobPackagerVerticalSimple([job], job.wallclock, self.max_jobs,
                                                                            max_wrapped_jobs, self._platform.max_wallclock)

                    jobs_list = job_vertical_packager.build_vertical_package(job)
                    self.max_jobs -= len(jobs_list)
                    if job.status is Status.READY:
                        packages.append(JobPackageVertical(jobs_list))
                    else:
                        package = JobPackageVertical(jobs_list, potential_dependency)
                        packages.append(package)
                        remote_dependencies_dict['name_to_id'][potential_dependency] = -1
                        remote_dependencies_dict['dependencies'][package.name] = potential_dependency
                    if self.remote_dependencies:
                        child = job_vertical_packager.get_wrappable_child(jobs_list[-1])
                        if child is not None:
                            section_list.insert(section_list.index(job) + 1, child)
                            potential_dependency = packages[-1].name
            else:
                break
        return packages, remote_dependencies_dict

    def _build_hybrid_package(self, jobs_list, max_wrapped_jobs, section):
        jobs_resources = dict()
        jobs_resources['MACHINEFILES'] = self._as_config.get_wrapper_machinefiles()

        ## READY JOBS ##
        ## Create the horizontal ##
        horizontal_packager = JobPackagerHorizontal(jobs_list, self._platform.max_processors, max_wrapped_jobs,
                                                    self.max_jobs, self._platform.processors_per_node)
        if self.wrapper_type == 'vertical-horizontal':
            return self._build_vertical_horizontal_package(horizontal_packager, max_wrapped_jobs, jobs_resources)
        else:
            return self._build_horizontal_vertical_package(horizontal_packager, section, jobs_resources)

    def _build_horizontal_vertical_package(self, horizontal_packager, section, jobs_resources):
        total_wallclock = '00:00'
        horizontal_package = horizontal_packager.build_horizontal_package()
        horizontal_packager.create_sections_order(section)
        horizontal_packager.add_sectioncombo_processors(horizontal_packager.total_processors)
        horizontal_package.sort(key=lambda job: horizontal_packager.sort_by_expression(job.name))
        job = max(horizontal_package, key=attrgetter('total_wallclock'))
        wallclock = job.wallclock
        current_package = [horizontal_package]
        #current_package = []
        ## Get the next horizontal packages ##
        #self._maxTotalProcessors = horizontal_packager.total_processors
        total_processors =horizontal_packager.total_processors
        new_package=horizontal_packager.get_next_packages(section, max_wallclock=self._platform.max_wallclock,horizontal_vertical=True,total_processors=total_processors)
        if new_package is not None:
            current_package += new_package

        for i in range(len(current_package)):
            total_wallclock = sum_str_hours(total_wallclock, wallclock)
        total_processors = self._maxTotalProcessors

        return JobPackageHorizontalVertical(current_package, total_processors, total_wallclock,
                                            jobs_resources=jobs_resources)

    def _build_vertical_horizontal_package(self, horizontal_packager, max_wrapped_jobs, jobs_resources):
        total_wallclock = '00:00'

        horizontal_package = horizontal_packager.build_horizontal_package()
        total_processors = horizontal_packager.total_processors
        current_package = []

        ## Create the vertical ##
        for job in horizontal_package:
            job_list = JobPackagerVerticalSimple([job], job.wallclock, self.max_jobs,
                                                 max_wrapped_jobs,
                                                 self._platform.max_wallclock).build_vertical_package(job)
            current_package.append(job_list)

        for job in current_package[-1]:
            total_wallclock = sum_str_hours(total_wallclock, job.wallclock)

        return JobPackageVerticalHorizontal(current_package, total_processors, total_wallclock,
                                            jobs_resources=jobs_resources)


class JobPackagerVertical(object):

    def __init__(self, jobs_list, total_wallclock, max_jobs, max_wrapped_jobs, max_wallclock):
        self.jobs_list = jobs_list
        self.total_wallclock = total_wallclock
        self.max_jobs = max_jobs
        self.max_wrapped_jobs = max_wrapped_jobs
        self.max_wallclock = max_wallclock

    def build_vertical_package(self, job):
        if len(self.jobs_list) >= self.max_jobs or len(self.jobs_list) >= self.max_wrapped_jobs:
            return self.jobs_list
        child = self.get_wrappable_child(job)
        if child is not None:
            self.total_wallclock = sum_str_hours(self.total_wallclock, child.wallclock)
            if self.total_wallclock <= self.max_wallclock:
                child.packed = True
                self.jobs_list.append(child)
                return self.build_vertical_package(child)
        return self.jobs_list

    def get_wrappable_child(self, job):
        pass

    def _is_wrappable(self, job):
        pass


class JobPackagerVerticalSimple(JobPackagerVertical):

    def __init__(self, jobs_list, total_wallclock, max_jobs, max_wrapped_jobs, max_wallclock):
        super(JobPackagerVerticalSimple, self).__init__(jobs_list, total_wallclock, max_jobs, max_wrapped_jobs, max_wallclock)

    def get_wrappable_child(self, job):
        for child in job.children:
            if self._is_wrappable(child, job):
                return child
            continue
        return None

    def _is_wrappable(self, job, parent=None):
        if job.section != parent.section:
            return False
        for other_parent in job.parents:
            if other_parent.status != Status.COMPLETED and other_parent not in self.jobs_list:
                return False
        return True


class JobPackagerVerticalMixed(JobPackagerVertical):

    def __init__(self, dict_jobs, ready_job, jobs_list, total_wallclock, max_jobs, max_wrapped_jobs, max_wallclock):
        super(JobPackagerVerticalMixed, self).__init__(jobs_list, total_wallclock, max_jobs, max_wrapped_jobs, max_wallclock)
        self.ready_job = ready_job
        self.dict_jobs = dict_jobs

        date = dict_jobs.keys()[-1]
        member = dict_jobs[date].keys()[-1]
        if ready_job.date is not None:
            date = ready_job.date
        if ready_job.member is not None:
            member = ready_job.member

        self.sorted_jobs = dict_jobs[date][member]
        self.index = 0

    def get_wrappable_child(self, job):
        sorted_jobs = self.sorted_jobs

        for index in range(self.index, len(sorted_jobs)):
            child = sorted_jobs[index]
            if self._is_wrappable(child):
                self.index = index+1
                return child
            continue
        return None

    def _is_wrappable(self, job):
        if job.packed is False and (job.status == Status.READY or job.status == Status.WAITING):
            for parent in job.parents:
                if parent not in self.jobs_list and parent.status != Status.COMPLETED:
                    return False
            return True
        return False


class JobPackagerHorizontal(object):
    def __init__(self, job_list, max_processors, max_wrapped_jobs, max_jobs, processors_node):
        self.processors_node = processors_node
        self.max_processors = max_processors
        self.max_wrapped_jobs = max_wrapped_jobs
        self.job_list = job_list
        self.max_jobs = max_jobs
        self._current_processors = 0
        self._sort_order_dict = dict()
        self._components_dict = dict()
        self._section_processors = dict()

        self._maxTotalProcessors = 0
        self._sectionList = list()
        self._package_sections = dict()
    def build_horizontal_package(self,horizontal_vertical=False):
        current_package = []
        if horizontal_vertical:
            self._current_processors = 0
        for job in self.job_list:
            if self.max_jobs > 0 and len(current_package) < self.max_wrapped_jobs:
                self.max_jobs -= 1
                if int(job.tasks) != 0 and int(job.tasks) != int(self.processors_node) and \
                        int(job.tasks) < job.total_processors:
                    nodes = int(ceil(job.total_processors / float(job.tasks)))
                    total_processors = int(self.processors_node) * nodes
                else:
                    total_processors = job.total_processors
                if (self._current_processors + total_processors) <= int(self.max_processors):
                    current_package.append(job)
                    self._current_processors += total_processors
                else:
                    current_package = [job]
                    self._current_processors = total_processors
            else:
                break

        self.create_components_dict()


        return current_package

    def create_sections_order(self, jobs_sections):
        for i, section in enumerate(jobs_sections.split('&')):
            self._sort_order_dict[section] = i

    #EXIT FALSE IF A SECTION EXIST AND HAVE LESS PROCESSORS
    def add_sectioncombo_processors(self,total_processors_section):
        keySection = ""

        self._sectionList.sort()
        for section in self._sectionList:
            keySection += str(section)
        if keySection in self._package_sections:
            if self._package_sections[keySection] < total_processors_section:
                return False
        else:
            self._package_sections[keySection] = total_processors_section
        self._maxTotalProcessors=max(max(self._package_sections.values()),self._maxTotalProcessors)
        return True


    def sort_by_expression(self, jobname):
        jobname = jobname.split('_')[-1]
        return self._sort_order_dict[jobname]

    def get_next_packages(self, jobs_sections, max_wallclock=None, potential_dependency=None, remote_dependencies_dict=dict(),horizontal_vertical=False,total_processors=0):
        packages = []
        job = max(self.job_list, key=attrgetter('total_wallclock'))
        wallclock = job.wallclock
        total_wallclock = wallclock

        while self.max_jobs > 0:
            next_section_list = []
            for job in self.job_list:
                for child in job.children:
                    if job.section == child.section or (job.section in jobs_sections and child.section in jobs_sections) \
                            and child.status in [Status.READY, Status.WAITING]:
                        wrappable = True
                        for other_parent in child.parents:
                            if other_parent.status != Status.COMPLETED and other_parent not in self.job_list:
                                wrappable = False
                        if wrappable and child not in next_section_list:
                            next_section_list.append(child)

            next_section_list.sort(key=lambda job: self.sort_by_expression(job.name))
            self.job_list = next_section_list
            package_jobs = self.build_horizontal_package(horizontal_vertical)

            if package_jobs :
                #if not self.add_sectioncombo_processors(self.total_processors) and horizontal_vertical:
                if total_processors < self._current_processors:
                    return packages
                if max_wallclock:
                    total_wallclock = sum_str_hours(total_wallclock, wallclock)
                    if total_wallclock > max_wallclock:
                        return packages
                packages.append(package_jobs)
                if remote_dependencies_dict:
                    current_package = JobPackageHorizontal(package_jobs, potential_dependency)
                    remote_dependencies_dict['name_to_id'][potential_dependency] = -1
                    remote_dependencies_dict['dependencies'][current_package.name] = potential_dependency
            else:
                break

        return packages

    @property
    def total_processors(self):
        return self._current_processors

    @property
    def components_dict(self):
        return self._components_dict

    def create_components_dict(self):
        self._sectionList=[]
        for job in self.job_list:
            if job.section not in self._sectionList:
                self._sectionList.append(job.section)
            if job.section not in self._components_dict:

                self._components_dict[job.section] = dict()
                self._components_dict[job.section]['COMPONENTS'] = {parameter: job.parameters[parameter]
                                                                    for parameter in job.parameters.keys()
                                                                    if '_NUMPROC' in parameter }
