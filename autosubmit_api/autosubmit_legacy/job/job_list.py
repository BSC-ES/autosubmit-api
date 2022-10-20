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
import json

from bscearth.utils.config_parser import ConfigParserFactory

import os
import re
import pickle
import hashlib
import traceback
import datetime
import math
import random

# Spectral imports
import numpy as np
import networkx as nx
from scipy import sparse
from fnmatch import fnmatch
from collections import deque, OrderedDict
from threading import Thread
# End Spectral imports

from time import localtime, strftime, time, mktime
from shutil import move
from random import shuffle
from dateutil.relativedelta import *

from autosubmit_api.autosubmit_legacy.job.job import Job
from autosubmit_api.config.config_common import AutosubmitConfig
from bscearth.utils.log import Log
from autosubmit_api.autosubmit_legacy.job.job_dict import DicJobs
from autosubmit_api.autosubmit_legacy.job.job_utils import Dependency
from autosubmit_api.autosubmit_legacy.job.job_utils import SubJob
from autosubmit_api.autosubmit_legacy.job.job_utils import SubJobManager, job_times_to_text, datechunk_to_year
from autosubmit_api.performance.utils import calculate_ASYPD_perjob, calculate_SYPD_perjob
import autosubmit_api.components.jobs.utils as JUtils
from autosubmit_api.monitor.monitor import Monitor
from autosubmit_api.autosubmit_legacy.job.job_common import Status, Type
from bscearth.utils.date import date2str, parse_date, sum_str_hours
import autosubmit_api.experiment.common_db_requests as DbRequests
from autosubmit_api.autosubmit_legacy.job.job_packages import JobPackageSimple, JobPackageArray, JobPackageThread
from autosubmit_api.autosubmit_legacy.job.job_package_persistence import JobPackagePersistence
# from autosubmit_api.autosubmit_legacy.job.tree import Tree
import autosubmit_api.database.db_structure as DbStructure
from autosubmit_api.database.db_jobdata import JobDataStructure, JobRow, ExperimentGraphDrawing
from autosubmit_api.builders.experiment_history_builder import ExperimentHistoryDirector, ExperimentHistoryBuilder
from autosubmit_api.history.data_classes.job_data import JobData

from networkx import DiGraph
from autosubmit_api.autosubmit_legacy.job.job_utils import transitive_reduction
from autosubmit_api.common.utils import timestamp_to_datetime_format
from typing import List, Dict, Tuple


class JobList:
    """
    Class to manage the list of jobs to be run by autosubmit

    """

    def __init__(self, expid, config, parser_factory, job_list_persistence):
        self._persistence_path = os.path.join(
            config.LOCAL_ROOT_DIR, expid, "pkl")
        self._update_file = "updated_list_" + expid + ".txt"
        self._failed_file = "failed_job_list_" + expid + ".pkl"
        self._persistence_file = "job_list_" + expid
        self._job_list = list()
        self._expid = expid
        self._config = config
        self._parser_factory = parser_factory
        self._stat_val = Status()
        self._parameters = []
        self._date_list = []
        self._member_list = []
        self._chunk_list = []
        self._dic_jobs = dict()
        self._persistence = job_list_persistence
        self._graph = DiGraph()

        self.packages_dict = dict()
        self._ordered_jobs_by_date_member = dict()

        self.packages_id = dict()
        self.job_package_map = dict()
        self.sections_checked = set()
        self._wrapper_queue = None
        try:
            as_conf = AutosubmitConfig(
                self.expid, config, ConfigParserFactory())
            as_conf.reload()
            self._wrapper_queue = as_conf.get_wrapper_queue()
            # print("Wrapper Q: {}".format(self._wrapper_queue))
        except Exception as exp:
            pass
            # print(exp)

    @property
    def expid(self):
        """
        Returns the experiment identifier

        :return: experiment's identifierexpid
        :rtype: str
        """
        return self._expid

    @property
    def graph(self):
        """
        Returns the graph

        :return: graph
        :rtype: networkx graph
        """
        return self._graph

    @graph.setter
    def graph(self, value):
        self._graph = value

    def generate(self, date_list, member_list, num_chunks, chunk_ini, parameters, date_format, default_retrials,
                 default_job_type, wrapper_type=None, wrapper_jobs=None, new=True, notransitive=False, run_only_members=[]):
        """
        Creates all jobs needed for the current workflow

        :param default_job_type: default type for jobs
        :type default_job_type: str
        :param date_list: start dates
        :type date_list: list
        :param member_list: members
        :type member_list: list
        :param num_chunks: number of chunks to run
        :type num_chunks: int
        :param chunk_ini: the experiment will start by the given chunk
        :type chunk_ini: int
        :param parameters: parameters for the jobs
        :type parameters: dict
        :param date_format: option to format dates
        :type date_format: str
        :param default_retrials: default retrials for ech job
        :type default_retrials: intO
        :param new: is it a new generation?
        :type new: bool
        """
        try:
            self._parameters = parameters
            self._date_list = date_list
            self._member_list = member_list

            chunk_list = range(chunk_ini, num_chunks + 1)
            self._chunk_list = chunk_list

            jobs_parser = self._get_jobs_parser()
            dic_jobs = DicJobs(self, jobs_parser, date_list, member_list,
                               chunk_list, date_format, default_retrials)
            self._dic_jobs = dic_jobs
            priority = 0

            # Log.info("Creating jobs...")
            time_0 = time()
            jobs_data = dict()
            # Reading from pkl
            if not new:
                jobs_data = {str(row[0]): row for row in self.load()}

            # for key in jobs_data.keys():
            #     print(str(key) + " ~ " + str(jobs_data[key]))

            self._create_jobs(dic_jobs, jobs_parser, priority,
                              default_job_type, jobs_data)
            # print("Create jobs time {0}".format(time() - time_0))

            # Log.info("Adding dependencies...")
            # time_0 = time()
            self._add_dependencies(
                date_list, member_list, chunk_list, dic_jobs, jobs_parser, self.graph)
            # print("Add dependencies time {0}".format(time() - time_0))
            # Log.info("Removing redundant dependencies...")
            # time_0 = time()
            self.update_genealogy(new, notransitive)
            for job in self._job_list:
                job.parameters = parameters
            # print("Remove redundante time {0}".format(time() - time_0))
            # Checking for member constraints
            if len(run_only_members) > 0:
                # Found
                old_job_list = [job for job in self._job_list]
                self._job_list = [
                    job for job in old_job_list if job.member is None or job.member in run_only_members or job.status not in [Status.WAITING, Status.READY]]
                for job in self._job_list:
                    job.parents = [
                        jobp for jobp in job.parents if jobp in self._job_list]
                    job.children = [
                        jobc for jobc in job._children if jobc in self._job_list]

            if wrapper_type == 'vertical-mixed':
                self._ordered_jobs_by_date_member = self._create_sorted_dict_jobs(
                    wrapper_jobs)
        except AssertionError as e:
            raise AssertionError(str(e))
        except Exception as e:
            print(e)

    @staticmethod
    def _add_dependencies(date_list, member_list, chunk_list, dic_jobs, jobs_parser, graph, option="DEPENDENCIES"):
        for job_section in jobs_parser.sections():
            # Log.debug("Adding dependencies for {0} jobs".format(job_section))

            # If does not have dependencies, do nothing
            if not jobs_parser.has_option(job_section, option):
                continue

            dependencies_keys = jobs_parser.get(
                job_section, option).split()
            dependencies = JobList._manage_dependencies(
                dependencies_keys, dic_jobs, job_section)

            for job in dic_jobs.get_jobs(job_section):
                num_jobs = 1
                if isinstance(job, list):
                    num_jobs = len(job)
                for i in xrange(num_jobs):
                    _job = job[i] if num_jobs > 1 else job
                    JobList._manage_job_dependencies(dic_jobs, _job, date_list, member_list, chunk_list, dependencies_keys,
                                                     dependencies, graph)

    @staticmethod
    def _manage_dependencies(dependencies_keys, dic_jobs, job_section):
        dependencies = dict()
        for key in dependencies_keys:
            distance = None
            splits = None
            sign = None

            if '-' not in key and '+' not in key and '*' not in key:
                section = key
            else:
                if '-' in key:
                    sign = '-'
                elif '+' in key:
                    sign = '+'
                elif '*' in key:
                    sign = '*'
                key_split = key.split(sign)
                section = key_split[0]
                distance = int(key_split[1])

            if '[' in section:
                section_name = section[0:section.find("[")]
                splits_section = int(
                    dic_jobs.get_option(section_name, 'SPLITS', 0))
                splits = JobList._calculate_splits_dependencies(
                    section, splits_section)
                section = section_name

            dependency_running_type = dic_jobs.get_option(
                section, 'RUNNING', 'once').lower()
            delay = int(dic_jobs.get_option(section, 'DELAY', -1))
            select_chunks_opt = dic_jobs.get_option(
                job_section, 'SELECT_CHUNKS', None)
            selected_chunks = []
            if select_chunks_opt is not None:
                if '*' in select_chunks_opt:
                    sections_chunks = select_chunks_opt.split(' ')
                    for section_chunk in sections_chunks:
                        info = section_chunk.split('*')
                        if info[0] in key:
                            for relation in xrange(1, len(info)):
                                auxiliar_relation_list = []
                                for location in info[relation].split('-'):
                                    auxiliar_chunk_list = []
                                    location = location.strip('[').strip(']')
                                    if ':' in location:
                                        if len(location) == 3:
                                            for chunk_number in xrange(int(location[0]), int(location[2]) + 1):
                                                auxiliar_chunk_list.append(
                                                    chunk_number)
                                        elif len(location) == 2:
                                            if ':' == location[0]:
                                                for chunk_number in xrange(0, int(location[1]) + 1):
                                                    auxiliar_chunk_list.append(
                                                        chunk_number)
                                            elif ':' == location[1]:
                                                for chunk_number in xrange(int(location[0]) + 1, len(dic_jobs._chunk_list) - 1):
                                                    auxiliar_chunk_list.append(
                                                        chunk_number)
                                    elif ',' in location:
                                        for chunk in location.split(','):
                                            auxiliar_chunk_list.append(
                                                int(chunk))
                                    elif re.match('^[0-9]+$', location):
                                        auxiliar_chunk_list.append(
                                            int(location))
                                    auxiliar_relation_list.append(
                                        auxiliar_chunk_list)
                                selected_chunks.append(auxiliar_relation_list)
            if len(selected_chunks) >= 1:
                # []select_chunks_dest,select_chunks_orig
                dependency = Dependency(
                    section, distance, dependency_running_type, sign, delay, splits, selected_chunks)
            else:
                # []select_chunks_dest,select_chunks_orig
                dependency = Dependency(
                    section, distance, dependency_running_type, sign, delay, splits, [])

            dependencies[key] = dependency
        return dependencies

    @staticmethod
    def _calculate_splits_dependencies(section, max_splits):
        splits_list = section[section.find("[") + 1:section.find("]")]
        splits = []
        for str_split in splits_list.split(","):
            if str_split.find(":") != -1:
                numbers = str_split.split(":")
                # change this to be checked in job_common.py
                max_splits = min(int(numbers[1]), max_splits)
                for count in range(int(numbers[0]), max_splits + 1):
                    splits.append(int(str(count).zfill(len(numbers[0]))))
            else:
                if int(str_split) <= max_splits:
                    splits.append(int(str_split))
        return splits

    @staticmethod
    def _manage_job_dependencies(dic_jobs, job, date_list, member_list, chunk_list, dependencies_keys, dependencies,
                                 graph):
        for key in dependencies_keys:
            dependency = dependencies[key]
            skip, (chunk, member, date) = JobList._calculate_dependency_metadata(job.chunk, chunk_list,
                                                                                 job.member, member_list,
                                                                                 job.date, date_list,
                                                                                 dependency)
            if skip:
                continue
            chunk_relations_to_add = list()
            if len(dependency.select_chunks_orig) > 0:  # find chunk relation
                relation_indx = 0
                while relation_indx < len(dependency.select_chunks_orig):
                    if len(dependency.select_chunks_orig[relation_indx]) == 0 or job.chunk in dependency.select_chunks_orig[relation_indx] or job.chunk is None:
                        chunk_relations_to_add.append(relation_indx)
                    relation_indx += 1
                relation_indx -= 1

            # If doesn't contain select_chunks or running isn't chunk . ...
            if len(dependency.select_chunks_orig) <= 0 or job.chunk is None or len(chunk_relations_to_add) > 0:
                parents_jobs = dic_jobs.get_jobs(
                    dependency.section, date, member, chunk)
                for parent in parents_jobs:
                    if dependency.delay == -1 or chunk > dependency.delay:
                        if isinstance(parent, list):
                            if job.split is not None:
                                parent = filter(
                                    lambda _parent: _parent.split == job.split, parent)[0]
                            else:
                                if dependency.splits is not None:
                                    parent = filter(
                                        lambda _parent: _parent.split in dependency.splits, parent)
                        if len(dependency.select_chunks_dest) <= 0 or parent.chunk is None:
                            job.add_parent(parent)
                            JobList._add_edge(graph, job, parent)
                        else:
                            visited_parents = set()
                            for relation_indx in chunk_relations_to_add:
                                if parent.chunk in dependency.select_chunks_dest[relation_indx] or len(dependency.select_chunks_dest[relation_indx]) == 0:
                                    if parent not in visited_parents:
                                        job.add_parent(parent)
                                        JobList._add_edge(graph, job, parent)
                                    visited_parents.add(parent)

            JobList.handle_frequency_interval_dependencies(chunk, chunk_list, date, date_list, dic_jobs, job, member,
                                                           member_list, dependency.section, graph)

    @staticmethod
    def _calculate_dependency_metadata(chunk, chunk_list, member, member_list, date, date_list, dependency):
        skip = False
        if dependency.sign is '-':
            if chunk is not None and dependency.running == 'chunk':
                chunk_index = chunk_list.index(chunk)
                if chunk_index >= dependency.distance:
                    chunk = chunk_list[chunk_index - dependency.distance]
                else:
                    skip = True
            elif member is not None and dependency.running in ['chunk', 'member']:
                member_index = member_list.index(member)
                if member_index >= dependency.distance:
                    member = member_list[member_index - dependency.distance]
                else:
                    skip = True
            elif date is not None and dependency.running in ['chunk', 'member', 'startdate']:
                date_index = date_list.index(date)
                if date_index >= dependency.distance:
                    date = date_list[date_index - dependency.distance]
                else:
                    skip = True

        if dependency.sign is '+':
            if chunk is not None and dependency.running == 'chunk':
                chunk_index = chunk_list.index(chunk)
                if (chunk_index + dependency.distance) < len(chunk_list):
                    chunk = chunk_list[chunk_index + dependency.distance]
                else:  # calculating the next one possible
                    temp_distance = dependency.distance
                    while temp_distance > 0:
                        temp_distance -= 1
                        if (chunk_index + temp_distance) < len(chunk_list):
                            chunk = chunk_list[chunk_index + temp_distance]
                            break

            elif member is not None and dependency.running in ['chunk', 'member']:
                member_index = member_list.index(member)
                if (member_index + dependency.distance) < len(member_list):
                    member = member_list[member_index + dependency.distance]
                else:
                    skip = True
            elif date is not None and dependency.running in ['chunk', 'member', 'startdate']:
                date_index = date_list.index(date)
                if (date_index + dependency.distance) < len(date_list):
                    date = date_list[date_index - dependency.distance]
                else:
                    skip = True
        return skip, (chunk, member, date)

    @staticmethod
    def handle_frequency_interval_dependencies(chunk, chunk_list, date, date_list, dic_jobs, job, member, member_list,
                                               section_name, graph):
        if job.wait and job.frequency > 1:
            if job.chunk is not None:
                max_distance = (chunk_list.index(chunk) + 1) % job.frequency
                if max_distance == 0:
                    max_distance = job.frequency
                for distance in range(1, max_distance):
                    for parent in dic_jobs.get_jobs(section_name, date, member, chunk - distance):
                        job.add_parent(parent)
                        JobList._add_edge(graph, job, parent)
            elif job.member is not None:
                member_index = member_list.index(job.member)
                max_distance = (member_index + 1) % job.frequency
                if max_distance == 0:
                    max_distance = job.frequency
                for distance in range(1, max_distance, 1):
                    for parent in dic_jobs.get_jobs(section_name, date,
                                                    member_list[member_index - distance], chunk):
                        job.add_parent(parent)
                        JobList._add_edge(graph, job, parent)
            elif job.date is not None:
                date_index = date_list.index(job.date)
                max_distance = (date_index + 1) % job.frequency
                if max_distance == 0:
                    max_distance = job.frequency
                for distance in range(1, max_distance, 1):
                    for parent in dic_jobs.get_jobs(section_name, date_list[date_index - distance],
                                                    member, chunk):
                        job.add_parent(parent)
                        JobList._add_edge(graph, job, parent)

    @staticmethod
    def _add_edge(graph, job, parents):
        num_parents = 1
        if isinstance(parents, list):
            num_parents = len(parents)
        for i in range(num_parents):
            parent = parents[i] if isinstance(parents, list) else parents
            graph.add_edge(parent.name, job.name)

    @staticmethod
    def _create_jobs(dic_jobs, parser, priority, default_job_type, jobs_data=dict()):
        for section in parser.sections():
            # Log.debug("Creating {0} jobs".format(section))
            dic_jobs.read_section(
                section, priority, default_job_type, jobs_data)
            priority += 1

    def _create_sorted_dict_jobs(self, wrapper_jobs):
        dict_jobs = dict()
        for date in self._date_list:
            dict_jobs[date] = dict()
            for member in self._member_list:
                dict_jobs[date][member] = list()
        num_chunks = len(self._chunk_list)

        filtered_jobs_list = filter(
            lambda job: job.section in wrapper_jobs, self._job_list)

        filtered_jobs_fake_date_member, fake_original_job_map = self._create_fake_dates_members(
            filtered_jobs_list)

        sections_running_type_map = dict()
        for section in wrapper_jobs.split(" "):
            sections_running_type_map[section] = self._dic_jobs.get_option(
                section, "RUNNING", 'once')

        for date in self._date_list:
            str_date = self._get_date(date)
            for member in self._member_list:
                sorted_jobs_list = filter(lambda job: job.name.split("_")[1] == str_date and
                                          job.name.split("_")[2] == member, filtered_jobs_fake_date_member)

                previous_job = sorted_jobs_list[0]
                section_running_type = sections_running_type_map[previous_job.section]

                jobs_to_sort = [previous_job]
                previous_section_running_type = None

                for index in range(1, len(sorted_jobs_list) + 1):
                    if index < len(sorted_jobs_list):
                        job = sorted_jobs_list[index]

                        if previous_job.section != job.section:
                            previous_section_running_type = section_running_type
                            section_running_type = sections_running_type_map[job.section]

                    if (previous_section_running_type != None and previous_section_running_type != section_running_type) \
                            or index == len(sorted_jobs_list):

                        jobs_to_sort = sorted(jobs_to_sort, key=lambda k: (k.name.split('_')[1], (k.name.split('_')[2]),
                                                                           (int(k.name.split('_')[3])
                                                                            if len(k.name.split('_')) == 5 else num_chunks + 1)))

                        for idx in range(0, len(jobs_to_sort)):
                            if jobs_to_sort[idx] in fake_original_job_map:
                                fake_job = jobs_to_sort[idx]
                                jobs_to_sort[idx] = fake_original_job_map[fake_job]

                        dict_jobs[date][member] += jobs_to_sort
                        jobs_to_sort = []

                    jobs_to_sort.append(job)
                    previous_job = job

        return dict_jobs

    def _create_fake_dates_members(self, filtered_jobs_list):
        filtered_jobs_fake_date_member = []
        fake_original_job_map = dict()

        import copy
        for job in filtered_jobs_list:
            fake_job = None
            # running once and synchronize date
            if job.date is None and job.member is None:
                date = self._date_list[-1]
                member = self._member_list[-1]

                fake_job = copy.deepcopy(job)
                fake_job.name = fake_job.name.split('_', 1)[0] + "_" + self._get_date(date) + "_" \
                    + member + "_" + fake_job.name.split("_", 1)[1]
                filtered_jobs_fake_date_member.append(fake_job)
                fake_original_job_map[fake_job] = job
            # running date or synchronize member
            elif job.member is None:
                member = self._member_list[-1]
                fake_job = copy.deepcopy(job)
                fake_job.name = fake_job.name.split('_', 2)[0] + "_" + fake_job.name.split('_', 2)[
                    1] + "_" + member + "_" + fake_job.name.split("_", 2)[2]
                filtered_jobs_fake_date_member.append(fake_job)
                fake_original_job_map[fake_job] = job

            if fake_job is None:
                filtered_jobs_fake_date_member.append(job)

        return filtered_jobs_fake_date_member, fake_original_job_map

    def _get_date(self, date):
        date_format = ''
        if date.hour > 1:
            date_format = 'H'
        if date.minute > 1:
            date_format = 'M'
        str_date = date2str(date, date_format)
        return str_date

    def __len__(self):
        return self._job_list.__len__()

    def get_date_list(self):
        """
        Get inner date list

        :return: date list
        :rtype: list
        """
        return self._date_list

    def get_member_list(self):
        """
        Get inner member list

        :return: member list
        :rtype: list
        """
        return self._member_list

    def get_chunk_list(self):
        """
        Get inner chunk list

        :return: chunk list
        :rtype: list
        """
        return self._chunk_list

    def get_job_list(self):
        """
        Get inner job list

        :return: job list
        :rtype: list
        """
        return self._job_list

    def get_date_format(self):
        date_format = ''
        for date in self.get_date_list():
            if date.hour > 1:
                date_format = 'H'
            if date.minute > 1:
                date_format = 'M'
        return date_format

    def get_ordered_jobs_by_date_member(self):
        """
        Get the dictionary of jobs ordered according to wrapper's expression divided by date and member

        :return: jobs ordered divided by date and member
        :rtype: dict
        """
        return self._ordered_jobs_by_date_member

    def get_completed(self, platform=None):
        """
        Returns a list of completed jobs

        :param platform: job platform
        :type platform: HPCPlatform
        :return: completed jobs
        :rtype: list
        """
        return [job for job in self._job_list if (platform is None or job.platform is platform) and
                job.status == Status.COMPLETED]

    def get_uncompleted(self, platform=None):
        """
        Returns a list of completed jobs

        :param platform: job platform
        :type platform: HPCPlatform
        :return: completed jobs
        :rtype: list
        """
        return [job for job in self._job_list if (platform is None or job.platform is platform) and
                job.status != Status.COMPLETED]

    def get_submitted(self, platform=None):
        """
        Returns a list of submitted jobs

        :param platform: job platform
        :type platform: HPCPlatform
        :return: submitted jobs
        :rtype: list
        """
        return [job for job in self._job_list if (platform is None or job.platform is platform) and
                job.status == Status.SUBMITTED]

    def get_running(self, platform=None):
        """
        Returns a list of jobs running

        :param platform: job platform
        :type platform: HPCPlatform
        :return: running jobs
        :rtype: list
        """
        return [job for job in self._job_list if (platform is None or job.platform is platform) and
                job.status == Status.RUNNING]

    def get_queuing(self, platform=None):
        """
        Returns a list of jobs queuing

        :param platform: job platform
        :type platform: HPCPlatform
        :return: queuedjobs
        :rtype: list
        """
        return [job for job in self._job_list if (platform is None or job.platform is platform) and
                job.status == Status.QUEUING]

    def get_failed(self, platform=None):
        """
        Returns a list of failed jobs

        :param platform: job platform
        :type platform: HPCPlatform
        :return: failed jobs
        :rtype: list
        """
        return [job for job in self._job_list if (platform is None or job.platform is platform) and
                job.status == Status.FAILED]

    def get_unsubmitted(self, platform=None):
        """
        Returns a list of unsummited jobs

        :param platform: job platform
        :type platform: HPCPlatform
        :return: all jobs
        :rtype: list
        """
        return [job for job in self._job_list if (platform is None or job.platform is platform) and
                (job.status != Status.SUBMITTED and job.status != Status.QUEUING and job.status == Status.RUNNING and job.status == Status.COMPLETED)]

    def get_all(self, platform=None):
        """
        Returns a list of all jobs

        :param platform: job platform
        :type platform: HPCPlatform
        :return: all jobs
        :rtype: list
        """
        return [job for job in self._job_list]

    def get_ready(self, platform=None):
        """
        Returns a list of ready jobs

        :param platform: job platform
        :type platform: HPCPlatform
        :return: ready jobs
        :rtype: list
        """
        return [job for job in self._job_list if (platform is None or job.platform is platform) and
                job.status == Status.READY]

    def get_waiting(self, platform=None):
        """
        Returns a list of jobs waiting

        :param platform: job platform
        :type platform: HPCPlatform
        :return: waiting jobs
        :rtype: list
        """
        return [job for job in self._job_list if (platform is None or job.platform is platform) and
                job.status == Status.WAITING]

    def get_unknown(self, platform=None):
        """
        Returns a list of jobs on unknown state

        :param platform: job platform
        :type platform: HPCPlatform
        :return: unknown state jobs
        :rtype: list
        """
        return [job for job in self._job_list if (platform is None or job.platform is platform) and
                job.status == Status.UNKNOWN]

    def get_suspended(self, platform=None):
        """
        Returns a list of jobs on unknown state

        :param platform: job platform
        :type platform: HPCPlatform
        :return: unknown state jobs
        :rtype: list
        """
        return [job for job in self._job_list if (platform is None or job.platform is platform) and
                job.status == Status.SUSPENDED]

    def get_in_queue(self, platform=None):
        """
        Returns a list of jobs in the platforms (Submitted, Running, Queuing, Unknown)

        :param platform: job platform
        :type platform: HPCPlatform
        :return: jobs in platforms
        :rtype: list
        """
        return self.get_submitted(platform) + self.get_running(platform) + self.get_queuing(
            platform) + self.get_unknown(platform)

    def get_not_in_queue(self, platform=None):
        """
        Returns a list of jobs NOT in the platforms (Ready, Waiting)

        :param platform: job platform
        :type platform: HPCPlatform
        :return: jobs not in platforms
        :rtype: list
        """
        return self.get_ready(platform) + self.get_waiting(platform)

    def get_finished(self, platform=None):
        """
        Returns a list of jobs finished (Completed, Failed)


        :param platform: job platform
        :type platform: HPCPlatform
        :return: finished jobs
        :rtype: list
        """
        return self.get_completed(platform) + self.get_failed(platform)

    def get_active(self, platform=None):
        """
        Returns a list of active jobs (In platforms, Ready)

        :param platform: job platform
        :type platform: HPCPlatform
        :return: active jobs
        :rtype: list
        """
        return self.get_in_queue(platform) + self.get_ready(platform)

    def get_job_by_name(self, name):
        """
        Returns the job that its name matches parameter name

        :parameter name: name to look for
        :type name: str
        :return: found job
        :rtype: job
        """
        for job in self._job_list:
            if job.name == name:
                return job
        Log.warning("We could not find that job {0} in the list!!!!", name)

    def get_in_queue_grouped_id(self, platform):
        jobs = self.get_in_queue(platform)
        jobs_by_id = dict()
        for job in jobs:
            if job.id not in jobs_by_id:
                jobs_by_id[job.id] = list()
            jobs_by_id[job.id].append(job)
        return jobs_by_id

    def get_in_ready_grouped_id(self, platform):
        jobs = []
        [jobs.append(job) for job in jobs if (
            platform is None or job._platform.name is platform.name)]

        jobs_by_id = dict()
        for job in jobs:
            if job.id not in jobs_by_id:
                jobs_by_id[job.id] = list()
            jobs_by_id[job.id].append(job)
        return jobs_by_id

    def sort_by_name(self):
        """
        Returns a list of jobs sorted by name

        :return: jobs sorted by name
        :rtype: list
        """
        return sorted(self._job_list, key=lambda k: k.name)

    def sort_by_id(self):
        """
        Returns a list of jobs sorted by id

        :return: jobs sorted by ID
        :rtype: list
        """
        return sorted(self._job_list, key=lambda k: k.id)

    def sort_by_type(self):
        """
        Returns a list of jobs sorted by type

        :return: job sorted by type
        :rtype: list
        """
        return sorted(self._job_list, key=lambda k: k.type)

    def sort_by_status(self):
        """
        Returns a list of jobs sorted by status

        :return: job sorted by status
        :rtype: list
        """
        return sorted(self._job_list, key=lambda k: k.status)

    @staticmethod
    def load_file(filename):
        """
        Recreates an stored joblist from the pickle file

        :param filename: pickle file to load
        :type filename: str
        :return: loaded joblist object
        :rtype: JobList
        """
        if os.path.exists(filename):
            fd = open(filename, 'rw')
            return pickle.load(fd)
        else:
            Log.critical('File {0} does not exist'.format(filename))
            return list()

    def load(self):
        """
        Recreates an stored job list from the persistence

        :return: loaded job list object
        :rtype: JobList
        """
        # Log.info("Loading JobList")
        return self._persistence.load(self._persistence_path, self._persistence_file)

    def save(self):
        """
        Persists the job list
        """
        self._persistence.save(self._persistence_path,
                               self._persistence_file, self._job_list)

    def update_from_file(self, store_change=True):
        """
        Updates jobs list on the fly from and update file
        :param store_change: if True, renames the update file to avoid reloading it at the next iteration
        """
        if os.path.exists(os.path.join(self._persistence_path, self._update_file)):
            Log.info("Loading updated list: {0}".format(
                os.path.join(self._persistence_path, self._update_file)))
            for line in open(os.path.join(self._persistence_path, self._update_file)):
                if line.strip() == '':
                    continue
                job = self.get_job_by_name(line.split()[0])
                if job:
                    job.status = self._stat_val.retval(line.split()[1])
                    job.fail_count = 0
            now = localtime()
            output_date = strftime("%Y%m%d_%H%M", now)
            if store_change:
                move(os.path.join(self._persistence_path, self._update_file),
                     os.path.join(self._persistence_path, self._update_file +
                                  "_" + output_date))

    @property
    def parameters(self):
        """
        List of parameters common to all jobs
        :return: parameters
        :rtype: dict
        """
        return self._parameters

    @parameters.setter
    def parameters(self, value):
        self._parameters = value

    def update_list(self, as_conf, store_change=True, fromSetStatus=False):
        """
        Updates job list, resetting failed jobs and changing to READY all WAITING jobs with all parents COMPLETED

        :param as_conf: autosubmit config object
        :type as_conf: AutosubmitConfig
        :return: True if job status were modified, False otherwise
        :rtype: bool
        """
        # load updated file list
        save = False
        if self.update_from_file(store_change):
            save = store_change

        # reset jobs that has failed less than 10 times
        Log.debug('Updating FAILED jobs')
        for job in self.get_failed():
            job.inc_fail_count()
            if not hasattr(job, 'retrials') or job.retrials is None:
                retrials = as_conf.get_retrials()
            else:
                retrials = job.retrials

            if job.fail_count <= retrials:
                tmp = [
                    parent for parent in job.parents if parent.status == Status.COMPLETED]
                if len(tmp) == len(job.parents):
                    job.status = Status.READY
                    job.packed = False
                    save = True
                    Log.debug(
                        "Resetting job: {0} status to: READY for retrial...".format(job.name))
                else:
                    job.status = Status.WAITING
                    save = True
                    job.packed = False
                    Log.debug(
                        "Resetting job: {0} status to: WAITING for parents completion...".format(job.name))

        # if waiting jobs has all parents completed change its State to READY

        for job in self.get_completed():

            if job.synchronize is not None:  # and job in self.get_active():
                Log.debug('Updating SYNC jobs')
                tmp = [
                    parent for parent in job.parents if parent.status == Status.COMPLETED]
                if len(tmp) != len(job.parents):
                    job.status = Status.WAITING
                    save = True
                    Log.debug(
                        "Resetting sync job: {0} status to: WAITING for parents completion...".format(job.name))
        Log.debug('Update finished')

        Log.debug('Updating WAITING jobs')
        for job in self.get_waiting():
            if not fromSetStatus:
                tmp = [
                    parent for parent in job.parents if parent.status == Status.COMPLETED]
                if len(tmp) == len(job.parents):
                    job.status = Status.READY
                    save = True
                    Log.debug(
                        "Setting job: {0} status to: READY (all parents completed)...".format(job.name))
        Log.debug('Update finished')

        return save

    def update_genealogy(self, new=True, notransitive=False):
        """
        When we have created the job list, every type of job is created.
        Update genealogy remove jobs that have no templates
        :param new: if it is a new job list or not
        :type new: bool
        """
        # print("Update Genealogy Start")
        for job in self._job_list[:]:
            if job.file is None or job.file == '':
                self._remove_job(job)

        # Simplifying dependencies: if a parent is already an ancestor of another parent,
        # we remove parent dependency
        time_0 = time()
        if not notransitive:
            # Transitive reduction required
            current_structure = None
            try:
                current_structure = DbStructure.get_structure(
                    self.expid, self._config.STRUCTURES_DIR)
                # pass
            except Exception as exp:
                print(exp)
                pass
            # print("Lengths : " + str(len(self._job_list)) + "\t" +
            #       str(len(current_structure.keys())))

            structure_valid = False
            if ((current_structure) and (len(self._job_list) == len(current_structure.keys()))):
                structure_valid = True
                # print(current_structure.keys())
                # Structure exists and is valid, use it as a source of dependencies
                for job in self._job_list:
                    if job.name not in current_structure:
                        structure_valid = False
                        continue
                if structure_valid == True:
                    # Log.info("Using existing valid structure.")
                    for job in self._job_list:
                        children_to_remove = [
                            child for child in job.children if child.name not in current_structure[job.name]]
                        # print("Actual {} -> {}".format(job.name,
                        #       [x.name for x in job.children]))
                        # print("Structure {} -> {}".format(job.name,
                        #       current_structure[job.name]))
                        for child in children_to_remove:
                            job.children.remove(child)
                            child.parents.remove(job)
            if structure_valid == False:
                # Structure does not exist or it is not be updated, attempt to create it.
                # print("Current: ")
                # print(current_structure)
                # Log.info("Updating structure persistence...")
                self.graph = transitive_reduction(self.graph)
                for job in self._job_list:
                    children_to_remove = [
                        child for child in job.children if child.name not in self.graph.neighbors(job.name)]
                    for child in children_to_remove:
                        job.children.remove(child)
                        child.parents.remove(job)
                # The API no longer needs to generate a structure
                # try:
                #     DbStructure.save_structure(
                #         self.graph, self.expid, self._config.STRUCTURES_DIR)
                # except Exception as exp:
                #     pass
        # print("Update Geanology took {}".format(time() - time_0))
        for job in self._job_list:
            if not job.has_parents() and new:
                job.status = Status.READY
        # print("Update Genealogy End")

    def check_scripts(self, as_conf):
        """
        When we have created the scripts, all parameters should have been substituted.
        %PARAMETER% handlers not allowed

        :param as_conf: experiment configuration
        :type as_conf: AutosubmitConfig
        """
        Log.info("Checking scripts...")
        out = True

        for job in self._job_list:
            if job.check.lower() == 'on_submission':
                continue
            if job.check.lower() != 'true':
                show_logs = False
                if job.section not in self.sections_checked:
                    Log.warning(
                        'Template {0} will be checked without logs'.format(job.section))
            elif job.section in self.sections_checked:
                show_logs = False
            else:
                show_logs = True

            if not job.check_script(as_conf, self.parameters, show_logs):
                out = False
                if show_logs:
                    Log.warning(
                        "Invalid parameter substitution in {0} template", job.section)
            self.sections_checked.add(job.section)
        if out:
            Log.result("Scripts OK")
        else:
            Log.warning("Scripts check failed")
            Log.user_warning(
                "Running after failed scripts check is at your own risk!")
        return out

    def _remove_job(self, job):
        """
        Remove a job from the list

        :param job: job to remove
        :type job: Job
        """
        for child in job.children:
            for parent in job.parents:
                child.add_parent(parent)
            child.delete_parent(job)

        for parent in job.parents:
            parent.children.remove(job)

        self._job_list.remove(job)

    def rerun(self, chunk_list, notransitive=False, monitor=False):
        """
        Updates job list to rerun the jobs specified by chunk_list

        :param chunk_list: list of chunks to rerun
        :type chunk_list: str
        """
        jobs_parser = self._get_jobs_parser()

        Log.info("Adding dependencies...")
        dependencies = dict()
        for job_section in jobs_parser.sections():
            Log.debug(
                "Reading rerun dependencies for {0} jobs".format(job_section))

            # If does not has rerun dependencies, do nothing
            if not jobs_parser.has_option(job_section, "RERUN_DEPENDENCIES"):
                continue

            dependencies_keys = jobs_parser.get(
                job_section, "RERUN_DEPENDENCIES").split()
            dependencies = JobList._manage_dependencies(
                dependencies_keys, self._dic_jobs)

        for job in self._job_list:
            job.status = Status.COMPLETED

        data = json.loads(chunk_list)
        for d in data['sds']:
            date = parse_date(d['sd'])
            Log.debug("Date: {0}", date)
            for m in d['ms']:
                member = m['m']
                Log.debug("Member: " + member)
                previous_chunk = 0
                for c in m['cs']:
                    Log.debug("Chunk: " + c)
                    chunk = int(c)
                    for job in [i for i in self._job_list if i.date == date and i.member == member and (i.chunk == chunk)]:

                        if not job.rerun_only or chunk != previous_chunk + 1:
                            job.status = Status.WAITING
                            Log.debug("Job: " + job.name)

                        job_section = job.section
                        if job_section not in dependencies:
                            continue

                        for key in dependencies_keys:
                            skip, (current_chunk, current_member, current_date) = JobList._calculate_dependency_metadata(chunk, member, date,
                                                                                                                         dependencies[key])
                            if skip:
                                continue

                            section_name = dependencies[key].section
                            for parent in self._dic_jobs.get_jobs(section_name, current_date, current_member,
                                                                  current_chunk):
                                parent.status = Status.WAITING
                                Log.debug("Parent: " + parent.name)

        for job in [j for j in self._job_list if j.status == Status.COMPLETED]:
            if job.synchronize is None:
                self._remove_job(job)

        self.update_genealogy(notransitive=notransitive)
        for job in [j for j in self._job_list if j.synchronize != None]:
            if job.status == Status.COMPLETED:
                job.status = Status.WAITING
            else:
                self._remove_job(job)

    def _get_jobs_parser(self):
        jobs_parser = self._parser_factory.create_parser()
        jobs_parser.optionxform = str
        jobs_parser.read(
            os.path.join(self._config.LOCAL_ROOT_DIR, self._expid, 'conf', "jobs_" + self._expid + ".conf"))
        return jobs_parser

    def remove_rerun_only_jobs(self, notransitive=False):
        """
        Removes all jobs to be run only in reruns
        """
        flag = False
        for job in set(self._job_list):
            if job.rerun_only:
                self._remove_job(job)
                flag = True

        if flag:
            self.update_genealogy(notransitive=notransitive)
        del self._dic_jobs

    # def get_tree_representation(self):
    #     """
    #     Return a tree (treelib) representation of the list of jobs

    #     :return: job list hierarchy as a tree
    #     :rtype: treelib instance
    #     """
    #     allJobs = self.get_all()
    #     tree = Tree(allJobs)
    #     return tree

    @staticmethod
    def get_sourcetag():
        return " <span class='badge' style='background-color:#80d4ff'>SOURCE</span>"

    @staticmethod
    def get_targettag():
        return " <span class='badge' style='background-color:#99ff66'>TARGET</span>"

    @staticmethod
    def get_synctag():
        return " <span class='badge' style='background-color:#0066ff; color:white'>SYNC</span>"

    @staticmethod
    def get_checkmark():
        return " <span class='badge' style='background-color:#4dffa6'>&#10004;</span>"

    @staticmethod
    def get_completed_tag():
        return " <span class='badge' style='background-color:%B'> %C / %T COMPLETED</span>"

    @staticmethod
    def get_running_tag():
        return " <span class='badge' style='background-color:green; color:white'>%R RUNNING</span>"

    @staticmethod
    def get_queuing_tag():
        return " <span class='badge' style='background-color:pink'>%Q QUEUING</span>"

    @staticmethod
    def get_failed_tag():
        return " <span class='badge' style='background-color:red'>%F FAILED</span>"

    def update_job_logs(self, path_to_logs):
        """
        Updates job out and err logs of the job list
        """
        relevant_job_names = [
            job.name for job in self._job_list if job.status in [Status.COMPLETED, Status.FAILED]]
        file_names = [name for name in os.listdir(path_to_logs) if fnmatch(
            name, '*.out') or fnmatch(name, '*.err')]
        # err_names = []
        # file_names.sort()

        try:
            out_set = [name for name in file_names if name.split(
                '.')[-1] == 'out']
            out_set.sort()
            # for name in out_set:
            #     if name.find('a3jq_20141101_fc00_INI') >= 0:
            #         print(name)
            new_outs = {name.split('.')[0]: name for name in out_set}
        except:
            out_set = set()
            new_outs = dict()
        try:
            err_set = [name for name in file_names if name.split(
                '.')[-1] == 'err']
            err_set.sort()
            # for name in err_set:
            #     if name.find('a3jq_20141101_fc00_INI') >= 0:
            #         print(name)
            new_errs = {name.split('.')[0]: name for name in err_set}
        except:
            err_set = set()
            new_errs = dict()

        for job in self._job_list:
            if job.status in [Status.COMPLETED, Status.FAILED]:
                job.out = new_outs.get(job.name, 'NA')
                job.err = new_errs.get(job.name, 'NA')

        # print(new_outs['a3jq_20141101_fc00_INI'])
        # print(new_errs['a3jq_20141101_fc00_INI'])
        # print(file_names)

    @staticmethod
    def get_tree_structured_from_previous_run(expid, BasicConfig, run_id, chunk_unit=None, chunk_size=1):
        """
        Return the structured tree using data from a previous run
        """

        # Get data
        # print("Exp {} Run {}".format(expid, run_id))
        BasicConfig.read()
        job_data_structure = JobDataStructure(expid, BasicConfig)
        experiment_run = job_data_structure.get_experiment_run_by_id(run_id)
        if experiment_run:
            chunk_unit = experiment_run.chunk_unit
            chunk_size = experiment_run.chunk_size
        else:
            raise Exception("Autosubmit couldn't fin the experiment header information necessary to complete this request.")
        job_list = job_data_structure.get_current_job_data(
            run_id, all_states=True)
        if not job_list:
            return [], [], {}
        else:
            already_included = []
            job_list.sort(key=lambda x: x.counter)
            for job in job_list:
                original_job_name = job.job_name
                job.job_name = job.job_name + \
                    ("+" * len(filter(lambda x: x == job.job_name, already_included))
                     if job.job_name in already_included else "")
                already_included.append(original_job_name)

        # for job in job_list:
        #     print(job.job_name)
        # dateformat = self.get_date_format
        source = JobList.get_sourcetag()
        target = JobList.get_targettag()
        sync = JobList.get_synctag()
        check_mark = JobList.get_checkmark()
        # Identify chunks
        chunks = {int(job.chunk)
                  for job in job_list if job.chunk is not None and len(str(job.chunk)) > 0}
        date_list = {datetime.datetime.strptime(
            job.date, '%Y-%m-%d %H:%M:%S') for job in job_list if len(job.date) > 0}
        dateformat = ''
        for date in date_list:
            if date.hour > 1:
                dateformat = 'H'
            if date.minute > 1:
                dateformat = 'M'
        date_member_groups = {}
        result_header = {}
        result_exp = []
        result_exp_wrappers = []
        sync_jobs = []
        # members (sections in database)
        members = {job.section for job in job_list if len(job.section) > 0}
        # print(members)
        added_job_names = set()
        date_member_repetition = {}
        job_name_to_job_title = {}
        job_name_to_job = {job.job_name: job for job in job_list}
        year_per_sim = datechunk_to_year(chunk_unit, chunk_size)
        path_to_logs = os.path.join(
            BasicConfig.LOCAL_ROOT_DIR, expid, "tmp", "LOG_" + expid)

        packages = {job.rowtype for job in job_list if job.rowtype > 2}
        package_to_jobs = {package: [
            job.job_name for job in job_list if job.rowtype == package] for package in packages}

        # Dictionary package -> { job_name : ( queue_time, [], job.name, start_time ) }
        package_to_jobs_for_normalization = {package: {job.job_name: (job.queuing_time(
        ), [], job.job_name, job.start, job.finish) for job in job_list if job.rowtype == package} for package in packages}
        # For Job -> Package, use job.rowtype
        dates = {date: date2str(date, dateformat) for date in date_list}

        # print(len(job_list))
        # for job in job_list:
        #     print(job.section)
        #     print(job.date)

        # print(job_list[0].section)
        start_time = time()
        for key in dates:
            for member in members:
                # print(str(key) + " : " + str(member))
                current_list = date_member_repetition.get(
                    (key, member), [])
                # local_short_list = filter(
                #     lambda x: x.date == key and x.member == member, jobs)
                local_list = filter(lambda x: (
                    str(x.date) == str(key) and str(x.section) == str(member)) or x in current_list, job_list)
                print("Local list {} for {} - {}".format(len(local_list), key, member))
                date_member_groups[(key, member)] = sorted(
                    local_list, key=lambda x: x.chunk)
                added_job_names.update({job.job_name for job in local_list})
                # print(local_list[0].name)
                # jobs = [job for job in jobs if job not in local_short_list]
                # jobs.extend(date_member_repetition[(date,member)])
                # jobs -= local_list
        print("Spent in main: " + str(time() - start_time))

        # Printing date - member groups / date - chunk syncs
        # Working with date-member groups
        for date in dates.keys():
            date_member = list()
            all_suspended = True
            all_waiting = True
            all_completed = True
            total_jobs_startdate = 0
            for member in members:
                completed = 0
                queueing = 0
                running = 0
                failed = 0
                children_member = list()
                # already_included = []
                for job in date_member_groups[(date, member)]:
                    wrapped = ""
                    all_suspended = all_suspended and job.status == "SUSPENDED"
                    all_waiting = all_waiting and job.status == "WAITING"
                    all_completed = all_completed and job.status == "COMPLETED"
                    total_jobs_startdate += 1
                    # job.job_name in job_to_package.keys():
                    if job.rowtype > 2:
                        wrapped = " <span class='badge' style='background-color:#94b8b8'>Wrapped " + \
                            str(job.rowtype) + "</span>"
                    if job.status == "COMPLETED":
                        completed += 1
                    elif job.status == "RUNNING":
                        running += 1
                    elif job.status == "QUEUING":
                        queueing += 1
                    elif job.status == "FAILED":
                        failed += 1
                    current_title = job.title + \
                        ((" ~ " + str(job_times_to_text(job.queuing_time(),
                                                        job.running_time(), job.status))))
                    # if len(job._children) == 0:
                    #     current_title = current_title + target
                    # if len(job._parents) == 0:
                    #     current_title = current_title + source
                    if job.member == None:
                        current_title = current_title + sync
                        sync_jobs.append(job.job_name)
                    current_title = current_title + wrapped
                    # Individual Job
                    job_name_to_job_title[job.job_name] = current_title
                    # job.job_name = job.job_name + \
                    #     ("+" * len(filter(lambda x: x == job.job_name, already_included))
                    #      if job.job_name in already_included else "")
                    children_member.append({'title': current_title,
                                            'refKey': job.job_name,
                                            'data': 'Empty',
                                            'children': []})
                    # already_included.append(job.job_name)
                    job_name_to_job[job.job_name].tree_parent.append(
                        expid + "_" + str(dates[date]) + "_" + str(member))
                    # Delete included
                    # added_job_names.add(job.job_name)
                    # todo : this can be replaced with the functions of utils
                completed_tag = (" <span class='badge' style='background-color:yellow'>" if completed == len(
                    date_member_groups[(date, member)]) else " <span class='badge' style='background-color:#ffffb3'>") + \
                    str(completed) + " / " + \
                    str(len(
                        date_member_groups[(date, member)])) + " COMPLETED</span>"
                running_tag = " <span class='badge' style='background-color:green; color:white'>" + \
                    str(running) + " RUNNING</span>"
                queueing_tag = " <span class='badge' style='background-color:pink'>" + \
                    str(queueing) + " QUEUING</span>"
                failed_tag = " <span class='badge' style='background-color:red'>" + \
                    str(failed) + " FAILED</span>"
                # Date Member group
                date_member.append({'title': expid + "_" + str(dates[date]) + "_" + str(member) + completed_tag + (failed_tag if failed > 0 else '') + (running_tag if running > 0 else '') + (queueing_tag if queueing > 0 else ''),
                                    'folder': True,
                                    'refKey': expid + "_" + str(dates[date]) + "_" + str(member),
                                    'data': 'Empty',
                                    'expanded': False,
                                    'children': children_member})
                # Reference data
                result_header[expid + "_" + str(dates[date]) + "_" + str(member)] = ({'completed': completed,
                                                                                      'running': running,
                                                                                      'queuing': queueing,
                                                                                      'failed': failed,
                                                                                      'total': len(date_member_groups[(date, member)])})
            if len(date_member) > 0:
                # print(result_exp)
                if all_suspended or all_waiting or all_completed:
                   date_tag = JUtils.get_date_folder_tag("WAITING", total_jobs_startdate) if all_waiting else JUtils.get_date_folder_tag("SUSPENDED", total_jobs_startdate)
                   if all_completed:
                     date_tag = JUtils.get_date_folder_tag("COMPLETED", total_jobs_startdate)
                   date_folder_title = "{0}_{1}_{2}".format( expid, str(dates[date]), date_tag )
                else:
                   date_folder_title = expid + "_" + str(dates[date])

                result_exp.append({'title': date_folder_title,
                                   'folder': True,
                                   'refKey': expid + "_" + str(dates[date]),
                                   'data': 'Empty',
                                   'expanded':  False if len(dates) > 5 and (all_waiting or all_suspended or all_completed) else True,
                                   'children': date_member})

         # Printing date - chunk
        jobs = [job for job in job_list if job.job_name not in added_job_names]
        for date in dates:
            completed = 0
            queueing = 0
            running = 0
            failed = 0
            date_member = []
            local_list = filter(lambda x: x.date == date, jobs)
            if len(local_list) > 0:
                # already_included = []
                for job in local_list:
                    if job.status == "COMPLETED":
                        completed += 1
                    elif job.status == "RUNNING":
                        running += 1
                    elif job.status == "QUEUING":
                        queueing += 1
                    elif job.status == "FAILED":
                        failed += 1
                    current_title = job.title + \
                        ((" ~ " + str(job_times_to_text(job.queuing_time(),
                                                        job.running_time(), job.status))))
                    # print(current_title)
                    # if len(job._children) == 0:
                    #     current_title = current_title + target
                    # if len(job._parents) == 0:
                    #     current_title = current_title + source
                    # Individual Job
                    job_name_to_job_title[job.job_name] = current_title
                    # job.job_name = job.job_name + \
                    #     ("+" * len(filter(lambda x: x == job.job_name, already_included))
                    #      if job.job_name in already_included else "")
                    date_member.append({'title': current_title,
                                        'refKey': job.job_name,
                                        'data': 'Empty',
                                        'children': []})
                    # already_included.append(job.job_name)
                    job_name_to_job[job.job_name].tree_parent.append(
                        expid + "_" + str(dates[date]) + "_chunk")
                    # Delete Included
                    added_job_names.add(job.job_name)
                # jobs = [job for job in jobs if job not in local_list]
                completed_tag = (" <span class='badge' style='background-color:yellow'>" if completed == len(local_list) else " <span class='badge' style='background-color:#ffffb3'>") + \
                    str(completed) + " / " + \
                    str(len(local_list)) + " COMPLETED</span>"
                running_tag = " <span class='badge' style='background-color:green; color:white'>" + \
                    str(running) + " RUNNING</span>"
                queueing_tag = " <span class='badge' style='background-color:pink'>" + \
                    str(queueing) + " QUEUING</span>"
                failed_tag = " <span class='badge' style='background-color:red'>" + \
                    str(failed) + " FAILED</span>"
                # Date Chunk group

                result_exp.append({'title': expid + "_" + str(dates[date]) + "_chunk" + completed_tag + (failed_tag if failed > 0 else '') + (running_tag if running > 0 else '') + (queueing_tag if queueing > 0 else ''),
                                   'folder': True,
                                   'refKey': expid + "_" + str(dates[date]) + "_chunk",
                                   'data': 'Empty',
                                   'expanded': True,
                                   'children': date_member})

                # Reference data
                result_header[expid + "_" + str(dates[date]) + "_chunk"] = ({'completed': completed,
                                                                             'failed': failed,
                                                                             'running': running,
                                                                             'queuing': queueing,
                                                                             'total': len(local_list)})

        jobs = [job for job in job_list if job.job_name not in added_job_names]
        # print("Still in jobs")
        if len(jobs) > 0:
            floating_around = list()
            already_included = []
            for job in jobs:
                current_title = job.title + \
                    ((" ~ " + str(job_times_to_text(job.queuing_time(),
                                                    job.running_time(), job.status))))
                # if len(job._children) == 0:
                #     current_title = current_title + target
                # if len(job._parents) == 0:
                #     current_title = current_title + source
                job_name_to_job_title[job.job_name] = current_title
                job.job_name = job.job_name + \
                    ("+" * len(filter(lambda x: x == job.job_name, already_included))
                     if job.job_name in already_included else "")
                floating_around.append(
                    {'title': current_title,
                     'refKey': job.job_name,
                     'data': 'Empty', 'children': []})
                already_included.append(job.job_name)
                # if job.date not in dates.keys() and job.member not in members:
            result_exp.append({'title': 'Keys',
                               'folder': True,
                               'refKey': 'Keys',
                               'data': 'Empty',
                               'expanded': True,
                               'children': floating_around})

        # Retrieving packages
        if (package_to_jobs):
            for package in package_to_jobs:
                jobs_in_package = package_to_jobs[package]
                completed = 0
                queueing = 0
                running = 0
                failed = 0
                job_objects = sorted([job_name_to_job[name] for name in jobs_in_package if job_name_to_job.get(
                    name, None)], key=lambda x: x.chunk)
                # job_objects = sorted([job for k, job in job_name_to_job.items(
                # ) if k in jobs_in_package], key=lambda x: x.chunk)
                jobs_in_wrapper = []
                already_included = []
                for job in job_objects:
                    # if job_name in job_name_to_job.keys():
                    #     job = job_name_to_job[job_name]
                    # else:
                    #     continue
                    if job.status == "COMPLETED":
                        completed += 1
                    elif job.status == "RUNNING":
                        running += 1
                    elif job.status == "QUEUING":
                        queueing += 1
                    elif job.status == "FAILED":
                        failed += 1
                    current_title = job.title + \
                        ((" ~ " + str(job_times_to_text(job.queuing_time(package_to_jobs_for_normalization.get(job.rowtype, None)),
                                                        job.running_time(), job.status))))
                    # if len(job._children) == 0:
                    #     current_title = current_title + target
                    # if len(job._parents) == 0:
                    #     current_title = current_title + source
                    # Individual Job in wrapper
                    jobs_in_wrapper.append({'title': current_title,
                                            'refKey': job.job_name + ("+" * len(filter(lambda x: x == job.job_name, already_included)) if job.job_name in already_included else ""),
                                            'data': 'Empty',
                                            'children': []})
                    already_included.append(job.job_name)
                    job_name_to_job[job.job_name].tree_parent.append(
                        'Wrapper: ' + str(package))
                completed_tag = (" <span class='badge' style='background-color:yellow'>" if completed == len(jobs_in_package) else " <span class='badge' style='background-color:#ffffb3'>") + \
                    str(completed) + " / " + \
                    str(len(jobs_in_package)) + " COMPLETED</span>"
                running_tag = " <span class='badge' style='background-color:green; color:white'>" + \
                    str(running) + " RUNNING</span>"
                queueing_tag = " <span class='badge' style='background-color:pink'>" + \
                    str(queueing) + " QUEUING</span>"
                failed_tag = " <span class='badge' style='background-color:red'>" + \
                    str(failed) + " FAILED</span>"

                result_exp_wrappers.append({'title': 'Wrapper: ' + str(package) + completed_tag + (failed_tag if failed > 0 else '') + (running_tag if running > 0 else '') + (queueing_tag if queueing > 0 else '') + (check_mark if completed == len(jobs_in_package) else ''),
                                   'folder': True,
                                   'refKey': 'Wrapper: ' + str(package),
                                   'data': {'completed': completed, 'failed': failed, 'running': running, 'queuing': queueing, 'total': len(jobs_in_package)},
                                   'expanded': False,
                                   'children': jobs_in_wrapper})
                # Reference data
                result_header['Wrapper: ' + str(package)] = ({'completed': completed,
                                                              'running': running,
                                                              'queuing': queueing,
                                                              'failed': failed,
                                                              'total': len(jobs_in_package)})
        result_header['completed_tag'] = JobList.get_completed_tag()
        result_header['running_tag'] = JobList.get_running_tag()
        result_header['queuing_tag'] = JobList.get_queuing_tag()
        result_header['failed_tag'] = JobList.get_failed_tag()
        result_header['check_mark'] = check_mark
        result_header['packages'] = list(package_to_jobs.keys())
        result_header['chunk_unit'] = chunk_unit
        result_header['chunk_size'] = chunk_size
        nodes = list()

        # ASYPD : POST jobs in experiment
        post_jobs = [job for job in job_list if job.member ==
                     "POST" and job.status in {"COMPLETED", "RUNNING"}]
        average_post_time = 0
        if len(post_jobs) > 0:
            average_post_time = round(sum(job.queuing_time(package_to_jobs_for_normalization.get(
                job.rowtype, None)) for job in post_jobs) / len(post_jobs), 2)

        for job in job_list:
            wrapper_name = job.rowtype if job.rowtype > 2 else None

            out = os.path.join(
                path_to_logs, job.out) if job.out != "NA" else "NA"
            err = os.path.join(
                path_to_logs, job.err) if job.err != "NA" else "NA"
            ini_date, end_date = JobList.date_plus(datetime.datetime.strptime(
                job.date, '%Y-%m-%d %H:%M:%S'), chunk_unit, int(job.chunk), chunk_size) if job.date is not None and len(job.date) > 0 else (
                date2str(None, dateformat), "")
            nodes.append({'id': job.job_name,
                          'internal_id': job.job_name,
                          'label': job.job_name,
                          'status': job.status,
                          'status_code': Status.STRING_TO_CODE[job.status],
                          'platform_name': job.platform,
                          'chunk': job.chunk,
                          'member': job.section,
                          'sync': True if job.job_name in sync_jobs else False,
                          # job_name_to_job_title[job.job_name] if job.job_name in job_name_to_job_title.keys() else "",
                          'title': job_name_to_job_title.get(job.job_name, ""),
                          'date': ini_date,
                          'date_plus': end_date,
                          'SYPD': calculate_SYPD_perjob(chunk_unit, chunk_size, job.chunk, job.running_time() if job else 0, Status.STRING_TO_CODE[job.status]),
                          'ASYPD': calculate_ASYPD_perjob(chunk_unit, chunk_size, job.chunk, job.running_time() + job.queuing_time(package_to_jobs_for_normalization.get(job.rowtype, None)) if job else 0, average_post_time, Status.STRING_TO_CODE[job.status]),
                          'minutes_queue': job.queuing_time(package_to_jobs_for_normalization.get(job.rowtype, None)),
                          # job_running_to_min[job.job_name] if job.job_name in list(job_running_to_min.keys()) else -1,
                          'minutes': job.running_time(),
                          'submit': job.submit_datetime_str(),
                          'start': job.start_datetime_str(),
                          'finish': job.finish_datetime_str(),
                          'section': job.member,
                          'queue': job.qos,
                          'processors': job.ncpus,
                          'wallclock': job.wallclock,
                          'wrapper': wrapper_name,
                          'wrapper_code': wrapper_name,
                          'children': None,
                          'children_list': None,
                          'parents': None,
                          'out': out,
                          'err': err,
                          'tree_parents': job.tree_parent,
                          'parent_list': None,
                          'custom_directives': None,
                          'rm_id': job.job_id,
                          'status_color': Monitor.color_status(Status.STRING_TO_CODE[job.status])})

        # sort and add these sorted elements to the result list
        result_exp_wrappers.sort(key=lambda x: x["title"])

        # add root folder to enclose all the wrappers
        # If there is something inside the date-member group, we create it.
        if len(result_exp_wrappers) > 0:
             result_exp.append({
                 "title": "Wrappers",
                 "folder": True,
                 "refKey": "Wrappers_{0}".format(expid),
                 "data": "Empty",
                 "expanded": False,
                 "children": list(result_exp_wrappers)
             })

        return result_exp, nodes, result_header


    def get_tree_structured(self, BasicConfig, chunk_unit=None, chunk_size=1):
        """
        Return the structured tree
        """
        # print(self._chunk_list)
        source = JobList.get_sourcetag()
        target = JobList.get_targettag()
        sync = JobList.get_synctag()
        check_mark = JobList.get_checkmark()
        chunks = self._chunk_list
        # chunk_size = len(chunks) if chunks is not None else 0
        dates = {}
        job_name_to_job = {}
        job_running_to_runtext = {}
        job_running_to_min = {}
        dateformat = self.get_date_format
        members = set(self._member_list)
        jobs = [job for job in self._job_list]
        date_member_groups = {}
        date_member_repetition = {}
        job_name_to_job_title = {}
        sync_jobs = []
        result_exp = []
        result_exp_wrappers = []
        result_header = {}
        job_dictionary = {}
        year_per_sim = datechunk_to_year(chunk_unit, chunk_size)

        path_to_logs = os.path.join(
            BasicConfig.LOCAL_ROOT_DIR, self.expid, "tmp", "LOG_" + self.expid)
        # Test out err recovery
        print("Start update job logs.")
        time_0 = time()
        self.update_job_logs(path_to_logs)
        print("Update logs time {0}".format(time() - time_0))
        allJobs = self._job_list
        # path_local_root = BasicConfig.LOCAL_ROOT_DIR
        # db_file = os.path.join(path_local_root, "ecearth.db")
        # conn = DbRequests.create_connection(db_file)
        # job_times = DbRequests.get_times_detail_by_expid(conn, self.expid)

        # Try to get packages
        job_to_package = {}
        package_to_jobs = {}
        package_to_package_id = {}
        package_to_symbol = {}

        job_to_package, package_to_jobs, package_to_package_id, package_to_symbol = JobList.retrieve_packages(
            BasicConfig, self.expid, [job.name for job in allJobs])
        dates = {date: date2str(date, dateformat) for date in self._date_list}
        if len(dates) != len(set(dates)):
            raise Exception("Repeated dates found. Autosubmit API can't generate a representation for this configuration. Review your configuration files.")
        # for date in self._date_list:
        #     dates[date] = date2str(date, dateformat)
        # Retrieving times
        # print("Retrieving times collection...")
        # start_time_operation = time()
        job_name_to_job = {job.name: job for job in allJobs}
        # for job in allJobs:
        #     job_name_to_job[job.name] = job

        job_running_to_min, job_running_to_runtext, _ = JobList.get_job_times_collection(
            BasicConfig, allJobs, self.expid, job_to_package, package_to_jobs)

        # job_running_to_runtext[job.name] = running_text
        # print("Spent in times: " + str(time() - start_time_operation))

        # Pre-distributing those who have no member
        # start_time = time()
        added_job_names = set()
        # added_jobs = set()

        # Determine if some jobs with date but no member belong to a date-member group
        for date in dates:  # dates.keys():
            local_list = filter(lambda x: x.date ==
                                date and x.member == None, jobs)
            for job in local_list:
                # Perhaps I exaggerated in my search for optimization
                parents_members = {parent.member for parent in job._parents}
                children_members = {child.member for child in job._children}
                intersection_member_parent = members & parents_members
                intersection_member_children = members & children_members
                if len(intersection_member_parent) > 0 or len(intersection_member_children) > 0:
                    date_member_repetition.setdefault(
                        (date, intersection_member_parent.pop() if len(intersection_member_parent) > 0 else intersection_member_children.pop()), []).append(job)

        # jobs = [job for job in jobs if job.name not in added_job_names]
        # print("Spent in pre distribution: " + str(time() - start_time))
        # Main distribution of jobs into date-member groups
        # start_time = time()
        for key in dates:
            for member in members:
                # print(str(key) + " : " + str(member))
                current_list = date_member_repetition.get(
                    (key, member), [])
                # local_short_list = filter(
                #     lambda x: x.date == key and x.member == member, jobs)
                local_list = filter(lambda x: (
                    x.date == key and x.member == member) or x in current_list, jobs)
                date_member_groups[(key, member)] = sorted(
                    local_list, key=lambda x: x.chunk)
                added_job_names.update({job.name for job in local_list})
        # print("Spent in main: " + str(time() - start_time))
        # Printing date - member groups / date - chunk syncs
        # Working with date-member groups
        for date in dates.keys():
            date_member = list()
            all_suspended = True
            all_waiting = True
            all_completed = True
            total_jobs_startdate = 0
            for member in members:
                completed = 0
                queueing = 0
                running = 0
                failed = 0
                children_member = deque()
                date_member_list = date_member_groups.get((date, member), [])
                sections_in_date_member = {
                    job.section for job in date_member_list}
                # Section : List of jobs in section
                date_member_section = {section: [
                    job for job in date_member_list if job.section == section] for section in sections_in_date_member}
                # Section : Branch of date-member
                date_member_section_jobs = OrderedDict()
                section_open = set()
                # Job distribution
                for job in date_member_list:
                    wrapped = ""
                    # job.name in job_to_package.keys():
                    all_suspended = all_suspended and job.status == Status.SUSPENDED
                    all_waiting = all_waiting and job.status == Status.WAITING
                    all_completed = all_completed and job.status == Status.COMPLETED
                    total_jobs_startdate+=1
                    if job_to_package.get(job.name, None):
                        wrapped = " <span class='badge' style='background-color:#94b8b8'>Wrapped " + \
                            package_to_package_id[job_to_package[job.name]
                                                  ] + "</span>"
                    if job.status == Status.COMPLETED:
                        completed += 1
                    elif job.status == Status.RUNNING:
                        running += 1
                    elif job.status == Status.QUEUING:
                        queueing += 1
                    elif job.status == Status.FAILED:
                        failed += 1
                    current_title = job.title + \
                        ((" ~ " + job_running_to_runtext[job.name])
                         if job_running_to_runtext.get(job.name, None) and len(job_running_to_runtext[job.name]) > 0 else "")
                    if len(job._children) == 0:
                        current_title = current_title + target
                    if len(job._parents) == 0:
                        current_title = current_title + source
                    if job.member == None:
                        current_title = current_title + sync
                        sync_jobs.append(job.name)
                    current_title = current_title + wrapped
                    job_name_to_job_title[job.name] = current_title
                    if len(date_member_section.get(job.section, [])) > 1:
                        # Multiple job in Section
                        if job.status in (Status.COMPLETED, Status.WAITING, Status.READY):
                            date_member_section_jobs.setdefault(job.section, deque()).append({
                                'title': current_title,
                                'refKey': job.name,
                                'data': 'Empty',
                                'children': []
                            })
                        else:
                            date_member_section_jobs.setdefault(job.section, deque()).appendleft({
                                'title': current_title,
                                'refKey': job.name,
                                'data': 'Empty',
                                'children': []
                            })
                            section_open.add(job.section)
                    else:
                        # Unique job in Section
                        if job.status in (Status.COMPLETED, Status.WAITING, Status.READY):
                            children_member.append({'title': current_title,
                                                    'refKey': job.name,
                                                    'data': 'Empty',
                                                    'children': []})
                        else:
                            children_member.appendleft({'title': current_title,
                                                        'refKey': job.name,
                                                        'data': 'Empty',
                                                        'children': []})
                    job_name_to_job[job.name].tree_parent.append(
                        self._expid + "_" + str(dates[date]) + "_" + str(member))
                    # Delete included
                    # added_job_names.add(job.name)
                # If there are section folders, we add them to children member to the left
                reversed_date_member_section_jobs = OrderedDict(
                    reversed(date_member_section_jobs.items()))
                for section_folder in reversed_date_member_section_jobs:
                    children_member.appendleft({
                        'title': section_folder,
                        'folder': True,
                        'refKey': self._expid + "_" + str(dates[date]) + "_" + str(member) + "_" + str(section_folder),
                        'data': 'Empty',
                        'expanded': True if section_folder in section_open else False,
                        'children': list(reversed_date_member_section_jobs.get(section_folder, []))
                    })
                completed_tag = (" <span class='badge' style='background-color:yellow'>" if completed == len(
                    date_member_groups[(date, member)]) else " <span class='badge' style='background-color:#ffffb3'>") + \
                    str(completed) + " / " + \
                    str(len(
                        date_member_groups[(date, member)])) + " COMPLETED</span>"
                running_tag = " <span class='badge' style='background-color:green; color:white'>" + \
                    str(running) + " RUNNING</span>"
                queueing_tag = " <span class='badge' style='background-color:pink'>" + \
                    str(queueing) + " QUEUING</span>"
                failed_tag = " <span class='badge' style='background-color:red'>" + \
                    str(failed) + " FAILED</span>"
                # Date Member group
                date_member.append({'title': self._expid + "_" + str(dates[date]) + "_" + str(member) + completed_tag + (failed_tag if failed > 0 else '') + (running_tag if running > 0 else '') + (queueing_tag if queueing > 0 else '') + (check_mark if completed == len(date_member_groups[(date, member)]) else ''),
                                    'folder': True,
                                    'refKey': self._expid + "_" + str(dates[date]) + "_" + str(member),
                                    'data': 'Empty',
                                    'expanded': False,
                                    'children': list(children_member)})
                # Reference data
                result_header[self._expid + "_" + str(dates[date]) + "_" + str(member)] = ({'completed': completed,
                                                                                            'running': running,
                                                                                            'queuing': queueing,
                                                                                            'failed': failed,
                                                                                            'held': 0,
                                                                                            'total': len(date_member_groups[(date, member)])})
            if len(date_member) > 0:
                if all_suspended or all_waiting or all_completed:
                    date_tag = JUtils.get_date_folder_tag("WAITING", total_jobs_startdate) if all_waiting else JUtils.get_date_folder_tag("SUSPENDED", total_jobs_startdate)
                    if all_completed:
                        date_tag = JUtils.get_date_folder_tag("COMPLETED", total_jobs_startdate)
                    date_folder_title = "{0}_{1}_{2}".format(self._expid, str(dates[date]), date_tag)
                else:
                    date_folder_title = self._expid + "_" + str(dates[date])

                result_exp.append({'title': date_folder_title,
                                   'folder': True,
                                   'refKey': self._expid + "_" + str(dates[date]),
                                   'data': 'Empty',
                                   'expanded': False if len(dates) > 5 and (all_waiting or all_suspended or all_completed) else True,
                                   'children': date_member})

        # Printing date - chunk
        jobs = [job for job in jobs if job.name not in added_job_names]
        for date in dates:
            completed = 0
            queueing = 0
            running = 0
            failed = 0
            date_member = []
            local_list = filter(lambda x: x.date == date, jobs)
            if len(local_list) > 0:
                for job in local_list:
                    if job.status == Status.COMPLETED:
                        completed += 1
                    elif job.status == Status.RUNNING:
                        running += 1
                    elif job.status == Status.QUEUING:
                        queueing += 1
                    elif job.status == Status.FAILED:
                        failed += 1
                    current_title = job.title + \
                        ((" ~ " + job_running_to_runtext[job.name])
                         if job_running_to_runtext.get(job.name, None) and len(job_running_to_runtext[job.name]) > 0 else "")
                    # print(current_title)
                    if len(job._children) == 0:
                        current_title = current_title + target
                    if len(job._parents) == 0:
                        current_title = current_title + source
                    # Individual Job
                    job_name_to_job_title[job.name] = current_title
                    date_member.append({'title': current_title,
                                        'refKey': job.name,
                                        'data': 'Empty',
                                        'children': []})
                    job_name_to_job[job.name].tree_parent.append(
                        self._expid + "_" + str(dates[date]) + "_chunk")
                    # Delete Included
                    added_job_names.add(job.name)
                # jobs = [job for job in jobs if job not in local_list]
                completed_tag = (" <span class='badge' style='background-color:yellow'>" if completed == len(local_list) else " <span class='badge' style='background-color:#ffffb3'>") + \
                    str(completed) + " / " + \
                    str(len(local_list)) + " COMPLETED</span>"
                running_tag = " <span class='badge' style='background-color:green; color:white'>" + \
                    str(running) + " RUNNING</span>"
                queueing_tag = " <span class='badge' style='background-color:pink'>" + \
                    str(queueing) + " QUEUING</span>"
                failed_tag = " <span class='badge' style='background-color:red'>" + \
                    str(failed) + " FAILED</span>"
                # Date Chunk group

                result_exp.append({'title': self._expid + "_" + str(dates[date]) + "_chunk" + completed_tag + (failed_tag if failed > 0 else '') + (running_tag if running > 0 else '') + (queueing_tag if queueing > 0 else '') + (check_mark if completed == len(local_list) else ''),
                                   'folder': True,
                                   'refKey': self._expid + "_" + str(dates[date]) + "_chunk",
                                   'data': 'Empty',
                                   'expanded': True,
                                   'children': date_member})

                # Reference data
                result_header[self._expid + "_" + str(dates[date]) + "_chunk"] = ({'completed': completed,
                                                                                   'failed': failed,
                                                                                   'running': running,
                                                                                   'queuing': queueing,
                                                                                   'held': 0,
                                                                                   'total': len(local_list)})

        jobs = [job for job in jobs if job.name not in added_job_names]
        # print("Still in jobs")
        if len(jobs) > 0:
            floating_around = list()
            for job in jobs:
                current_title = job.title + \
                    ((" ~ " + job_running_to_runtext[job.name])
                     if job_running_to_runtext.get(job.name, None) and len(job_running_to_runtext[job.name]) > 0 else "")
                if len(job._children) == 0:
                    current_title = current_title + target
                if len(job._parents) == 0:
                    current_title = current_title + source
                job_name_to_job_title[job.name] = current_title
                floating_around.append(
                    {'title': current_title, 'refKey': job.name, 'data': 'Empty', 'children': []})
                # if job.date not in dates.keys() and job.member not in members:
            result_exp.append({'title': 'Keys',
                               'folder': True,
                               'refKey': 'Keys',
                               'data': 'Empty',
                               'expanded': True,
                               'children': floating_around})

        # Retrieving packages
        if (package_to_jobs):
            for package in package_to_jobs:
                jobs_in_package = package_to_jobs[package]
                completed = 0
                queueing = 0
                running = 0
                failed = 0
                job_objects = sorted([job_name_to_job[name] for name in jobs_in_package if job_name_to_job.get(
                    name, None)], key=lambda x: x.chunk)
                # job_objects = sorted([job for k, job in job_name_to_job.items(
                # ) if k in jobs_in_package], key=lambda x: x.chunk)
                jobs_in_wrapper = []
                for job in job_objects:
                    # if job_name in job_name_to_job.keys():
                    #     job = job_name_to_job[job_name]
                    # else:
                    #     continue
                    if job.status == Status.COMPLETED:
                        completed += 1
                    elif job.status == Status.RUNNING:
                        running += 1
                    elif job.status == Status.QUEUING:
                        queueing += 1
                    elif job.status == Status.FAILED:
                        failed += 1
                    current_title = job.title + \
                        ((" ~ " + job_running_to_runtext[job.name])
                         if job_running_to_runtext.get(job.name, None) and len(job_running_to_runtext[job.name]) > 0 else "")
                    if len(job._children) == 0:
                        current_title = current_title + target
                    if len(job._parents) == 0:
                        current_title = current_title + source
                    # Individual Job in wrapper
                    jobs_in_wrapper.append({'title': current_title,
                                            'refKey': job.name,
                                            'data': 'Empty',
                                            'children': []})
                    job_name_to_job[job.name].tree_parent.append(
                        'Wrapper: ' + str(package))
                completed_tag = (" <span class='badge' style='background-color:yellow'>" if completed == len(jobs_in_package) else " <span class='badge' style='background-color:#ffffb3'>") + \
                    str(completed) + " / " + \
                    str(len(jobs_in_package)) + " COMPLETED</span>"
                running_tag = " <span class='badge' style='background-color:green; color:white'>" + \
                    str(running) + " RUNNING</span>"
                queueing_tag = " <span class='badge' style='background-color:pink'>" + \
                    str(queueing) + " QUEUING</span>"
                failed_tag = " <span class='badge' style='background-color:red'>" + \
                    str(failed) + " FAILED</span>"
                # Wrapper group
                result_exp_wrappers.append({'title': 'Wrapper: ' + str(package) + completed_tag + (failed_tag if failed > 0 else '') + (running_tag if running > 0 else '') + (queueing_tag if queueing > 0 else '') + (check_mark if completed == len(jobs_in_package) else ''),
                                   'folder': True,
                                   'refKey': 'Wrapper: ' + str(package),
                                   'data': {'completed': completed, 'failed': failed, 'running': running, 'queuing': queueing, 'total': len(jobs_in_package)},
                                   'expanded': False,
                                   'children': jobs_in_wrapper})
                # Reference data
                result_header['Wrapper: ' + str(package)] = ({'completed': completed,
                                                              'running': running,
                                                              'queuing': queueing,
                                                              'failed': failed,
                                                              'held': 0,
                                                              'total': len(jobs_in_package)})
        result_header['completed_tag'] = JobList.get_completed_tag()
        result_header['running_tag'] = JobList.get_running_tag()
        result_header['queuing_tag'] = JobList.get_queuing_tag()
        result_header['failed_tag'] = JobList.get_failed_tag()
        result_header['check_mark'] = check_mark
        result_header['packages'] = list(package_to_jobs.keys())
        result_header['chunk_unit'] = chunk_unit
        result_header['chunk_size'] = chunk_size
        nodes = list()

        # ASYPD : POST jobs in experiment
        post_jobs = [job for job in allJobs if job.section ==
                     "POST" and job.status in {Status.COMPLETED, Status.RUNNING}]
        average_post_time = 0
        if len(post_jobs) > 0:
            average_post_time = round(sum(job_running_to_min[job.name].queue_time + job_running_to_min[job.name]
                                          .run_time for job in post_jobs if job_running_to_min.get(job.name, None) is not None) / len(post_jobs), 2)

        for job in allJobs:
            wrapper_name = job_to_package.get(
                job.name, None)  # if job.name in job_to_package.keys(
            # ) else None
            wrapper_code = wrapper_name.split(
                '_')[2] if wrapper_name else None
            if wrapper_code and self._wrapper_queue:
                job.queue = self._wrapper_queue
            # print("{0} {1}".format(job.name, job.queue))
            # min_q, min_r, _status, energy = job_running_to_min[job.name] if job.name in list(
            #     job_running_to_min.keys()) else (-1, -1, "UNKNOWN", 0)

            job_info = job_running_to_min.get(
                job.name, None)  # if job.name in job_running_to_min.keys(
            # ) else None
            # min_q = job_info.queue_time if job_info else 0
            # min_r = job_info.run_time if job_info else 0
            # _status = job_info.status if job_info else status_text
            # energy = job_info.energy if job_info else 0
            # Calculating ASYPD

            out = os.path.join(
                path_to_logs, job.out) if job.out != "NA" else None
            err = os.path.join(
                path_to_logs, job.err) if job.err != "NA" else None
            ini_date, end_date = JobList.date_plus(job.date, chunk_unit, job.chunk, chunk_size) if job.date is not None else (
                date2str(job.date, self.get_date_format), "")
            nodes.append({'id': job.name,
                          'internal_id': job.name,
                          'label': job.name,
                          'status': str(Status.VALUE_TO_KEY[job.status]),
                          'status_code': job.status,
                          'platform_name': job.platform_name,
                          'chunk': job.chunk,
                          'member': job.member,
                          'sync': True if job.name in sync_jobs else False,
                          # job_name_to_job_title[job.name] if job.name in job_name_to_job_title.keys() else "",
                          'title': job_name_to_job_title.get(job.name, ""),
                          'date': ini_date,
                          'date_plus': end_date,
                          'SYPD': calculate_SYPD_perjob(chunk_unit, chunk_size, job.chunk, job_info.run_time if job_info else 0, Status.VALUE_TO_KEY[job.status]),
                          'ASYPD': calculate_ASYPD_perjob(chunk_unit, chunk_size, job.chunk, job_info.run_time + job_info.queue_time if job_info else 0, average_post_time, Status.VALUE_TO_KEY[job.status]),
                          'minutes_queue': job_info.queue_time if job_info else 0,
                          # job_running_to_min[job.name] if job.name in list(job_running_to_min.keys()) else -1,
                          'minutes': job_info.run_time if job_info else 0,
                          'submit': timestamp_to_datetime_format(job_info.submit) if job_info else None,
                          'start': timestamp_to_datetime_format(job_info.start) if job_info else None,
                          'finish': timestamp_to_datetime_format(job_info.finish) if job_info else None,
                          'section': job.section,
                          'queue': job.queue,
                          'processors': job.processors,
                          'wallclock': job.wallclock,
                          'wrapper': wrapper_name,
                          'wrapper_code': wrapper_code,
                          'children': len(job._children),
                          'children_list': [job_search.name for job_search in job._children],
                          'parents': len(job._parents),
                          'out': out,
                          'err': err,
                          'tree_parents': job.tree_parent,
                          'parent_list': [job_search.name for job_search in job._parents],
                          'custom_directives': job.custom_directives,
                          'rm_id': job.id if job.id and job.id > 0 else None,
                          'status_color': Monitor.color_status(job.status)})

        # sort and add these sorted elements to the result list
        result_exp_wrappers.sort(key=lambda x: x["title"])

        # add root folder to enclose all the wrappers
        # If there is something inside the date-member group, we create it.
        if len(result_exp_wrappers) > 0:
             result_exp.append({
                 "title": "Wrappers",
                 "folder": True,
                 "refKey": "Wrappers_{0}".format(self._expid),
                 "data": "Empty",
                 "expanded": False,
                 "children": list(result_exp_wrappers)
             })

        return result_exp, nodes, result_header

    @staticmethod
    def date_plus(date, chunk_unit, chunk, chunk_size=1):
        previous_date = date
        if chunk is not None and chunk_unit is not None:
            # print(str(chunk) + " " + str(chunk_unit) + " " + str(chunk_size))
            chunk_previous = (chunk - 1) * (chunk_size)
            chunk = chunk * chunk_size
            # print("Previous " + str(chunk_previous))
            if (chunk_unit == "month"):
                date = date + relativedelta(months=+chunk)
                previous_date = previous_date + \
                    relativedelta(months=+chunk_previous)
            elif (chunk_unit == "year"):
                date = date + relativedelta(years=+chunk)
                previous_date = previous_date + \
                    relativedelta(years=+chunk_previous)
            elif (chunk_unit == "day"):
                date = date + datetime.timedelta(days=+chunk)
                previous_date = previous_date + \
                    datetime.timedelta(days=+chunk_previous)
            elif (chunk_unit == "hour"):
                date = date + datetime.timedelta(days=+int(chunk / 24))
                previous_date = previous_date + \
                    datetime.timedelta(days=+int(chunk_previous / 24))
        # date_str = date2str(date)
        # previous_date_str = date2str(previous_date)
        return JobList.date_to_str_space(date2str(previous_date)), JobList.date_to_str_space(date2str(date))

    @staticmethod
    def date_to_str_space(date_str):
        if (len(date_str) == 8):
            return str(date_str[0:4] + " " + date_str[4:6] + " " + date_str[6:])
        else:
            return ""

    def get_graph_representation(self, BasicConfig, layout='standard', grouped='none', chunk_unit=None, chunk_size=1):
        """
        Return graph representation in JSON format.\n
        :param layout: established the type of layour to generate: 'standard', 'laplacian'.  
        :type layout: string  
        :param grouped: type of grouping to be applied: 'date-member', 'status'.  
        :type grouped: string  
        :return: list of edges, list of nodes  
        :rtype: JSON format  
        """
        dateformat = self.get_date_format
        node_id = dict()
        nodes = list()
        edges = list()
        raw_edges = list()
        fake_edges = list()
        id_counter = 1
        dates = dict()
        list_groups = dict()
        # year_per_sim = datechunk_to_year(chunk_unit, chunk_size)
        # Building dictionary date original -> date formatted
        if len(self._date_list) != len(set(self._date_list)):
            raise Exception("Repeated dates found. Autosubmit API can't generate a representation for this configuration. Review your configuration files.")

        for date in self._date_list:
            dates[date] = date2str(date, dateformat)

        orderedJobs = list()

        path_to_logs = os.path.join(
            BasicConfig.LOCAL_ROOT_DIR, self.expid, "tmp", "LOG_" + self.expid)
        # Test out err recovery
        self.update_job_logs(path_to_logs)

        # Update Level
        allJobs = self.get_all()
        # Validate if the graph data should be updated
        graph_drawing_data = ExperimentGraphDrawing(self.expid).get_validated_data(self.get_all())
        if not graph_drawing_data or len(allJobs) > 1000:
            # print('Start Traverse Update.')
            start_time = time()
            allJobs = self.job_list_traverse_update()
            if allJobs == None:
                raise Exception(
                    "The system cannot generate a graph representation of this experiment.")
            # print('Traverse Update Ended. Seconds spent: ' +
            #       str(time() - start_time))
        else:
            if graph_drawing_data:
                print("Valid Graph Drawing detected.")
            else:
                print(
                    "Too many jobs for drawing calculation. Using quick and ugly heuristic instead.")

        monitor = Monitor()
        packages = None

        chunk_list = self._chunk_list
        # chunk_size = len(chunk_list) if chunk_list is not None else 0
        list_packages = set()
        # Packages
        job_to_package = dict()
        package_to_symbol = dict()
        package_to_group_number = dict()
        package_to_jobs = dict()

        job_name_to_job = dict()
        mainCoordinates = dict()
        package_level_job = dict()
        job_running_to_min = dict()
        job_running_to_runtext = dict()
        i_am_true_coordinates = False
        maxChildren = 0
        maxParent = 0
        total_jobs = len(allJobs)
        # job_info_from_pkl = self.get_list_from_pkl(BasicConfig, self.expid)

        job_to_package, package_to_jobs, package_to_package_id, package_to_symbol = JobList.retrieve_packages(
            BasicConfig, self.expid, [job.name for job in allJobs])

        group = 1
        for package in package_to_symbol.keys():
            package_to_group_number[package] = group
            group += 1

        # Retrieving minutes
        start_time_operation = time()
        for job in allJobs:
            job_name_to_job[job.name] = job
            node_id[job.name] = job.name

        job_running_to_min, job_running_to_runtext, _ = JobList.get_job_times_collection(
            BasicConfig, allJobs, self.expid, job_to_package, package_to_jobs)
        print("Spent in times: " + str(time() - start_time_operation))

        # Adding edges
        for job in allJobs:
            num_children = len(job._children)
            num_parent = len(job._parents)
            if num_children > maxChildren:
                maxChildren = num_children
            if num_parent > maxParent:
                maxParent = num_parent
            if job._children > 0:
                # current_group = job_to_package.get(job.name, None) # job_to_package[job.name] if job.name in job_to_package else None
                for child in job._children:
                    if ((node_id[job.name], node_id[child.name]) not in raw_edges):
                        edge_id = node_id[job.name] + "-" + node_id[child.name]
                        if job.name in job_to_package and child.name in job_to_package and job_to_package[job.name] == job_to_package[child.name]:
                            edges.append(
                                {'id': edge_id, 'from': node_id[job.name], 'to': node_id[child.name], 'is_wrapper': True, 'dashed': False})
                        else:
                            edges.append(
                                {'id': edge_id, 'from': node_id[job.name], 'to': node_id[child.name], 'is_wrapper': False, 'dashed': False})
                        raw_edges.append(
                            (node_id[job.name], node_id[child.name]))

        # Building horizontal fake edges
        for package in package_to_jobs:
            for job_name in package_to_jobs[package]:
                if job_name in job_name_to_job:
                    job = job_name_to_job[job_name]
                    if str(package) + '_' + str(job.level) not in package_level_job:
                        package_level_job[str(package) +
                                          '_' + str(job.level)] = list()
                    package_level_job[str(package) + '_' +
                                      str(job.level)].append(job)

        for package_level in package_level_job:
            special_list = package_level_job[package_level]
            if len(special_list) > 1:
                current = None
                for i in range(len(special_list)):
                    current = special_list[i]
                    if i < len(special_list) - 1:
                        if (node_id[current.name], node_id[special_list[i + 1].name]) not in raw_edges:
                            fake_edges.append({'id': node_id[current.name] + '-' + node_id[special_list[i + 1].name],
                                               'from': node_id[current.name], 'to': node_id[special_list[i + 1].name], 'is_wrapper': True, 'dashed': True})
                            raw_edges.append(
                                (node_id[current.name], node_id[special_list[i + 1].name]))

        # Main condition
        if (graph_drawing_data or len(allJobs) <= 1000) and (layout == 'standard'):
            if graph_drawing_data:
                print("Using existing GraphViz positioning.")
                i_am_true_coordinates = True
                mainCoordinates = graph_drawing_data
            else:
                print("Calculating Drawing Independently")
                mainCoordinates = ExperimentGraphDrawing(
                    self.expid).calculate_drawing(allJobs, independent=True, num_chunks=len(chunk_list))
                if not mainCoordinates:
                    mainCoordinates = dict()
                    graph = monitor.create_tree_list(
                        self.expid, allJobs, None, dict(), False)
                    result = graph.create('dot', format="plain")
                    for u in result.split("\n"):
                        splitList = u.split(" ")
                        if len(splitList) > 1 and splitList[0] == "node":
                            mainCoordinates[splitList[1]] = (
                                float(splitList[2]) * 90, float(splitList[3]) * -90)

            # print("Seconds spent in GraphViz: " + str(time() - start_time))
        elif (layout == 'standard' or layout == 'hierarchical'):
            # Given order
            print("Barycentric Started")
            start_time = time()
            # Testing Barycentric
            max_level = max([job.level for job in allJobs])
            print("Levels " + str(max_level))
            # min_level = min([job.level for job in allJobs])
            # Assuming level starts at 1
            for i in range(2, max_level + 1):

                # Order for first layer
                if i == 2:
                    jobs_layer_previous = filter(
                        lambda x: x.level == i - 1, allJobs)
                    k = 1
                    for job_prev in jobs_layer_previous:
                        job_prev.h_order = k
                        k = k + 1

                jobs_layer = filter(lambda x: x.level == i, allJobs)
                # print("Level " + str(i) + " ~ " + str(len(jobs_layer)))

                for job in jobs_layer:
                    sum_order = 0
                    for parent in job._parents:
                        sum_order += parent.h_order
                    neighbor_count = len(job._parents)
                    bary_value = 0
                    if neighbor_count > 0:
                        bary_value = sum_order / neighbor_count
                    job.barycentric_value = bary_value

                jobs_layer.sort(key=lambda x: x.barycentric_value)
                already_assigned_order = list()

                for j in range(1, len(jobs_layer) + 1):
                    if jobs_layer[j - 1].name not in already_assigned_order:
                        already_assigned_order.append(jobs_layer[j - 1].name)
                        jobs_layer[j -
                                   1].h_order = len(already_assigned_order) + 1
                        if jobs_layer[j - 1].name in job_to_package.keys():
                            jobs_in_wrapper = package_to_jobs[job_to_package[jobs_layer[j - 1].name]]
                            # jobs_in_wrapper.sort(key=lambda x: x.barycentric_value)
                            jobs_obj_in_wrapper = filter(
                                lambda x: x.name in jobs_in_wrapper, allJobs)
                            jobs_obj_in_wrapper.sort(
                                key=lambda x: x.barycentric_value)
                            subcount = len(already_assigned_order) + 2
                            for job_o_w in jobs_obj_in_wrapper:
                                job_names_in_layer = [
                                    job.name for job in jobs_layer]
                                if job_o_w.name in job_names_in_layer and job_o_w.name not in already_assigned_order:
                                    already_assigned_order.append(job_o_w.name)
                                    job_o_w.h_order = subcount
                                    subcount = subcount + 1

                # print("Level " + str(i))

            for job in allJobs:
                resize_y = 150
                resize_x = 185
                mainCoordinates[job.name] = (
                    job.h_order * resize_x, job.level * resize_y)
                # print(job.name + ": " + str(job.h_order) + ", x: " + str(job.h_order * resize) + ", y: " + str(job.level * resize) + " ~ baryval " + str(job.barycentric_value))
            print("Seconds spent in Barycentric: " + str(time() - start_time))
        elif (layout == 'standard' or layout == 'laplacian'):
            # Spectral Drawing of coordinates
            print("Start Construction Laplacian")
            start_time_operation = time()
            G = nx.Graph()
            total_nodes = len(allJobs)
            for job in allJobs:
                G.add_node(job.name)
            for edge in edges:
                G.add_edge(edge['from'], edge['to'], weight=(
                    1 if edge['is_wrapper'] == False else 3))
            for edge in fake_edges:
                G.add_edge(edge['from'], edge['to'], weight=3)
            lap_matrix = nx.normalized_laplacian_matrix(G)
            print("Finished Normalized Laplacian")
            eigval, eigvec = sparse.linalg.eigsh(lap_matrix, k=4, which="SM")
            eigval1 = float(eigval[1])
            eigval2 = float(eigval[2])
            x_coords = eigvec[:, 1] * (total_nodes / (eigval1)) * 10
            y_coords = eigvec[:, 2] * (total_nodes / (eigval2)) * 10

            for i in range(len(x_coords)):
                mainCoordinates[allJobs[i].name] = (x_coords[i], y_coords[i])
            print("Seconds Spent in Laplacian: " +
                  str(time() - start_time_operation))

        # ASYPD : POST jobs in experiment
        post_jobs = [job for job in allJobs if job.section ==
                     "POST" and job.status in {Status.COMPLETED, Status.RUNNING}]
        average_post_time = 0
        if len(post_jobs) > 0:
            average_post_time = round(sum(job_running_to_min[job.name].queue_time + job_running_to_min[job.name]
                                          .run_time for job in post_jobs if job_running_to_min.get(job.name, None) is not None) / len(post_jobs), 2)

        for job in allJobs:
            if (len(mainCoordinates.keys())) > 0:
                x, y = mainCoordinates[job.name]
            else:
                x, y = 0, 0
            package_name = job_to_package.get(
                job.name, None) if job_to_package else None
            # Wrapper Queue if exists
            if package_name and self._wrapper_queue:
                # print(self._wrapper_queue)
                job.queue = self._wrapper_queue
            # print("{0} {1}".format(job.name, job.queue))

            out = os.path.join(
                path_to_logs, job.out) if job.out != "NA" else None
            err = os.path.join(
                path_to_logs, job.err) if job.err != "NA" else None
            # min_q, min_r, status_retrieved, energy = job_running_to_min[job.name] if job.name in list(
            #     job_running_to_min.keys()) else (-1, -1, "UNKNOWN", 0)
            job_info = job_running_to_min[job.name] if job.name in job_running_to_min.keys(
            ) else None
            ini_date, end_date = JobList.date_plus(job.date, chunk_unit, job.chunk, chunk_size) if job.date is not None else (
                date2str(job.date, self.get_date_format), "")
            nodes.append({'id': job.name,
                          'internal_id': job.name,
                          'label': job.name,
                          'status': str(Status.VALUE_TO_KEY[job.status]),
                          'status_code': job.status,
                          'platform_name': job.platform_name,
                          'chunk': job.chunk,
                          'package': package_name,
                          'SYPD': calculate_SYPD_perjob(chunk_unit, chunk_size, job.chunk, job_info.run_time if job_info else 0, Status.VALUE_TO_KEY[job.status]),
                          'ASYPD': calculate_ASYPD_perjob(chunk_unit, chunk_size, job.chunk, job_info.run_time + job_info.queue_time if job_info else 0, average_post_time, Status.VALUE_TO_KEY[job.status]),
                          'member': job.member,
                          'date': ini_date,
                          'date_plus': end_date,
                          'section': job.section,
                          'queue': job.queue,
                          'level': job.level,
                          'dashed': True if job.name in job_to_package.keys() else False,
                          'shape': package_to_symbol[job_to_package[job.name]] if job.name in job_to_package else 'dot',
                          'processors': job.processors,
                          'wallclock': job.wallclock,
                          'children': len(job._children),
                          'children_list': [job_search.name for job_search in job._children],
                          'parents': len(job._parents),
                          'parent_list': [job_search.name for job_search in job._parents],
                          'custom_directives': job.custom_directives,
                          'status_color': Monitor.color_status(job.status),
                          'err': err,
                          'out': out,
                          'rm_id': job.id if job.id and job.id > 0 else None,
                          'minutes_queue': job_info.queue_time if job_info else 0,
                          'minutes': job_info.run_time if job_info else 0,
                          'submit': timestamp_to_datetime_format(job_info.submit) if job_info else None,
                          'start': timestamp_to_datetime_format(job_info.start) if job_info else None,
                          'finish': timestamp_to_datetime_format(job_info.finish) if job_info else None,
                          'x': x,
                          'y': y})
            id_counter += 1
        # print("Grouped : {}".format(grouped))
        # Building groups by grouped type provided
        if grouped == "date-member" and (len(dates) > 1 or len(self._member_list) > 1):
            colors = {}
            for date in dates:
                for member in self._member_list:
                    completed_members = 0
                    failed_members = 0
                    waiting_members = 0
                    other_members = 0
                    running_members = 0
                    suspended_members = 0
                    queueing_members = 0
                    submitted_members = 0
                    final_color = Monitor.color_status(Status.WAITING)
                    group_name = self._expid + "_" + \
                        str(dates[date]) + "_" + member + "_"
                    local_list = filter(
                        lambda x: x.name.startswith(group_name), allJobs)
                    # if group_name not in list(list_groups.keys()):
                    #     list_groups[group_name] = list()
                    # list_groups.setdefault(group_name, [])
                    for job in local_list:
                        if job.status == Status.COMPLETED:
                            completed_members += 1
                        elif job.status == Status.FAILED:
                            failed_members += 1
                        elif job.status == Status.WAITING:
                            waiting_members += 1
                        elif job.status == Status.RUNNING:
                            running_members += 1
                        elif job.status == Status.SUSPENDED:
                            suspended_members += 1
                        elif job.status == Status.QUEUING:
                            queueing_members += 1
                        elif job.status == Status.SUBMITTED:
                            submitted_members += 1
                        else:
                            other_members += 1

                    if completed_members > 0 and failed_members == 0:
                        final_color = Monitor.color_status(Status.COMPLETED)
                    if queueing_members > 0 and failed_members == 0:
                        final_color = Monitor.color_status(Status.QUEUING)
                    if submitted_members > 0 and failed_members == 0:
                        final_color = Monitor.color_status(Status.SUBMITTED)
                    if suspended_members > 0 and failed_members == 0:
                        final_color = Monitor.color_status(Status.SUSPENDED)
                    if running_members > 0 and failed_members == 0:
                        final_color = Monitor.color_status(Status.RUNNING)
                    if failed_members > 0:
                        final_color = Monitor.color_status(Status.FAILED)

                    colors[group_name] = final_color

            groups_data = []
            for group in colors:
                x_bound = list()
                y_bound = list()
                # print("Group: {}".format(group))
                for node in nodes:
                    if str(node['label']).startswith(group):
                        # print("{} -> {}".format(node['label'], group))
                        x_bound.append(node['x'])
                        y_bound.append(node['y'])
                y_coordinate = sum(y_bound) / \
                    len(y_bound) if len(y_bound) > 0 else 0
                x_coordinate = min(x_bound) if len(x_bound) > 0 else 0
                groups_data.append((group, x_coordinate, y_coordinate))
             # Sort by y
            groups_data.sort(key=lambda a: a[2], reverse=True)
            visited = set()
            for item in groups_data:
                name, x, y = item
                # print("{} -> x: {}, y: {}".format(name, x, y))
                visited.add(name)
                for jtem in groups_data:
                    namej, xj, yj = jtem
                    if namej not in name:
                        if abs(x - xj) <= 250 and abs(y - yj) <= 250:
                            # print("Collision {} {}".format(name, namej))
                            if y > yj:
                                y = y + (250 - abs(y - yj))
                            else:
                                y = y - (250 - abs(y - yj))
                list_groups[name] = {"color": colors[name], "x": x, "y": y}
        elif grouped == "date-member-chunk" and (len(self._chunk_list) > 1 or len(self._member_list) > 1):
            # This kills the vis-network graph
            try:
                colors = {}
                for date in dates:
                    for member in self._member_list:
                        for chunk in self._chunk_list:
                            group_name = self._expid + "_" + \
                                str(dates[date]) + "_" + \
                                member + "_" + str(chunk) + "_"
                            # print("Group Name: {}".format(group_name))
                            specific_list = filter(
                                lambda x: x.name.startswith(group_name), allJobs)
                            if len(specific_list) > 0:
                                failed_count = sum(
                                    1 for x in specific_list if x.status == Status.FAILED)
                                group_color = Monitor.color_status(
                                    Status.WAITING)
                                if failed_count > 0:
                                    group_color = Monitor.color_status(
                                        Status.FAILED)
                                else:
                                    running_count = sum(
                                        1 for x in specific_list if x.status == Status.RUNNING)
                                    if running_count > 0:
                                        group_color = Monitor.color_status(
                                            Status.RUNNING)
                                    else:
                                        queuing_count = sum(
                                            1 for x in specific_list if x.status == Status.QUEUING)
                                        if queuing_count > 0:
                                            group_color = Monitor.color_status(
                                                Status.QUEUING)
                                        else:
                                            completed_count = sum(
                                                1 for x in specific_list if x.status == Status.COMPLETED)
                                            if completed_count > 0:
                                                group_color = Monitor.color_status(
                                                    Status.COMPLETED)
                                colors[group_name] = group_color
                groups_data = []
                for group in colors:
                    x_bound = list()
                    y_bound = list()
                    for node in nodes:
                        if node['label'].startswith(group):
                            x_bound.append(node['x'])
                            y_bound.append(node['y'])
                    y_coordinate = sum(y_bound) / \
                        len(y_bound) if len(y_bound) > 0 else 0
                    x_coordinate = min(x_bound)
                    groups_data.append((group, x_coordinate, y_coordinate))
                    # list_groups[group] = {"color": list_groups[group]
                    #                     ['color'], "x": x_coordinate, "y": y_coordinate}
                # Sort by y
                groups_data.sort(key=lambda a: a[2], reverse=True)
                visited = set()
                for item in groups_data:
                    name, x, y = item
                    # print("{} -> x: {}, y: {}".format(name, x, y))
                    visited.add(name)
                    for jtem in groups_data:
                        namej, xj, yj = jtem
                        if namej not in name:
                            if abs(x - xj) <= 250 and abs(y - yj) <= 250:
                                # print("Collision {} {}".format(name, namej))
                                if y > yj:
                                    y = y + (250 - abs(y - yj))
                                else:
                                    y = y - (250 - abs(y - yj))
                    list_groups[name] = {"color": colors[name], "x": x, "y": y}

                # list_groups = {item[0]: {"color": colors[item[0]], "x": item[1], "y": item[2]} for item in groups_data}
                # for item in list_groups:
                #     print("{} -> x: {}, y: {}".format(item, list_groups[item]["x"], list_groups[item]["y"]))
            except Exception as exp:
                print(traceback.format_exc())
                print(exp)
        elif grouped == 'status':
            # status_list_waiting = filter(lambda x: x.status == Status.WAITING and x.packed == False, allJobs)
            list_groups['WAITING'] = {
                "color": Monitor.color_status(Status.WAITING)}
            list_groups['COMPLETED'] = {
                "color": Monitor.color_status(Status.COMPLETED)}
            list_groups['SUSPENDED'] = {
                "color": Monitor.color_status(Status.SUSPENDED)}

        # recentUpdatedJob = max(job.date for job in allJobs)
        # print(list(list_groups.keys()))
        # print(list_groups)
        return {'nodes': nodes,
                'edges': edges,
                'packages': package_to_jobs,
                'fake_edges': fake_edges,
                'groups': list(list_groups.keys()),
                'groups_data': list_groups,
                'graphviz': i_am_true_coordinates,
                'max_children': maxChildren,
                'max_parents': maxParent,
                'chunk_unit': chunk_unit,
                'chunk_size': chunk_size,
                'total_jobs': total_jobs}

    def job_list_traverse_update(self):
        """
        Traverses current job list and updates attribute 'level' to 
        reflect the hierarchical position of each job according to its dependencies
        :return: list of jobs
        """
        try:
            orderedList = list()
            # orderedbfs = list()
            allJobs = self.get_all()
            visited = list()
            # nochildren = list()
            # Find root
            root = list()
            # jobDict = dict()
            for job in allJobs:
                # jobDict[job.name] = job
                if job.has_parents() == False:
                    root.append(job)

            for item in root:
                # print(item)
                self._recursion_traverse_update(item, 0, visited, item, orderedList)

            # return orderedbfs
            return orderedList
        except Exception as exp:
            print(exp)
            return None

    def _bfs_order(self):
        nodes = []
        root = list()
        for job in self.get_all():
            if job.has_parents() == False:
                root.append(job)
        for item in root:
            stack = [item]
            while stack:
                cur_node = stack[0]
                stack = stack[1:]
                if cur_node not in nodes:
                    nodes.append(cur_node)
                    for child in cur_node._children:
                        stack.append(child)
        return nodes

    def _recursion_traverse_update(self, job, level, visited, parent, orderedList):
        """
        Handles recursive traversal and update: BFS
        """
        # for i in range(level):
        #         prefix += "|  "
        # Prefix + Job Name
        # result = "\n"+ prefix + bcolors.BOLD + job.name + bcolors.ENDC
        if job.name not in visited:
            visited.append(job.name)
            orderedList.append(job)
            level += 1
            if len(job._children) > 0:
                children = job._children
                job.level = level
                for child in children:
                    # Continues recursion
                    self._recursion_traverse_update(
                        child, level, visited, job, orderedList)
            else:
                job.level = level
        else:
            if job.level <= parent.level:
                level = parent.level + 1  # bool(random.getrandbits(1))
                job.level = level
                children = job._children
                for child in children:
                    self._recursion_traverse_update(
                        child, level, visited, job, orderedList)

                # visited.append(job.name)

    def print_with_status(self, statusChange=None):
        """
        Returns the string representation of the dependency tree of 
        the Job List

        :return: String representation
        :rtype: String
        """
        allJobs = self.get_all()
        # Header
        result = bcolors.BOLD + \
            "## String representation of Job List [" + str(len(allJobs)) + "] "

        if statusChange is not None:
            result += " with " + bcolors.OKGREEN + \
                str(len(statusChange.keys())) + \
                " Changes ##" + bcolors.ENDC + bcolors.ENDC
        else:
            result += "## " + bcolors.ENDC

        # Find root
        root = None
        for job in allJobs:
            if job.has_parents() == False:
                root = job

        # root exists
        if root is not None:
            result += self._recursion_print(root, 0, statusChange=statusChange)
        else:
            result += "\nCannot find root."

        return result

    def __str__(self):
        """
        Returns the string representation of the class.
        Usage print(class)

        :return: String representation.
        :rtype: String
        """
        allJobs = self.get_all()
        result = bcolors.BOLD + \
            "## String representation of Job List [" + \
            str(len(allJobs)) + "] ##" + bcolors.ENDC

        # Find root
        root = None
        for job in allJobs:
            if job.has_parents() == False:
                root = job

        # root exists
        if root is not None:
            result += self._recursion_print(root, 0)
        else:
            result += "\nCannot find root."

        return result

    def _recursion_print(self, job, level, statusChange=None):
        """
        Returns the list of children in a recursive way. Traverses the dependency tree.          
        :return: parent + list of children  
        :rtype: String
        """
        result = ""
        prefix = ""
        for i in range(level):
            prefix += "|  "
        # Prefix + Job Name
        result = "\n" + prefix + bcolors.BOLD + job.name + bcolors.ENDC
        if len(job._children) > 0:
            level += 1
            children = job._children
            total_children = len(job._children)
            # Writes children number
            result += " ~ [" + str(total_children) + \
                (" children] " if total_children > 1 else " child] ")
            if statusChange is not None:
                # Writes change if performed
                result += bcolors.BOLD + bcolors.OKGREEN + \
                    statusChange[job.name] if job.name in statusChange else ""
                result += bcolors.ENDC + bcolors.ENDC

            for child in children:
                # Continues recursion
                result += self._recursion_print(child,
                                                level, statusChange=statusChange)
        else:
            pass

        return result

    @staticmethod
    def get_job_times_collection(basic_config, allJobs, expid, job_to_package=None, package_to_jobs=None, timeseconds=True):
        """
        Gets queuing and running time for the collection of jobs

        :return: job running to min (queue, run, status), job running to text (text)
        """
        # Getting information
        path_local_root = basic_config.LOCAL_ROOT_DIR
        path_structure = basic_config.STRUCTURES_DIR
        db_file = os.path.join(path_local_root, "ecearth.db")
        conn = DbRequests.create_connection(db_file)
        # job_data = None
        # Job information from worker database
        job_times = DbRequests.get_times_detail_by_expid(conn, expid)
        conn.close()        
        # Job information from job historic data
        # print("Get current job data structure...")     
        experiment_history = ExperimentHistoryDirector(ExperimentHistoryBuilder(expid)).build_reader_experiment_history()  
        job_data = experiment_history.manager.get_all_last_job_data_dcs() if experiment_history.is_header_ready() else None        
        # Result variables
        job_running_time_seconds = dict()
        job_running_to_runtext = dict()
        result = dict()
        current_table_structure = dict()
        job_name_to_job_info = dict()
        # Work variables
        subjobs = list()
        # Get structure  if there are packages because package require special time calculation
        # print("Get Structure")
        if (job_to_package):
            current_table_structure = DbStructure.get_structure(expid, path_structure)
        # Main loop
        # print("Start main loop")
        for job in allJobs:
            job_info = JobList.retrieve_times(
                job.status, job.name, job._tmp_path, make_exception=False, job_times=job_times, seconds=timeseconds, job_data_collection=job_data)
            # if job_info:
            job_name_to_job_info[job.name] = job_info
            time_total = (job_info.queue_time +
                          job_info.run_time) if job_info else 0
            subjobs.append(SubJob(job.name, job_to_package.get(job.name, None), job_info.queue_time if job_info else 0,
                                  job_info.run_time if job_info else 0, time_total, job_info.status if job_info else Status.UNKNOWN))
        # print("Start job manager")
        Manager = SubJobManager(subjobs, job_to_package, package_to_jobs, current_table_structure)
        for sub in Manager.get_subjoblist():
            current_job_info = job_name_to_job_info.get(sub.name, None)  # if sub.name in job_name_to_job_info.keys(
            # ) else None
            if current_job_info:
                job_running_time_seconds[sub.name] = JobRow(sub.name, sub.queue, sub.run, sub.status, current_job_info.energy,
                                                            current_job_info.submit, current_job_info.start, current_job_info.finish, current_job_info.ncpus, current_job_info.run_id)
                job_running_to_runtext[sub.name] = job_times_to_text(sub.queue, sub.run, sub.status)

        return (job_running_time_seconds, job_running_to_runtext, [])

    @staticmethod
    def _job_running_check(status_code, name, tmp_path):
        # type: (int, str, str) -> Tuple[datetime.datetime, datetime.datetime, datetime.datetime, str]
        """
        Receives job data and returns the data from its TOTAL_STATS file in an ordered way.  
        :param status_code: Status of job  
        :type status_code: Integer  
        :param name: Name of job  
        :type name: String  
        :param tmp_path: Path to the tmp folder of the experiment  
        :type tmp_path: String  
        :return: submit time, start time, end time, status  
        :rtype: 4-tuple in datetime format
        """
        values = list()
        status_from_job = str(Status.VALUE_TO_KEY[status_code])
        now = datetime.datetime.now()
        submit_time = now
        start_time = now
        finish_time = now
        current_status = status_from_job
        path = os.path.join(tmp_path, name + '_TOTAL_STATS')
        if os.path.exists(path):
            request = 'tail -1 ' + path
            last_line = os.popen(request).readline()
            # print(last_line)

            values = last_line.split()
            # print(last_line)
            try:
                if status_code in [Status.RUNNING]:
                    submit_time = parse_date(
                        values[0]) if len(values) > 0 else now
                    start_time = parse_date(values[1]) if len(
                        values) > 1 else submit_time
                    finish_time = now
                elif status_code in [Status.QUEUING, Status.SUBMITTED, Status.HELD]:
                    submit_time = parse_date(
                        values[0]) if len(values) > 0 else now
                    start_time = parse_date(
                        values[1]) if len(values) > 1 and values[0] != values[1] else now
                elif status_code in [Status.COMPLETED]:
                    submit_time = parse_date(
                        values[0]) if len(values) > 0 else now
                    start_time = parse_date(
                        values[1]) if len(values) > 1 else submit_time
                    if len(values) > 3:
                        finish_time = parse_date(values[len(values) - 2])
                    else:
                        finish_time = submit_time
                else:
                    submit_time = parse_date(
                        values[0]) if len(values) > 0 else now
                    start_time = parse_date(values[1]) if len(
                        values) > 1 else submit_time
                    finish_time = parse_date(values[2]) if len(
                        values) > 2 else start_time
            except Exception as exp:
                start_time = now
                finish_time = now
                # NA if reading fails
                current_status = "NA"

        current_status = values[3] if (len(values) > 3 and len(
            values[3]) != 14) else status_from_job
        # TOTAL_STATS last line has more than 3 items, status is different from pkl, and status is not "NA"
        if len(values) > 3 and current_status != status_from_job and current_status != "NA":
            current_status = "SUSPICIOUS"
        return (submit_time, start_time, finish_time, current_status)

    @staticmethod
    def retrieve_times(status_code, name, tmp_path, make_exception=False, job_times=None, seconds=False, job_data_collection=None):
        # type: (int, str, str, bool, Dict[str, Tuple[int, int, int, int, int]], bool, List[JobData]) -> JobRow
        """
        Retrieve job timestamps from database.  
        :param status_code: Code of the Status of the job  
        :type status_code: Integer  
        :param name: Name of the job  
        :type name: String  
        :param tmp_path: Path to the tmp folder of the experiment  
        :type tmp_path: String  
        :param make_exception: flag for testing purposes  
        :type make_exception: Boolean
        :param job_times: Detail from as_times.job_times for the experiment
        :type job_times: Dictionary Key: job name, Value: 5-tuple (submit time, start time, finish time, status, detail id)
        :return: minutes the job has been queuing, minutes the job has been running, and the text that represents it  
        :rtype: int, int, str
        """
        status = "NA"
        energy = 0
        seconds_queued = 0
        seconds_running = 0
        queue_time = running_time = 0
        submit_time = 0
        start_time = 0
        finish_time = 0
        running_for_min = datetime.timedelta()
        queuing_for_min = datetime.timedelta()

        try:
            # Getting data from new job database
            if job_data_collection is not None:
                # for job in job_data_collection:
                #     print(job.job_name)
                job_data = next(
                    (job for job in job_data_collection if job.job_name == name), None)
                if job_data:
                    status = Status.VALUE_TO_KEY[status_code]
                    if status == job_data.status:
                        energy = job_data.energy
                        if job_times:
                            t_submit, t_start, t_finish, _, _ = job_times.get(name, (0, 0, 0, 0, 0))                            
                            if t_finish - t_start > job_data.running_time:
                                t_submit = t_submit if t_submit > 0 else job_data.submit
                                t_start = t_start if t_start > 0 else job_data.start
                                t_finish = t_finish if t_finish > 0 else job_data.finish
                            else:
                                t_submit = job_data.submit if job_data.submit > 0 else t_submit
                                t_start = job_data.start if job_data.start > 0 else t_start
                                t_finish = job_data.finish if job_data.finish > 0 else t_finish
                            job_data.submit = t_submit
                            job_data.start = t_start
                            job_data.finish = t_finish
                        else:
                            t_submit = job_data.submit
                            t_start = job_data.start
                            t_finish = job_data.finish
                        # Test if start time does not make sense
                        if t_start >= t_finish:
                            if job_times:
                                _, c_start, _, _, _ = job_times.get(name, (0, t_start, t_finish, 0, 0))
                                job_data.start = c_start if t_start > c_start else t_start                                                                 

                        if seconds == False:
                            queue_time = math.ceil(job_data.queuing_time / 60)
                            running_time = math.ceil(job_data.running_time / 60)
                        else:
                            queue_time = job_data.queuing_time
                            running_time = job_data.running_time

                        if status_code in [Status.SUSPENDED]:
                            t_submit = t_start = t_finish = 0
                        return JobRow(job_data.job_name, int(queue_time), int(running_time), status, energy, t_submit, t_start, t_finish, job_data.ncpus, job_data.run_id)

            # Using standard procedure
            if status_code in [Status.RUNNING, Status.SUBMITTED, Status.QUEUING, Status.FAILED] or make_exception == True:
                # COMPLETED adds too much overhead so these values are now stored in a database and retrieved separatedly
                submit_time, start_time, finish_time, status = JobList._job_running_check(status_code, name, tmp_path)
                if status_code in [Status.RUNNING, Status.FAILED]:
                    running_for_min = (finish_time - start_time)
                    queuing_for_min = (start_time - submit_time)
                    submit_time = mktime(submit_time.timetuple())
                    start_time = mktime(start_time.timetuple())
                    finish_time = mktime(finish_time.timetuple()) if status_code in [
                        Status.FAILED] else 0
                else:
                    queuing_for_min = (datetime.datetime.now() - submit_time)
                    running_for_min = datetime.datetime.now() - datetime.datetime.now()
                    submit_time = mktime(submit_time.timetuple())
                    start_time = 0
                    finish_time = 0

                submit_time = int(submit_time)
                start_time = int(start_time)
                finish_time = int(finish_time)

                seconds_queued = queuing_for_min.total_seconds()
                seconds_running = running_for_min.total_seconds()

            else:
                # For job times completed we no longer use timedeltas, but timestamps
                status = Status.VALUE_TO_KEY[status_code]                
                if job_times and status_code not in [Status.READY, Status.WAITING, Status.SUSPENDED]:                    
                    if name in job_times:                        
                        submit_time, start_time, finish_time, status, detail_id = job_times[name]
                        seconds_running = finish_time - start_time
                        seconds_queued = start_time - submit_time                                                
                        submit_time = int(submit_time)
                        start_time = int(start_time)
                        finish_time = int(finish_time)
                else:
                    submit_time = 0
                    start_time = 0
                    finish_time = 0

        except Exception as exp:
            print(traceback.format_exc())
            return

        seconds_queued = seconds_queued * \
            (-1) if seconds_queued < 0 else seconds_queued
        seconds_running = seconds_running * \
            (-1) if seconds_running < 0 else seconds_running
        if seconds == False:
            queue_time = math.ceil(
                seconds_queued / 60) if seconds_queued > 0 else 0
            running_time = math.ceil(
                seconds_running / 60) if seconds_running > 0 else 0
        else:
            queue_time = seconds_queued
            running_time = seconds_running
            # print(name + "\t" + str(queue_time) + "\t" + str(running_time))        
        return JobRow(name, 
                    int(queue_time), 
                    int(running_time), 
                    status, 
                    energy, 
                    int(submit_time), 
                    int(start_time), 
                    int(finish_time), 
                    None,
                    None)

    @staticmethod
    def retrieve_packages(basic_config, expid, current_jobs=None):
        """
        Retrieves dictionaries that map the collection of packages in the experiment

        :param basic_config: Basic configuration 
        :type basic_config: Configuration Object
        :param expid: Experiment Id
        :type expid: String
        :param current_jobs: list of names of current jobs
        :type current_jobs: list
        :return: job to package, package to jobs, package to package_id, package to symbol  
        :rtype: Dictionary(Job Object, Package_name), Dictionary(Package_name, List of Job Objects), Dictionary(String, String), Dictionary(String, String)
        """
        monitor = Monitor()
        packages = None
        try:
            packages = JobPackagePersistence(os.path.join(basic_config.LOCAL_ROOT_DIR, expid, "pkl"),
                                             "job_packages_" + expid).load(wrapper=False)
        except Exception as ex:
            print("Wrapper table not found, trying packages.")
            packages = None
            try:
                packages = JobPackagePersistence(os.path.join(basic_config.LOCAL_ROOT_DIR, expid, "pkl"),
                                                 "job_packages_" + expid).load(wrapper=True)
            except Exception as exp2:
                packages = None
                pass
            pass

        job_to_package = dict()
        package_to_jobs = dict()
        package_to_package_id = dict()
        package_to_symbol = dict()
        if (packages):
            try:
                for exp, package_name, job_name in packages:
                    if len(str(package_name).strip()) > 0:
                        if (current_jobs):
                            if job_name in current_jobs:
                                job_to_package[job_name] = package_name
                        else:
                            job_to_package[job_name] = package_name
                    # list_packages.add(package_name)
                for name in job_to_package:
                    package_name = job_to_package[name]
                    package_to_jobs.setdefault(package_name, []).append(name)
                    # if package_name not in package_to_jobs.keys():
                    #     package_to_jobs[package_name] = list()
                    # package_to_jobs[package_name].append(name)
                for key in package_to_jobs:
                    package_to_package_id[key] = key.split("_")[2]
                list_packages = job_to_package.values()
                for i in range(len(list_packages)):
                    if i % 2 == 0:
                        package_to_symbol[list_packages[i]] = 'square'
                    else:
                        package_to_symbol[list_packages[i]] = 'hexagon'
            except Exception as ex:
                print(traceback.format_exc())

        return (job_to_package, package_to_jobs, package_to_package_id, package_to_symbol)

    @staticmethod
    def ts_to_datetime(timestamp):
        if timestamp and timestamp > 0:
            # print(datetime.datetime.utcfromtimestamp(
            #     timestamp).strftime('%Y-%m-%d %H:%M:%S'))
            return datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
        else:
            return None
    # def timedelta2minutes(deltatime):
    #     return deltatime.days * 1440 + deltatime.minutes / 3600.0
