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

import datetime


class SubJob(object):
    """
    Class to manage package times
    """

    def __init__(self, name, package=None, queue=0, run=0, total=0, status="UNKNOWN"):
        self.name = name
        self.package = package
        self.queue = queue
        self.run = run
        self.total = total
        self.status = status
        self.transit = 0
        self.parents = list()
        self.children = list()


class SubJobManager(object):
    """
    Class to manage list of SubJobs
    """

    def __init__(self, subjoblist, job_to_package=None, package_to_jobs=None, current_structure=None):
        self.subjobList = subjoblist
        # print("Number of jobs in SubManager : {}".format(len(self.subjobList)))
        self.job_to_package = job_to_package
        self.package_to_jobs = package_to_jobs
        self.current_structure = current_structure
        self.subjobindex = dict()
        self.subjobfixes = dict()
        self.process_index()
        self.process_times()

    def process_index(self):
        """
        Builds a dictionary of jobname -> SubJob object.
        """
        for subjob in self.subjobList:
            self.subjobindex[subjob.name] = subjob

    def process_times(self):
        """
        """
        if (self.job_to_package) and (self.package_to_jobs):
            if(self.current_structure) and len(list(self.current_structure.keys())) > 0:
                # Structure exists
                new_queues = dict()
                fixes_applied = dict()
                for package in self.package_to_jobs:
                    # SubJobs in Package
                    local_structure = dict()
                    # SubJob Name -> SubJob Object
                    local_index = dict()
                    subjobs_in_package = [x for x in self.subjobList if x.package ==
                                                package]
                    local_jobs_in_package = [job for job in subjobs_in_package]
                    # Build index
                    for sub in local_jobs_in_package:
                        local_index[sub.name] = sub
                    # Build structure
                    for sub_job in local_jobs_in_package:
                        # If job in current_structure, store children names in dictionary
                        # local_structure: Job Name -> Children (if present in the Job package)
                        local_structure[sub_job.name] = [v for v in self.current_structure[sub_job.name]
                                                         if v in self.package_to_jobs[package]] if sub_job.name in self.current_structure else list()
                        # Assign children to SubJob in local_jobs_in_package
                        sub_job.children = local_structure[sub_job.name]
                        # Assign sub_job Name as a parent of each of its children
                        for child in local_structure[sub_job.name]:
                            local_index[child].parents.append(sub_job.name)

                    # Identify root as the job with no parents in the package
                    roots = [sub for sub in local_jobs_in_package if len(
                        sub.parents) == 0]

                    # While roots exists (consider pop)
                    while(len(roots) > 0):
                        sub = roots.pop(0)
                        if len(sub.children) > 0:
                            for sub_children_name in sub.children:
                                if sub_children_name not in new_queues:
                                    # Add children to root to continue the sequence of fixes
                                    roots.append(
                                        local_index[sub_children_name])
                                    fix_size = max(self.subjobindex[sub.name].queue +
                                                   self.subjobindex[sub.name].run, 0)
                                    # fixes_applied.setdefault(sub_children_name, []).append(fix_size) # If we care about repetition
                                    # Retain the greater fix size
                                    if fix_size > fixes_applied.get(sub_children_name, 0):
                                        fixes_applied[sub_children_name] = fix_size
                                    fixed_queue_time = max(
                                        self.subjobindex[sub_children_name].queue - fix_size, 0)
                                    new_queues[sub_children_name] = fixed_queue_time
                                    # print(new_queues[sub_name])

                for key, value in list(new_queues.items()):
                    self.subjobindex[key].queue = value
                    # print("{} : {}".format(key, value))
                for name in fixes_applied:
                    self.subjobfixes[name] = fixes_applied[name]

            else:
                # There is no structure
                for package in self.package_to_jobs:
                    # Filter only jobs in the current package
                    filtered = [x for x in self.subjobList if x.package ==
                                      package]
                    # Order jobs by total time (queue + run)
                    filtered = sorted(
                        filtered, key=lambda x: x.total, reverse=False)
                    # Sizes of fixes
                    fixes_applied = dict()
                    if len(filtered) > 1:
                        temp_index = 0
                        filtered[0].transit = 0
                        # Reverse for
                        for i in range(len(filtered) - 1, 0, -1):
                            # Assume that the total time of the next job is always smaller than
                            # the queue time of the current job
                            # because the queue time of the current also considers the
                            # total time of the previous (next because of reversed for) job by default
                            # Confusing? It is.
                            # Assign to transit the adjusted queue time
                            filtered[i].transit = max(filtered[i].queue -
                                                      filtered[i - 1].total, 0)

                        # Positive or zero transit time
                        positive = len(
                            [job for job in filtered if job.transit >= 0])

                        if (positive > 1):
                            for i in range(0, len(filtered)):
                                if filtered[i].transit >= 0:
                                    temp_index = i
                                    if i > 0:
                                        # Only consider after the first job
                                        filtered[i].queue = max(filtered[i].queue -
                                                                filtered[i - 1].total, 0)
                                        fixes_applied[filtered[i].name] = filtered[i - 1].total
                                else:
                                    filtered[i].queue = max(filtered[i].queue -
                                                            filtered[temp_index].total, 0)
                                    fixes_applied[filtered[i].name] = filtered[temp_index].total
                                # it is starting of level

                    for sub in filtered:
                        self.subjobindex[sub.name].queue = sub.queue
                        # print("{} : {}".format(sub.name, sub.queue))
                    for name in fixes_applied:
                        self.subjobfixes[name] = fixes_applied[name]

    def get_subjoblist(self):
        """
        Returns the list of SubJob objects with their corrected queue times
        in the case of jobs that belong to a wrapper.
        """
        return self.subjobList


def job_times_to_text(minutes_queue, minutes_running, status):
    """
    Return text correpsonding to queue and running time
    :param minutes_queue: seconds queuing (actually using seconds)
    :type minutes_queue: int
    :param minutes_running: seconds running (actually using seconds)
    :type minutes_running: int
    :param status: current status
    :type status: string
    :return: string
    """
    if status in ["COMPLETED", "FAILED", "RUNNING"]:
        running_text = "( " + str(datetime.timedelta(seconds=minutes_queue)) + \
            " ) + " + \
            str(datetime.timedelta(seconds=minutes_running))
    elif status in ["SUBMITTED", "QUEUING", "HELD", "HOLD"]:
        running_text = "( " + \
            str(datetime.timedelta(seconds=minutes_queue)) + " )"
    elif status in ["NA"]:
        running_text = " <small><i><b>NA</b></i></small>"
    else:
        running_text = ""

    if status == "SUSPICIOUS":
        running_text = running_text + \
            " <small><i><b>SUSPICIOUS</b></i></small>"
    return running_text
