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
import traceback
import datetime
import math

# Spectral imports
# End Spectral imports

from time import time, mktime
from dateutil.relativedelta import relativedelta

from autosubmit_api.autosubmit_legacy.job.job_utils import SubJob
from autosubmit_api.autosubmit_legacy.job.job_utils import SubJobManager, job_times_to_text
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.performance.utils import calculate_ASYPD_perjob, calculate_SYPD_perjob
from autosubmit_api.components.jobs import utils as JUtils
from autosubmit_api.monitor.monitor import Monitor
from autosubmit_api.common.utils import Status
from bscearth.utils.date import date2str, parse_date
# from autosubmit_legacy.job.tree import Tree
from autosubmit_api.database import db_structure as DbStructure
from autosubmit_api.database.db_jobdata import JobDataStructure, JobRow
from autosubmit_api.builders.experiment_history_builder import ExperimentHistoryDirector, ExperimentHistoryBuilder
from autosubmit_api.history.data_classes.job_data import JobData

from typing import List, Dict, Optional, Tuple

from autosubmit_api.persistance.experiment import ExperimentPaths


class JobList:
    """
    Class to manage the list of jobs to be run by autosubmit
    """
    def __init__(self, expid, config, parser_factory, job_list_persistence):
        self._expid = expid


    @property
    def expid(self):
        """
        Returns the experiment identifier

        :return: experiment's identifierexpid
        :rtype: str
        """
        return self._expid

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
                    ("+" * len([x for x in already_included if x == job.job_name])
                     if job.job_name in already_included else "")
                already_included.append(original_job_name)

        # for job in job_list:
        #     print(job.job_name)
        # dateformat = self.get_date_format
        sync = JobList.get_synctag()
        check_mark = JobList.get_checkmark()
        # Identify chunks
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
        exp_paths = ExperimentPaths(expid)
        path_to_logs = exp_paths.tmp_log_dir

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
                local_list = [x for x in job_list if (
                    str(x.date) == str(key) and str(x.section) == str(member)) or x in current_list]
                print(("Local list {} for {} - {}".format(len(local_list), key, member)))
                date_member_groups[(key, member)] = sorted(
                    local_list, key=lambda x: x.chunk if x.chunk is not None else 0)
                added_job_names.update({job.job_name for job in local_list})
                # print(local_list[0].name)
                # jobs = [job for job in jobs if job not in local_short_list]
                # jobs.extend(date_member_repetition[(date,member)])
                # jobs -= local_list
        print(("Spent in main: " + str(time() - start_time)))

        # Printing date - member groups / date - chunk syncs
        # Working with date-member groups
        for date in list(dates.keys()):
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
                    if job.member is None:
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
                   date_folder_title = "{0}_{1} {2}".format(
                       expid,
                       str(dates[date]),
                       date_tag
                   )
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
            local_list = [x for x in jobs if x.date == date]
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
                    ("+" * len([x for x in already_included if x == job.job_name])
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
                    name, None)], key=lambda x: x.chunk if x.chunk is not None else 0)
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
                                            'refKey': job.job_name + ("+" * len([x for x in already_included if x == job.job_name]) if job.job_name in already_included else ""),
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

    @staticmethod
    def get_job_times_collection(basic_config: APIBasicConfig, allJobs, expid, job_to_package=None, package_to_jobs=None, timeseconds=True):
        """
        Gets queuing and running time for the collection of jobs

        :return: job running to min (queue, run, status), job running to text (text)
        """
        # Getting information
        # path_local_root = basic_config.LOCAL_ROOT_DIR
        path_structure = basic_config.STRUCTURES_DIR
        # db_file = os.path.join(path_local_root, basic_config.DB_FILE)
        # Job information from job historic data
        # print("Get current job data structure...")
        job_data = None
        try:
            experiment_history = ExperimentHistoryDirector(ExperimentHistoryBuilder(expid)).build_reader_experiment_history()
            job_data = experiment_history.manager.get_all_last_job_data_dcs() if experiment_history.is_header_ready() else None
        except Exception:
            print(traceback.print_exc())
        # Result variables
        job_running_time_seconds = dict()
        job_running_to_runtext = dict()
        # result = dict()
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
                job.status, job.name, job._tmp_path, make_exception=False, job_times=None, seconds=timeseconds, job_data_collection=job_data)
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
    def _job_running_check(
        status_code: int, name: str, tmp_path: str
    ) -> Tuple[datetime.datetime, datetime.datetime, datetime.datetime, str]:
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
            except Exception:
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
    def retrieve_times(
        status_code: int,
        name: str,
        tmp_path: str,
        make_exception: bool = False,
        job_times: Optional[Dict[str, Tuple[int, int, int, int, int]]] = None,
        seconds: bool = False,
        job_data_collection: Optional[List[JobData]] = None,
    ) -> JobRow:
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

                        if seconds is False:
                            queue_time = math.ceil(job_data.queuing_time / 60)
                            running_time = math.ceil(job_data.running_time / 60)
                        else:
                            queue_time = job_data.queuing_time
                            running_time = job_data.running_time

                        if status_code in [Status.SUSPENDED]:
                            t_submit = t_start = t_finish = 0
                        return JobRow(job_data.job_name, int(queue_time), int(running_time), status, energy, t_submit, t_start, t_finish, job_data.ncpus, job_data.run_id)

            # Using standard procedure
            if status_code in [Status.RUNNING, Status.SUBMITTED, Status.QUEUING, Status.FAILED] or make_exception is True:
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

        except Exception:
            print((traceback.format_exc()))
            return

        seconds_queued = seconds_queued * \
            (-1) if seconds_queued < 0 else seconds_queued
        seconds_running = seconds_running * \
            (-1) if seconds_running < 0 else seconds_running
        if seconds is False:
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
