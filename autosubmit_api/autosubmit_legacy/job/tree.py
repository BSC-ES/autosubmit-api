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

import json 

class Tree(object):

    def __init__(self, list_job):
        self.root = list()        
        self._listjob = list_job
        self.visited = list()
        for job in self._listjob:                       
            if job.has_parents() == False:
                self.root.append(job)
            
    def traverse_format(self):
        """
        Start recursive traversal and construction of tree
        """        
        result = list()
        for start in self.root:            
            self.visited.append(start.name)
            level = 0
            result.append({'title' : start.title, 'refKey': start.name, 'data': 'Empty', 'expanded': True , 'children' : self.recursive_add(start, level)})
        return result
        
    def recursive_add(self, job, level):
        res_data = list()
        level = level + 1
        for start in job._children:            
            if start.name not in self.visited:                
                self.visited.append(start.name)
                res_data.append({'title' : start.title, 'refKey': start.name, 'data': 'Empty', 'expanded': True if level <= 100 else False, 'children': self.recursive_add(start,level)})
            else:
                res_data.append({'title' : start.title, 'refKey': start.name, 'data': 'Empty', 'children': []})
        return res_data


        


# class Node(object):
#     def __init__(self, identifier, data = None):
#         self._identifier = identifier
#         self.data = data
#         self.children = {}