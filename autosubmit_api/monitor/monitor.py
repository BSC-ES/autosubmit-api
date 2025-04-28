#!/usr/bin/env python

# Copyright 2015 Earth Sciences Department, BSC-CNS

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


import pydotplus as pydotplus
import copy


from autosubmit_api.common.utils import Status
from bscearth.utils.log import Log

# from diagram import create_bar_diagram


class Monitor:
    """Class to handle monitoring of Jobs at HPC."""

    _table = dict(
        [
            (Status.UNKNOWN, "white"),
            (Status.WAITING, "#aaaaaa"),
            (Status.READY, "lightblue"),
            (Status.PREPARED, "lightsalmon"),
            (Status.SUBMITTED, "cyan"),
            (Status.HELD, "salmon"),
            (Status.QUEUING, "lightpink"),
            (Status.RUNNING, "green"),
            (Status.COMPLETED, "yellow"),
            (Status.FAILED, "red"),
            (Status.SUSPENDED, "orange"),
            (Status.SKIPPED, "lightyellow"),
            (Status.DELAYED, "lightcyan"),
        ]
    )

    @staticmethod
    def color_status(status):
        """
        Return color associated to given status

        :param status: status
        :type status: Status
        :return: color
        :rtype: str
        """
        if status == Status.WAITING:
            return Monitor._table[Status.WAITING]
        elif status == Status.READY:
            return Monitor._table[Status.READY]
        elif status == Status.PREPARED:
            return Monitor._table[Status.PREPARED]
        elif status == Status.SUBMITTED:
            return Monitor._table[Status.SUBMITTED]
        elif status == Status.HELD:
            return Monitor._table[Status.HELD]
        elif status == Status.QUEUING:
            return Monitor._table[Status.QUEUING]
        elif status == Status.RUNNING:
            return Monitor._table[Status.RUNNING]
        elif status == Status.COMPLETED:
            return Monitor._table[Status.COMPLETED]
        elif status == Status.SKIPPED:
            return Monitor._table[Status.SKIPPED]
        elif status == Status.FAILED:
            return Monitor._table[Status.FAILED]
        elif status == Status.SUSPENDED:
            return Monitor._table[Status.SUSPENDED]
        elif status == Status.DELAYED:
            return Monitor._table[Status.DELAYED]
        else:
            return Monitor._table[Status.UNKNOWN]

    def create_tree_list(self, expid, joblist, packages, groups, hide_groups=False, job_dictionary=None):
        """
        Create graph from joblist

        :param expid: experiment's identifier
        :type expid: str
        :param joblist: joblist to plot
        :type joblist: JobList
        :return: created graph
        :rtype: pydotplus.Dot
        """
        Log.debug('Creating workflow graph...')
        graph = pydotplus.Dot(graph_type='digraph')

        exp = pydotplus.Subgraph(
            graph_name='Experiment', label=expid, name="maingroup")
        self.nodes_ploted = set()
        Log.debug('Creating job graph...')

        jobs_packages_dict = dict()
        if packages is not None and packages:
            for (exp_id, package_name, job_name) in packages:
                jobs_packages_dict[job_name] = package_name

        # packages_subgraphs_dict = dict()
        date_member_cluster = dict()
        # print("Iteration joblist: ")
        for job in joblist:
            if job.date is not None and job.member is not None and job.has_parents():
                date_member_cluster[job.name] = str(
                    str(job.name[0:13]) + str(job.member))
                # date_member_cluster[(job.long_name[0:13], job.member)].append(job.name)
            # print(job)
            # print(job.has_parents())
            if job.has_parents():
                continue

            if not groups or job.name not in groups['jobs'] or (job.name in groups['jobs'] and len(groups['jobs'][job.name]) == 1):
                node_job = pydotplus.Node(job.name, shape='box', style="filled",
                                          fillcolor=self.color_status(job.status))

                if groups and job.name in groups['jobs']:
                    group = groups['jobs'][job.name][0]
                    node_job.obj_dict['name'] = group
                    node_job.obj_dict['attributes']['fillcolor'] = self.color_status(
                        groups['status'][group])
                    node_job.obj_dict['attributes']['status'] = groups['status'][group]
                    node_job.obj_dict['attributes']['shape'] = 'box3d'

                exp.add_node(node_job)
                self._add_children(job, exp, node_job, groups, hide_groups, job_dictionary)

        if groups:
            #print("In groups.")
            if not hide_groups:
                # print("Not hide groups.")
                for job, group in list(groups['jobs'].items()):
                    #print("Length of group: " + str(len(group)))
                    if len(group) > 1:
                        group_name = 'cluster_' + '_'.join(group)
                        #print("Group name: " + group_name)
                        if group_name not in graph.obj_dict['subgraphs']:
                            subgraph = pydotplus.Cluster(
                                graph_name='_'.join(group))
                            subgraph.obj_dict['attributes']['color'] = 'invis'
                        else:
                            subgraph = graph.get_subgraph(group_name)[0]

                        previous_node = exp.get_node(group[0])[0]
                        #print("Previous Node: " + previous_node)
                        if len(subgraph.get_node(group[0])) == 0:
                            subgraph.add_node(previous_node)

                        for i in range(1, len(group)):
                            node = exp.get_node(group[i])[0]
                            if len(subgraph.get_node(group[i])) == 0:
                                subgraph.add_node(node)

                            edge = subgraph.get_edge(
                                node.obj_dict['name'], previous_node.obj_dict['name'])
                            if len(edge) == 0:
                                edge = pydotplus.Edge(previous_node, node)
                                edge.obj_dict['attributes']['dir'] = 'none'
                                # constraint false allows the horizontal alignment
                                edge.obj_dict['attributes']['constraint'] = 'false'
                                edge.obj_dict['attributes']['penwidth'] = 4
                                subgraph.add_edge(edge)

                            previous_node = node
                        if group_name not in graph.obj_dict['subgraphs']:
                            graph.add_subgraph(subgraph)
            else:
                for edge in copy.deepcopy(exp.obj_dict['edges']):
                    if edge[0].replace('"', '') in groups['status']:
                        del exp.obj_dict['edges'][edge]

            graph.set_strict(True)

        graph.add_subgraph(exp)

        Log.debug('Graph definition finalized')
        return graph

    def _add_children(self, job, exp, node_job, groups, hide_groups, job_dictionary=None):
        if job in self.nodes_ploted:
            return
        self.nodes_ploted.add(job)
        if job.has_children() != 0:
            children_list = []
            if job_dictionary:
                children_list = sorted([job_dictionary[job_name] for job_name in job.children_names], key=lambda k: k.name)
            else:
                children_list = sorted(job.children, key=lambda k: k.name)
            for child in children_list:
                node_child, skip = self._check_node_exists(
                    exp, child, groups, hide_groups)
                if len(node_child) == 0 and not skip:
                    node_child = self._create_node(child, groups, hide_groups)
                    if node_child:
                        exp.add_node(node_child)
                        exp.add_edge(pydotplus.Edge(node_job, node_child))
                    else:
                        skip = True
                elif not skip:
                    node_child = node_child[0]
                    exp.add_edge(pydotplus.Edge(node_job, node_child))
                    skip = True
                if not skip:
                    self._add_children(
                        child, exp, node_child, groups, hide_groups, job_dictionary)

    def _check_node_exists(self, exp, job, groups, hide_groups):
        skip = False
        if groups and job.name in groups['jobs']:
            group = groups['jobs'][job.name][0]
            node = exp.get_node(group)
            if len(groups['jobs'][job.name]) > 1 or hide_groups:
                skip = True
        else:
            node = exp.get_node(job.name)

        return node, skip

    def _create_node(self, job, groups, hide_groups):
        node = None

        if groups and job.name in groups['jobs'] and len(groups['jobs'][job.name]) == 1:
            if not hide_groups:
                group = groups['jobs'][job.name][0]
                node = pydotplus.Node(group, shape='box3d', style="filled",
                                      fillcolor=self.color_status(groups['status'][group]))
                node.set_name(group.replace('"', ''))

        elif not groups or job.name not in groups['jobs']:
            node = pydotplus.Node(job.name, shape='box', style="filled",
                                  fillcolor=self.color_status(job.status))
        return node