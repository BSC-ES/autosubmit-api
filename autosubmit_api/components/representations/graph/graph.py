#!/usr/bin/env python

import networkx as nx
from autosubmit_api.builders.experiment_history_builder import ExperimentHistoryBuilder, ExperimentHistoryDirector
from autosubmit_api.performance import utils as PUtils
# import common.utils as utils
from autosubmit_api.common.utils import Status, get_average_total_time
from autosubmit_api.components.jobs.job_factory import Job
from autosubmit_api.components.jobs.joblist_loader import JobListLoader
from autosubmit_api.monitor.monitor import Monitor
from autosubmit_api.database.db_jobdata import ExperimentGraphDrawing

from autosubmit_api.components.representations.graph.edge import Edge, RealEdge
from typing import List, Dict, Optional, Tuple, Any
from scipy.sparse import linalg

GRAPHVIZ_MULTIPLIER = 90
SMALL_EXPERIMENT_THRESHOLD = 1000
BARYCENTRIC_X_MULTIPLIER = 320
BARYCENTRIC_Y_MULTIPLIER = 150

class Layout:
  STANDARD = "standard"
  LAPLACIAN = "laplacian"

class GroupedBy:
  STATUS = "status"
  DATE_MEMBER = "date-member"
  NO_GROUP = "none"

class GraphRepresentation(object):
  """ Graph Representation of Experiment """
  def __init__(self, expid: str, job_list_loader: JobListLoader, layout: str, grouped: str = GroupedBy.NO_GROUP):
    self.expid = expid
    self.layout = layout
    self.grouped_by = grouped
    self.joblist_loader = job_list_loader
    self.joblist_helper = self.joblist_loader.joblist_helper
    self.jobs = self.joblist_loader.jobs
    self.job_dictionary = self.joblist_loader.job_dictionary
    self.average_post_time: float = 0.0
    self.we_have_valid_graph_drawing: bool = False
    self.we_have_valid_graphviz_drawing: bool = False
    self.edges: List[Edge] = []
    self.package_edges: List[Edge] = []
    self.nodes: List[Dict[str, Any]] = []
    self.groups: Dict[str, Dict[str, Any]] = {}
    self.max_children_count: int = 0
    self.max_parent_count: int = 0

  @property
  def job_count(self):
    return len(self.jobs)

  @property
  def edge_count(self):
    return len(self.edges)

  def perform_calculations(self):
    """ Calculate Graph Representation """
    self.joblist_loader.validate_job_list_configuration()
    self.add_normal_edges()
    self.calculate_valid_drawing()
    self._calculate_average_post_time()
    self._generate_node_data()
    self._calculate_groups()

  def get_graph_representation_data(self):
    return {'nodes': self.nodes,
            'edges': [edge.get_as_json() for edge in self.edges],
            'packages': self.joblist_helper.package_to_jobs,
            'fake_edges': [],
            'groups': list(self.groups.keys()),
            'groups_data': self.groups,
            'graphviz': self.we_have_valid_graphviz_drawing,
            'max_children': self.max_children_count,
            'max_parents': self.max_parent_count,
            'chunk_unit': self.joblist_loader.chunk_unit,
            'chunk_size': self.joblist_loader.chunk_size,
            'total_jobs': self.job_count,
            "error": False,
            "error_message": "",
            "pkl_timestamp": 10000000}

  def calculate_valid_drawing(self):
    self.update_jobs_level()
    if self.layout == Layout.STANDARD:
      self.assign_graphviz_coordinates_to_jobs()
    elif self.layout == Layout.LAPLACIAN:
      self.assign_laplacian_coordinates_to_jobs()
    else:
      raise ValueError("You have requested a {0} layout, which is not implemented.".format(self.layout))
    if not self.we_have_valid_graph_drawing:
      self.assign_barycentric_coordinates_to_jobs()

  def _calculate_groups(self):
    if self.grouped_by == GroupedBy.STATUS:
      self.groups = self._get_grouped_by_status_dict()
    elif self.grouped_by == GroupedBy.DATE_MEMBER:
      self.groups = self._get_grouped_by_date_member_dict()
    elif self.grouped_by == GroupedBy.NO_GROUP:
      self.groups = dict()
    else:
      raise ValueError("You have provided an invalid grouping selection: {}".format(self.grouped_by))

  def _get_grouped_by_status_dict(self) -> Dict[str, Dict[str, Any]]:
    groups = {}
    groups['WAITING'] = {"color": Monitor.color_status(Status.WAITING)}
    groups['COMPLETED'] = {"color": Monitor.color_status(Status.COMPLETED)}
    groups['SUSPENDED'] = {"color": Monitor.color_status(Status.SUSPENDED)}
    return groups

  def _get_grouped_by_date_member_dict(self) -> Dict[str, Dict[str, Any]]:
    if len(self.joblist_loader.dates) == 0 or len(self.joblist_loader.members) == 0:
      raise Exception("This experiment doesn't admit grouping by date and member because there are {} dates and {} members.".format(
                      len(self.joblist_loader.dates), len(self.joblist_loader.members)))
    groups = {}
    group_color = {}
    group_coordinates = list()
    for date in self.joblist_loader.dates:
      formatted_date = self.joblist_loader.dates_formatted_dict.get(date, None)
      for member in self.joblist_loader.members:
        status_counters = {}
        group_name = "{}_{}_{}_".format(self.expid, formatted_date, member)
        jobs_in_date_member = [x for x in self.jobs if x.name.startswith(group_name)]
        if len(jobs_in_date_member) == 0:
          raise Exception("You have configured date {} and member {} in your experiment but there are no jobs that use these settings. \
          Review your configuration, something might be wrong.".format(formatted_date, member))
        for job in jobs_in_date_member:
          status_counters[job.status] = status_counters.setdefault(job.status, 0) + 1
        group_color[group_name] = self._get_defined_group_color(status_counters)
        group_coordinates.append((group_name,
                              int(sum(job.x_coordinate for job in jobs_in_date_member)/len(jobs_in_date_member)),
                              int(sum(job.y_coordinate for job in jobs_in_date_member)/len(jobs_in_date_member))))
    non_collision_group_coordinates = self._solve_group_collisions(group_coordinates)
    for group_name in group_color:
      x, y = non_collision_group_coordinates[group_name]
      groups[group_name] = { "color": group_color[group_name], "x": x, "y": y }
    return groups


  def _solve_group_collisions(self, group_coordinates: List[Tuple[str, int, int]]) -> Dict[str, Tuple[int, int]]:
    group_coordinates.sort(key=lambda group_triple: group_triple[2], reverse=True)
    new_group_coordinates = dict()
    visited = set()
    for group_triple in group_coordinates:
      group_name, x_i_coordinate, y_i_coordinate = group_triple
      visited.add(group_name)
      for group_triple_compared in group_coordinates:
        group_name_compared, x_j_coordinate, y_j_coordinate = group_triple_compared
        if group_name_compared not in visited:
          if abs(x_i_coordinate - x_j_coordinate) <= 250 and abs(y_i_coordinate - y_j_coordinate) <= 250:
            if y_i_coordinate > y_j_coordinate:
                y_i_coordinate = y_i_coordinate + (250 - abs(y_i_coordinate - y_j_coordinate))
            else:
                y_i_coordinate = y_i_coordinate - (250 - abs(y_i_coordinate - y_j_coordinate))
      new_group_coordinates[group_name] =  (x_i_coordinate, y_i_coordinate)
    return new_group_coordinates

  def _get_defined_group_color(self, status_counters: Dict[int, int]) -> str:
    if status_counters.get(Status.FAILED, 0) > 0:
      return Monitor.color_status(Status.FAILED)
    elif status_counters.get(Status.RUNNING, 0) > 0:
      return Monitor.color_status(Status.RUNNING)
    elif status_counters.get(Status.SUSPENDED, 0) > 0:
      return Monitor.color_status(Status.SUSPENDED)
    elif status_counters.get(Status.SUBMITTED, 0) > 0:
      return Monitor.color_status(Status.SUBMITTED)
    elif status_counters.get(Status.QUEUING, 0) > 0:
      return Monitor.color_status(Status.QUEUING)
    elif status_counters.get(Status.COMPLETED, 0) > 0:
      return Monitor.color_status(Status.COMPLETED)
    else:
      return Monitor.color_status(Status.WAITING)

  def assign_graphviz_coordinates_to_jobs(self):
    """ Gets from database or calculates the coordinates if experiment is small #jobs <= 1000 """
    self.we_have_valid_graph_drawing = self._assign_coordinates_to_jobs(self._get_graph_drawing_data())
    self.we_have_valid_graphviz_drawing = self.we_have_valid_graph_drawing
    if not self.we_have_valid_graph_drawing and len(self.jobs) <= SMALL_EXPERIMENT_THRESHOLD:
      self.assign_graphviz_calculated_coordinates_to_jobs()

  def assign_graphviz_calculated_coordinates_to_jobs(self):
    """ Runs GraphViz to get the coordinates """
    self.we_have_valid_graph_drawing = self._assign_coordinates_to_jobs(self._get_calculated_graph_drawing())
    self.we_have_valid_graphviz_drawing = self.we_have_valid_graph_drawing

  def assign_laplacian_coordinates_to_jobs(self):
    """ Calculates Laplacian """
    self.we_have_valid_graph_drawing = self._assign_coordinates_to_jobs(self._get_calculated_graph_laplacian_drawing())
    self.we_have_valid_graphviz_drawing = False

  def assign_barycentric_coordinates_to_jobs(self):
    """ Calculates coordinates """
    self.we_have_valid_graph_drawing = self._assign_coordinates_to_jobs(self._get_calculated_hierarchical_drawing())
    self.we_have_valid_graphviz_drawing = False

  def update_jobs_level(self):
    def update_level(parent_job: Job):
      stack.append(parent_job)
      while stack:
        current = stack.pop()
        current.level += 1
        for children_job_name in current.children_names:
          if self.job_dictionary[children_job_name].level == 0:
            self.job_dictionary[children_job_name].level = current.level
            stack.append(self.job_dictionary[children_job_name])

    job_roots_names = [job.name for job in self.jobs if len(job.parents_names) == 0]
    for job_name in job_roots_names:
      stack = []
      update_level(self.job_dictionary[job_name])

  def reset_jobs_coordinates(self):
    """ Mainly for testing purposes """
    for job in self.jobs:
      job.x_coordinate, job.y_coordinate = (0, 0)

  def add_normal_edges(self):
    for job in self.jobs:
      for child_name in job.children_names:
        if job.name != child_name:
          self.edges.append(RealEdge(job.name, child_name, self.joblist_loader.are_these_in_same_package(job.name, child_name)))

  def _calculate_average_post_time(self):
    post_jobs = [job for job in self.jobs if job.section == "POST" and job.status in {Status.COMPLETED}]
    self.average_post_time = get_average_total_time(post_jobs)

  def _generate_node_data(self):
    # Get last run data for each job
    try:
      experiment_history = ExperimentHistoryDirector(ExperimentHistoryBuilder(self.expid)).build_reader_experiment_history()
      last_jobs_run = experiment_history.get_all_jobs_last_run_dict()
    except Exception:
      last_jobs_run = {}

    # Generate node data
    for job_name in self.job_dictionary:
      job = self.job_dictionary[job_name]
      self._calculate_max_children_parent(len(job.children_names), len(job.parents_names))

      # Get chunk size and unit
      chunk_size = self.joblist_loader.chunk_size
      chunk_unit = self.joblist_loader.chunk_unit
      last_run = last_jobs_run.get(job_name)
      if last_run and last_run.chunk_unit and last_run.chunk_size:
        chunk_unit, chunk_size = last_run.chunk_unit, last_run.chunk_size

      # Calculate dates
      ini_date, end_date = job.get_date_ini_end(chunk_size, chunk_unit)

      # Calculate performance metrics
      SYPD = PUtils.calculate_SYPD_perjob(chunk_unit, chunk_size, job.chunk, job.run_time, job.status)
      ASYPD = PUtils.calculate_ASYPD_perjob(chunk_unit, chunk_size, job.chunk, job.total_time, self.average_post_time, job.status)

      self.nodes.append({
        "id": job.name,
        "internal_id": job.name,
        "label": job.name,
        "status": job.status_text,
        "status_code": job.status,
        "status_color": job.status_color,
        "platform_name": job.platform,
        "chunk": job.chunk,
        "chunk_size": chunk_size,
        "chunk_unit": chunk_unit,
        "package": job.package,
        "wrapper": job.package,
        "member": job.member,
        "date": ini_date,
        "date_plus": end_date,
        "SYPD": SYPD,
        "ASYPD": ASYPD,
        "minutes_queue": job.queue_time,
        "minutes": job.run_time,
        "submit": job.submit_datetime,
        "start": job.start_datetime,
        "finish": job.finish_datetime,
        "section": job.section,
        "queue": job.qos,
        "level": job.level,
        "dashed": True if job.package else False,
        "shape": self.joblist_helper.package_to_symbol.get(job.package, "dot"),
        "processors": job.ncpus,
        "wallclock": job.wallclock,
        "children": len(job.children_names),
        "children_list": list(job.children_names),
        "parents": len(job.parents_names),
        "parent_list": list(job.parents_names),
        "out": job.out_file_path,
        "err": job.err_file_path,
        "custom_directives": None,
        "rm_id": job.rm_id,
        "x": job.x_coordinate,
        "y": job.y_coordinate,
        "workflow_commit": job.workflow_commit,
      })

  def _calculate_max_children_parent(self, children_count: int, parent_count: int):
    self.max_children_count = max(self.max_children_count, children_count)
    self.max_parent_count = max(self.max_parent_count, parent_count)

  def _assign_coordinates_to_jobs(self, valid_coordinates: Optional[Dict[str, Tuple[int, int]]]) -> bool:
    """ False if valid_coordinates is None OR empty"""
    if valid_coordinates and len(valid_coordinates) > 0:
      for job_name in self.job_dictionary:
        self.job_dictionary[job_name].x_coordinate, self.job_dictionary[job_name].y_coordinate = valid_coordinates[job_name]
      return True
    return False

  def _get_graph_drawing_data(self) -> Optional[Dict[str, Tuple[int, int]]]:
    return ExperimentGraphDrawing(self.expid).get_validated_data(self.jobs)

  def _get_calculated_graph_drawing(self) -> Dict[str, Tuple[int, int]]:
    coordinates = dict()
    graph = Monitor().create_tree_list(self.expid, self.jobs, None, dict(), False, self.job_dictionary)
    graph_viz_result = graph.create("dot", format="plain")
    for node_data in graph_viz_result.split(b'\n'):
      node_data = node_data.split(b' ')
      if len(node_data) > 1 and node_data[0].decode() == "node":
        coordinates[str(node_data[1].decode())] = (int(float(node_data[2])) * GRAPHVIZ_MULTIPLIER, int(float(node_data[3])) * -GRAPHVIZ_MULTIPLIER)
    return coordinates

  def _get_calculated_graph_laplacian_drawing(self) -> Dict[str, Tuple[int, int]]:
    coordinates = dict()
    nx_graph = nx.Graph()
    for job_name in self.job_dictionary:
      nx_graph.add_node(job_name)
    for edge in self.edges:
      nx_graph.add_edge(edge._from, edge._to, weight=(3 if edge._is_in_wrapper else 1))
    laplacian_matrix = nx.normalized_laplacian_matrix(nx_graph)
    eigval, eigvec = linalg.eigsh(laplacian_matrix, k=4, which="SM")
    eigval1 = float(eigval[1])
    eigval2 = float(eigval[2])
    x_coords = eigvec[:, 1] * (self.job_count / eigval1) * 10.0
    y_coords = eigvec[:, 2] * (self.job_count / eigval2) * 10.0
    for i, job_name in enumerate(nx_graph.nodes):
      coordinates[job_name] = (int(x_coords[i]), int(y_coords[i]))
    return coordinates

  def _get_calculated_hierarchical_drawing(self) -> Dict[str, Tuple[int, int]]:
    coordinates = {}
    processed_packages = set()
    max_level = max(job.level for job in self.jobs)
    for i in range(2, max_level+1):
      if i == 2:
        jobs_in_previous_layer = [x for x in self.jobs if x.level == i-1]
        for k, job in enumerate(jobs_in_previous_layer):
          self.job_dictionary[job.name].horizontal_order = (k+1)

      jobs_in_layer = [x for x in self.jobs if x.level == i]
      for job in jobs_in_layer:
        sum_order = sum(self.job_dictionary[job_name].horizontal_order for job_name in job.parents_names)
        if len(job.parents_names) > 0:
          self.job_dictionary[job.name].barycentric_value = sum_order/len(job.parents_names)

      jobs_in_layer.sort(key=lambda x: x.barycentric_value)
      job_names_in_layer = {job.name for job in jobs_in_layer}
      already_assigned_order = set()
      for job in jobs_in_layer:
        if job.name not in already_assigned_order:
          self.job_dictionary[job.name].horizontal_order = len(already_assigned_order) + 1
          already_assigned_order.add(job.name)
          if job.package and (job.package, job.level) not in processed_packages:
            processed_packages.add((job.package, job.level))
            job_names_in_package_and_same_level = [job.name for job in jobs_in_layer if job.name in self.joblist_helper.package_to_jobs.get(job.package, [])]
            for job_name in job_names_in_package_and_same_level:
              if self.job_dictionary[job_name].name in job_names_in_layer and job_name not in already_assigned_order:
                self.job_dictionary[job_name].horizontal_order = len(already_assigned_order) + 1
                already_assigned_order.add(job_name)

    for job_name in self.job_dictionary:
      # print("{} {} {}".format(job_name, self.job_dictionary[job_name].horizontal_order, self.job_dictionary[job_name].level))
      coordinates[job_name] = (int(self.job_dictionary[job_name].horizontal_order*BARYCENTRIC_X_MULTIPLIER), int(self.job_dictionary[job_name].level*BARYCENTRIC_Y_MULTIPLIER))
    return coordinates



  # We are no long adding fake edges for packages
  # def add_package_edges(self):
  #   for package in self.joblist_helper.package_to_jobs:
  #     pairs = set()
  #     for job_name_from in self.joblist_helper.package_to_jobs[package]:
  #       for job_name_to in self.joblist_helper.package_to_jobs[package]:
