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
import os

import time
from os import path
from os import chdir
from os import listdir
from os import remove

import pydotplus as pydotplus
import copy

import subprocess

from autosubmit_api.common.utils import Status
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.config.config_common import AutosubmitConfigResolver
from bscearth.utils.log import Log
from bscearth.utils.config_parser import ConfigParserFactory

# from diagram import create_bar_diagram


class Monitor:
    """Class to handle monitoring of Jobs at HPC."""
    _table = dict([(Status.UNKNOWN, 'white'), (Status.WAITING, '#aaaaaa'), (Status.READY, 'lightblue'), (Status.PREPARED, 'lightsalmon'),
                   (Status.SUBMITTED, 'cyan'), (Status.HELD,
                                                'salmon'), (Status.QUEUING, 'lightpink'), (Status.RUNNING, 'green'),
                   (Status.COMPLETED, 'yellow'), (Status.FAILED, 'red'), (Status.SUSPENDED, 'orange'), (Status.SKIPPED, 'lightyellow')])

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
        elif status == Status.QUEUING:
            return Monitor._table[Status.QUEUING]
        elif status == Status.RUNNING:
            return Monitor._table[Status.RUNNING]
        elif status == Status.COMPLETED:
            return Monitor._table[Status.COMPLETED]
        elif status == Status.HELD:
            return Monitor._table[Status.HELD]
        elif status == Status.FAILED:
            return Monitor._table[Status.FAILED]
        elif status == Status.SUSPENDED:
            return Monitor._table[Status.SUSPENDED]
        elif status == Status.SKIPPED:
            return Monitor._table[Status.SKIPPED]
        else:
            return Monitor._table[Status.UNKNOWN]

    def simplified_tree(self, expid, list_of_jobs):
        """
        Create a graph from list of jobs.
        Simplified version of create_tree_list
        """
        graph = pydotplus.Dot(graph_type="digraph")
        already_in = list()
        # Add all nodes
        for job in list_of_jobs:
            if job.name not in already_in:
                already_in.append(job.name)
                node_job = pydotplus.Node(job.name, shape='box', style="filled",
                                          fillcolor=self.color_status(job.status))
                graph.add_node(node_job)
            else:
                print("Repetition Node")

        already_in_edge = list()
        # Add all edges
        for job in list_of_jobs:
            children = job._children
            for child in job._children:
                if (job.name, child.name) not in already_in_edge:
                    already_in_edge.append((job.name, child.name))
                    graph.add_edge(pydotplus.Edge(job.name, child.name))
                else:
                    print("Repetition Edge")
        return graph

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
        if packages != None and packages:
            for (exp_id, package_name, job_name) in packages:
                jobs_packages_dict[job_name] = package_name

        packages_subgraphs_dict = dict()
        date_member_cluster = dict()
        # print("Iteration joblist: ")
        for job in joblist:
            if job.date != None and job.member != None and job.has_parents():
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

    def generate_output(self, expid, joblist, path, output_format="pdf", packages=None, show=False, groups=dict(), hide_groups=False):
        """
        Plots graph for joblist and stores it in a file

        :param expid: experiment's identifier
        :type expid: str
        :param joblist: joblist to plot
        :type joblist: JobList
        :param output_format: file format for plot
        :type output_format: str (png, pdf, ps)
        :param show: if true, will open the new plot with the default viewer
        :type show: bool
        """
        Log.info('Plotting...')
        now = time.localtime()
        output_date = time.strftime("%Y%m%d_%H%M", now)
        output_file = os.path.join(APIBasicConfig.LOCAL_ROOT_DIR, expid, "plot", expid + "_" + output_date + "." +
                                   output_format)
        # print(expid)
        # print(len(joblist))
        # print("Packages")
        # print(packages)
        # print("Groups")
        # print(groups)
        # print(hide_groups)
        graph = self.create_tree_list(
            expid, joblist, packages, groups, hide_groups)
        # print(graph)
        # for u in exp.get_node_list():
        #     print(u)

        # for v in exp.get_edge_list():
        #     print(str(v.get_source()) + " to " + str(v.get_destination()))
        return False
        # print(graph.source)
        # for u in graph.get_edge_list():
        #     print(u)
        # for v in graph[u]:
        #     print(v)

        Log.debug("Saving workflow plot at '{0}'", output_file)
        if output_format == "png":
            # noinspection PyUnresolvedReferences
            graph.write_png(output_file)
        elif output_format == "pdf":
            # noinspection PyUnresolvedReferences
            graph.write_pdf(output_file)
            # result = graph.create('dot', format="plain")
            # for u in result.split("\n"):
            #     splitList = u.split(" ")
            #     if len(splitList) > 1 and splitList[0] == "node":
            #         print(splitList[0] + " " + splitList[1] + " x:" + splitList[2] + " y:" + splitList[3])

            # result = graph.create(format="plain")
            # for u in result.split("\n"):
            #     # print(u)
            #     splitList = u.split(" ")
            #     # print(splitList)
            #     if len(splitList) > 1 and splitList[0] == "node":
            #         print(splitList[0] + " " + splitList[1] + " x:" + splitList[2] + " y:" + splitList[3])

        elif output_format == "ps":
            # noinspection PyUnresolvedReferences
            graph.write_ps(output_file)
        elif output_format == "svg":
            # noinspection PyUnresolvedReferences
            graph.write_svg(output_file)
        else:
            Log.error('Format {0} not supported', output_format)
            return
        Log.result('Plot created at {0}', output_file)
        if show:
            try:
                subprocess.check_call(['xdg-open', output_file])
            except subprocess.CalledProcessError:
                Log.error('File {0} could not be opened', output_file)

        self.generate_output_txt(expid, joblist, path, "default")

    def generate_output_txt(self, expid, joblist, path, classictxt=False):
        Log.info('Writing status txt...')

        now = time.localtime()
        output_date = time.strftime("%Y%m%d_%H%M", now)
        file_path = os.path.join(
            APIBasicConfig.LOCAL_ROOT_DIR, expid, "status", expid + "_" + output_date + ".txt")

        if not os.path.exists(os.path.dirname(file_path)):
            os.makedirs(os.path.dirname(file_path))

        output_file = open(file_path, 'w+')
        if classictxt:
            for job in joblist:
                log_out = ""
                log_err = ""
                if job.status in [Status.FAILED, Status.COMPLETED]:
                    log_out = path + "/" + job.local_logs[0]
                    log_err = path + "/" + job.local_logs[1]

                output = job.name + " " + \
                    Status().VALUE_TO_KEY[job.status] + \
                    " " + log_out + " " + log_err + "\n"
                output_file.write(output)
        else:
            output_file.write(
                "Writing jobs, they're grouped by [FC and DATE] \n")
            self.write_output_txt_recursive(
                joblist[0], output_file, "", file_path)
            output_file.close()
        Log.result('Status txt created at {0}', output_file)

    def write_output_txt_recursive(self, job, output_file, level, path):
        log_out = ""
        log_err = ""
        # if job.status in [Status.FAILED, Status.COMPLETED]:
        #    log_out = path + "/" + job.local_logs[0]
        #    log_err = path + "/" + job.local_logs[1]
        # + " " + log_out + " " + log_err + "\n"
        output = level + job.name + " " + \
            Status().VALUE_TO_KEY[job.status] + "\n"
        output_file.write(output)
        if job.has_children() > 0:
            for child in job.children:
                self.write_output_txt_recursive(
                    child, output_file, "_" + level, path)

    def generate_output_stats(self, expid, joblist, output_format="pdf", period_ini=None, period_fi=None, show=False):
        """
        Plots stats for joblist and stores it in a file

        :param expid: experiment's identifier
        :type expid: str
        :param joblist: joblist to plot
        :type joblist: JobList
        :param output_format: file format for plot
        :type output_format: str (png, pdf, ps)
        :param period_ini: initial datetime of filtered period
        :type period_ini: datetime
        :param period_fi: final datetime of filtered period
        :type period_fi: datetime
        :param show: if true, will open the new plot with the default viewer
        :type show: bool
        """
        Log.info('Creating stats file')
        now = time.localtime()
        output_date = time.strftime("%Y%m%d_%H%M", now)

        directory = os.path.join(APIBasicConfig.LOCAL_ROOT_DIR, expid, "stats")
        if not os.path.exists(directory):
            os.makedirs(directory)

        output_file = os.path.join(APIBasicConfig.LOCAL_ROOT_DIR, expid, "stats", expid + "_statistics_" + output_date +
                                   "." + output_format)

        # create_bar_diagram(expid, joblist, self.get_general_stats(expid), output_file, period_ini, period_fi)
        Log.result('Stats created at {0}', output_file)
        if show:
            try:
                subprocess.check_call(['xdg-open', output_file])
            except subprocess.CalledProcessError:
                Log.error('File {0} could not be opened', output_file)

    @staticmethod
    def clean_plot(expid):
        """
        Function to clean space on BasicConfig.LOCAL_ROOT_DIR/plot directory.
        Removes all plots except last two.

        :param expid: experiment's identifier
        :type expid: str
        """
        search_dir = os.path.join(APIBasicConfig.LOCAL_ROOT_DIR, expid, "plot")
        chdir(search_dir)
        files = list(filter(path.isfile, listdir(search_dir)))
        files = [path.join(search_dir, f)
                 for f in files if 'statistics' not in f]
        files.sort(key=lambda x: path.getmtime(x))
        remain = files[-2:]
        filelist = [f for f in files if f not in remain]
        for f in filelist:
            remove(f)
        Log.result("Plots cleaned!\nLast two plots remanining there.\n")

    @staticmethod
    def clean_stats(expid):
        """
        Function to clean space on BasicConfig.LOCAL_ROOT_DIR/plot directory.
        Removes all stats' plots except last two.

        :param expid: experiment's identifier
        :type expid: str
        """
        search_dir = os.path.join(APIBasicConfig.LOCAL_ROOT_DIR, expid, "plot")
        chdir(search_dir)
        files = list(filter(path.isfile, listdir(search_dir)))
        files = [path.join(search_dir, f) for f in files if 'statistics' in f]
        files.sort(key=lambda x: path.getmtime(x))
        remain = files[-1:]
        filelist = [f for f in files if f not in remain]
        for f in filelist:
            remove(f)
        Log.result("Stats cleaned!\nLast stats' plot remanining there.\n")

    @staticmethod
    def get_general_stats(expid):
        general_stats = []
        general_stats_path = os.path.join(
            APIBasicConfig.LOCAL_ROOT_DIR, expid, "tmp", expid + "_GENERAL_STATS")
        parser = AutosubmitConfigResolver.get_parser(
            ConfigParserFactory(), general_stats_path)
        for section in parser.sections():
            general_stats.append((section, ''))
            general_stats += parser.items(section)
        return general_stats
