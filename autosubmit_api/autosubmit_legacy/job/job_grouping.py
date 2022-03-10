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

from autosubmitAPIwu.job.job_common import Status
from bscearth.utils.date import date2str
import copy

class JobGrouping(object):

    def __init__(self, group_by, jobs, job_list, expand_list=list(), expanded_status=list()):
        """
        CONSTRUCTOR:\n
        group_by: automatic, date, member, chunk.\n
        jobs: A copy of the jobs.\n
        job_list: JobList instance.\n
        expand_list: A formula that specifies the jobs that should not be grouped (or that should be expanded) e.g. "[ 19601101 [ fc0 [1 2 3 4] fc1 [1] ] 19651101 [ fc0 [16-30] ] ]".\n
        espanded_status: List of status that should not be grouped (e.g. "RUNNING, FAILED") (or that should be expanded). Comma separated or single.\n
        """        
        self.group_by = group_by
        self.jobs = jobs
        self.job_list = job_list
        self.date_format = job_list.get_date_format()
        self.expand_list = expand_list
        self.expand_status = expanded_status
        self.automatic = False
        # Key: Group, Value: Starts as a List(of String) but at the end of the process turns into String.
        self.group_status_dict = dict() 
        # List of jobs that should not be grouped as a result of parsing expand_list    
        self.ungrouped_jobs = list()

    def group_jobs(self):
        """
        Main method of the class.\n
        Groups self.jobs according to parameters set in constructor.\n
        Choose of return value is questionable.\n

        :return: Dictionary that has 2 keys.\n
        Key 1: [Jobs] Value 1: Dictionary of Key: Job, Value: Group.\n
        Key 2: [Status] Value 1: Dictionary of Key: Group, Value: Final Status
        """
        if self.expand_list:
            self._set_expanded_jobs()

        jobs_group_dict = dict()
        blacklist = list()

        groups_map = dict()
        if self.group_by == 'automatic':
            # This assignment is almost irrelevant
            self.automatic = True
            # Grouping by automatic, groups_map is Empty
            # Filling dictionary Key: Job Name, Value: Group Name
            # Perhaps the original developer forgot to include self.ungrouped_jobs in the automatic grouping
            jobs_group_dict = self._automatic_grouping(groups_map)
        else:
            self._create_groups(jobs_group_dict, self.ungrouped_jobs)

            # Retrieve dictionary of group -> status list (set) in that group
            # This dictionary was filled in self._create_groups()
            for group, statuses in self.group_status_dict.items():
                # Function that returns the status of the group
                # Provides a hierarchy, returns int 
                status = self._set_group_status(statuses)
                self.group_status_dict[group] = status

        final_jobs_group = dict()
        # Iterating the items in the Dictionary that
        # associates job -> group, dictionary filled in self._create_groups()
        for job, groups in jobs_group_dict.items():
            for group in groups:
                # This blacklist is always empty
                if group not in blacklist:
                    # This part is confusing
                    # groups_map filled if group_by is automatic, otherwise empty
                    # Iterating through old small groups
                    while group in groups_map:
                        # group = new bigger group
                        group = groups_map[group]                    
                    # Testing if group exists
                    # Status is now unique from the process above
                    if group in self.group_status_dict:
                        # Start filling final_jobs_group
                        if job not in final_jobs_group:
                            final_jobs_group[job] = list()
                        # Associate job -> group
                        final_jobs_group[job].append(group)
        # Why?
        jobs_group_dict = final_jobs_group

        groups_dict = dict()
        groups_dict['jobs'] = jobs_group_dict
        groups_dict['status'] = self.group_status_dict

        return groups_dict

    # Fill self.ungrouped_jobs 
    def _set_expanded_jobs(self):
        """
        Uses self.expand_list to produce a list of jobs that should not be grouped (or that must be expanded).\n
        Parses the input self.expand_list as a nested expression.\n
        Uses self.group_by as a decision variable.\n

        Modifies: self.expand_list
        """

        text = self.expand_list

        self.ungrouped_jobs = []

        from pyparsing import nestedExpr
        """
        Function to parse rerun specification from json format

        :param text: text to parse
        :type text: list
        :return: parsed output
        """
        count = 0

        out = nestedExpr('[', ']').parseString(text).asList()

        depth = lambda L: isinstance(L, list) and max(map(depth, L)) + 1

        if self.group_by == 'date':
            if depth(out) == 2:
                dates = list()
                for date in out[0]:
                    dates.append(date)
                self.ungrouped_jobs = dates
            else:
                raise ValueError("Please check the syntax of the expand parameter including only dates")
        elif self.group_by == 'member':
            if depth(out) == 3:
                for element in out[0]:
                    if count % 2 == 0:
                        date = out[0][count]
                        members = out[0][count + 1]
                        for member in members:
                            self.ungrouped_jobs.append(date + '_' + member)
                        count += 1
                    else:
                        count += 1
            else:
                raise ValueError(
                    "Please check the syntax of the expand parameter including dates and the corresponding members")
        elif self.group_by == 'chunk':
            if depth(out) == 4:
                for element in out[0]:
                    if count % 2 == 0:
                        date = out[0][count]
                        member_chunks = out[0][count + 1]
                        member_count = 0
                        for element_member in member_chunks:
                            if member_count % 2 == 0:
                                member = member_chunks[member_count]
                                chunks = list()
                                for chunk in member_chunks[member_count + 1]:
                                    if chunk.find("-") != -1:
                                        numbers = chunk.split("-")
                                        for count in range(int(numbers[0]), int(numbers[1]) + 1):
                                            chunks.append(count)
                                    else:
                                        chunks.append(int(chunk))
                                for chunk in chunks:
                                    self.ungrouped_jobs.append(date + '_' + member + '_' + str(chunk))
                            member_count += 1
                    count += 1
            else:
                raise ValueError(
                    "Please check the syntax of the expand parameter including dates and the corresponding members and chunks")

    def _set_group_status(self, statuses):
        """
        Receives a collection of status.\n 
        :return: Final status.\n
        :rtype: int
        """
        if isinstance(statuses, int):
            return statuses
        if len(statuses) == 1:
            return next(iter(statuses))
        else:
            if Status.FAILED in statuses:
                return Status.FAILED
            elif Status.RUNNING in statuses:
                return Status.RUNNING
            elif Status.SUBMITTED in statuses:
                return Status.SUBMITTED
            elif Status.QUEUING in statuses:
                return Status.QUEUING
            elif Status.READY in statuses:
                return Status.READY
            elif Status.WAITING in statuses:
                return Status.WAITING
            elif Status.SUSPENDED in statuses:
                return Status.SUSPENDED
            elif Status.UNKNOWN in statuses:
                return Status.UNKNOWN

    def _create_groups(self, jobs_group_dict, blacklist=list()):
        """
        Creates some an approximation of the groups.
        Fills self.group_status_dict[] as dictionary Key: Group, Value: Set of Status.\n

        jobs_group_dict: as a reference and fills it. Key: Job.Name, Value: Group.\n
        blacklist: List of jobs that should not be grouped.\n
        When called form automatic, receives en empty list as blacklist.\n
        When called from other grouping option, the blacklist starts as the list self.ungrouped_jobs.\n

        Uses self.expand_status (list of status that should not be grouped).\n
        Modifies: self.jobs, self.group_status_dict, [parameter] jobs_group_dict
        """
        # Reverse iteration for some reason, bottom-up approach perhaps
        for i in reversed(range(len(self.jobs))):
            job = self.jobs[i]

            groups = []
            # Returns True or False
            if not self._check_synchronized_job(job, groups):
                # Split is only set when doing automatic
                if self.group_by == 'split':
                    if job.split is not None:
                        idx = job.name.rfind("_")
                        groups.append(job.name[:idx - 1] + job.name[idx + 1:])                
                elif self.group_by == 'chunk':
                    if job.chunk is not None:
                        # Building group name
                        groups.append(date2str(job.date, self.date_format) + '_' + job.member + '_' + str(job.chunk))
                elif self.group_by == 'member':
                    if job.member is not None:
                        groups.append(date2str(job.date, self.date_format) + '_' + job.member)
                elif self.group_by == 'date':
                    if job.date is not None:                        
                        groups.append(date2str(job.date, self.date_format))
            # If a group has been created, then current job is used, so it is taken out of the original list.
            # Modifying an object while iterating it is not really recommended in my opinion
            if groups:
                self.jobs.pop(i)
                #print("Popping: " + str(job1.name) + " because " + str(groups))

            # Only one group is generated every iteration
            while groups:
                group = groups.pop(0)
                # Checking blacklist to avoid repetition
                if group not in blacklist:
                    if group not in self.group_status_dict:
                        self.group_status_dict[group] = set()
                    # Dictionary of group name to a list of status codes (0 -> WAITING) of its jobs
                    self.group_status_dict[group].add(job.status)                                    
                    # If status code of job in expand_status list (from input command), then it should not be grouped 
                    # OR 
                    # If automatic grouping and group already in the dictionary from above (which is redundant)
                    # AND the length of the value for the key 'group' is greater than 1, meaning that more than 1 status has been added, not allowed for automatic
                    if job.status in self.expand_status or \
                            self.automatic and group in self.group_status_dict and (len(self.group_status_dict[group]) > 1):
                        # Remove the group from the result
                        self.group_status_dict.pop(group)
                        # Adding the group to the blacklist
                        blacklist.append(group)
                        break
                    # Is this job in the list of jobs grouped?    
                    if job.name not in jobs_group_dict:
                        jobs_group_dict[job.name] = list()
                    # Dictionary of jobs to the groups they belong
                    jobs_group_dict[job.name].append(group)
                    


    # This is always false
    def _check_synchronized_job(self, job, groups):
        """
        Always returns False
        Does not change groups
        """
        synchronized = False
        # Making sure job is a chunk
        if job.chunk is not None:   
            # job.chunk exists but .date and .member don't. Is that possible?         
            if job.date is None and job.member is None:
                # Rule: If job.chunk exists, and job.date and job.member are None
                # then this job is sync
                synchronized = True
                for date in self.job_list.get_date_list():
                    # Create group name for every date in experiment
                    group_name = date2str(date, self.date_format)
                    if self.group_by in ['member', 'chunk']:                        
                        for member in self.job_list.get_member_list():
                            # If group_by is member, add +member to group name
                            group_name += '_' + member
                            if self.group_by in ['chunk']:
                                # If group_by is chunk, add +chunk to group name
                                group_name += '_' + str(job.chunk)
                            # Adding group name to list of groups
                            groups.append(group_name)
                            # Innecesary line
                            group_name = date2str(date, self.date_format)
                    else:
                        groups.append(group_name)
            # .date is not None and .member is not None
            elif job.member is None:
                # Rule: If job.chunk exists, and job.member is None, meaning that job.date is not None
                # then this job is sync
                synchronized = True                
                if self.group_by == 'date':
                    # Adding groups to list
                    groups.append(date2str(job.date, self.date_format))
                else:
                    for member in self.job_list.get_member_list():
                        group_name = date2str(job.date, self.date_format) + '_' + member
                        if self.group_by in ['chunk']:
                            group_name += '_' + str(job.chunk)
                        groups.append(group_name)

        return synchronized


    def _automatic_grouping(self, groups_map):
        """
        Performs automatic grouping.\n
        groups_map: is empty. In this process this will be filled as a Dictionary Key: Old small group, Value: New bigger group. \n
        Modifies: *self.groups_status_dict*, self.jobs\n

        :return: Dictionary that matches job name to corresponding group name.\n
        :rtype: Dictionary Key: String, Value: String
        """

        all_jobs = copy.deepcopy(self.jobs)
        # Try running as split
        split_groups, split_groups_status = self._create_splits_groups()
        
        blacklist = list()
        jobs_group_dict = dict()
        self.group_status_dict = dict()
        # Try running as chunk
        self.group_by = 'chunk'
        self.jobs = all_jobs
        self._create_groups(jobs_group_dict, blacklist)
        
        for group, statuses in self.group_status_dict.items():
            # Concludes a status for the group
            status = self._set_group_status(statuses)
            # Assign that status to the key group in the dictionary
            self.group_status_dict[group] = status


        # At this point groups_map is empty
        
        # Enter high level thing
        self._create_higher_level_group(self.group_status_dict.keys(), groups_map)

        # Using split_groups, split_groups_status that were extracted at the start of the function
        # Also uses jobs_group_dict that is a result from chunk grouping
        self._fix_splits_automatic_grouping(split_groups, split_groups_status, jobs_group_dict)


        # Check if remaining jobs can be grouped, reversed so it performs bottom-up
        # Since the last grouping was done by chunk, the list self.jobs still contains those jobs that can be merged into bigger groups
        # See self._cheate_higher_level_group
        for i in reversed(range(len(self.jobs))):            
            job = self.jobs[i]            
            for group, status in self.group_status_dict.items():
                # If the name of the group is contained in the name of the job and they have the same status
                if group in job.name and status == job.status:
                    # Add the job and assign it to the new group
                    jobs_group_dict[job.name] = [group]
                    self.jobs.pop(i)

        return jobs_group_dict


    def _create_splits_groups(self):
        """
        Only called from automatic grouping.\n
        Sets self.group_by to 'split', starts a bottom-up grouping process.\n

        :return: Dictionary of Job Names to Group Names, Dictionary of Group Names to List of Status of Jobs included in Group.\n
        :rtype: Tuple([Dictionary Key: String, Value: String], [Dictonary Key: String, Value: List(of String)])
        """
        jobs_group_dict = dict()

        self.group_by = 'split'
        self._create_groups(jobs_group_dict, list())
        return jobs_group_dict, self.group_status_dict

    def _fix_splits_automatic_grouping(self, split_groups, split_groups_status, jobs_group_dict):
        """
        This function will only be executed when jobs are using split in the experiment, and the group_by options has been set to automatic.
        """
        if split_groups and split_groups_status:
            group_maps = dict()
            for group in self.group_status_dict.keys():
                matching_groups = [split_group for split_group in split_groups_status.keys() if group in split_group]
                for matching_group in matching_groups:
                    group_maps[matching_group] = group
                    split_groups_status.pop(matching_group)

            for split_group, statuses in split_groups_status.items():
                status = self._set_group_status(statuses)
                self.group_status_dict[split_group] = status

            for job, groups in split_groups.items():
                final_groups = list()
                for group in groups:
                    if group in group_maps:
                        group = group_maps[group]
                    final_groups.append(group)
                if final_groups:
                    jobs_group_dict[job] = final_groups

    def _check_valid_group(self, groups_list, name, groups_map):
        """
        Determines if a group_list can be merged into a new bigger group name.\n
        groups_list: List of groups names of those that will possibly be grouped inside a higher group. \n
        name: Also known as new_group, is a possible new group name that groups groups_list.\n
        Modifies self.group_status_dict. Adds new bigger groups.\n
        groups_map: Starts as Empty.\n
        :return: True if the assignment is valid, False otherwise.\n
        :rtype: Boolean
        """
        # Retrieves status from dictionary Keys: group name, Values: Status
        # At this point it is a unique value per key
        group_status = self.group_status_dict[groups_list[0]]

        # Iterating starting at second item
        for group in groups_list[1:]:
            status = self.group_status_dict[group]
            # If the status of the first item in the list of existing groups 
            # is not the same as the other existing groups, then not valid            
            if status != group_status:
                return False
        
        # At this point the assignment is valid   
        for group in groups_list:
            # Take out of dict the groups that will be merged
            self.group_status_dict.pop(group)
            # map group to name (proposed group)
            groups_map[group] = name

        # Add name to group dict with the status previously determined
        self.group_status_dict[name] = group_status
        return True

    def _create_higher_level_group(self, groups_to_check, groups_map):
        """
        Reviews groups_to_check and attempts to merge these groups into bigger ones. The list of groups that can be merged is stored in groups_map.
        Curiously, it does not receive jobs_group_dict that is highly related to self.group_status_dict.\n
        Modifies self.group_status_dict.\n
        groups_to_check: Groups created from chunk pre process, only group names as it receives only keys.\n
        groups_map: Empty. Dictionary Key: Old small group, Value: New bigger group. \n
        Also uses: self.group_status_dict, self.job_list
        """
        
        checked_groups = list()
        for group in groups_to_check:
            # This if is not needed, groups_to_check === self.group_status_dict.keys()
            if group in self.group_status_dict:
                split_count = len(group.split('_'))
                # splits > 1 indicates that we are not at date level
                # split === 1 indicates date level, if date level then no more reduction is possible
                if split_count > 1:
                    # new group name is equal to the name of the group until the last occurrence of "_"
                    # This is a possible new group
                    new_group = group[:(group.rfind("_"))]
                    # If splits === 3 then we are at chunk level
                    # Else it is member level
                    # The number of possible groups according to the level (member or chunk)
                    num_groups = len(self.job_list.get_chunk_list()) if split_count == 3 else len(self.job_list.get_member_list())
                    # Controlling repetition
                    if new_group not in checked_groups:
                        checked_groups.append(new_group)
                        # This one takes the prize for weirdest one yet
                        # Selects from self.group_status_dict (group names) if key contains new_group+'_'
                        # Meaning that we are counting the number of elements in  the list of groups already defined (self.group_status_dict) 
                        # that a are a subset of new_group+'_'
                        possible_groups = [existing_group for existing_group in list(self.group_status_dict.keys()) if
                                              new_group+'_' in existing_group]

                        # If length of list from the line before is equal to the number of chunks or members
                        # Meaning that there is parity between the possible new_group and its subsets, to the number of chunks or members.
                        # chunks in the case of making possible member groups, members in the case of making possible date groups
                        if len(possible_groups) == num_groups:
                            # Remember that groups_map starts as empty
                            if self._check_valid_group(possible_groups, new_group, groups_map):
                                # Remember that groups_to_check === self.group_status_dict.keys()
                                # So, adding a new key to self.group_status_dict
                                # An attempt to make recursive, bottom-up                                
                                groups_to_check.append(new_group)