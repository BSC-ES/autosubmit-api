#!/usr/bin/env python

import unittest
import math

from networkx.algorithms.distance_measures import center
from autosubmit_api.common.utils import Status
from autosubmit_api.components.representations.graph.graph import GraphRepresentation, GroupedBy, Layout
from autosubmit_api.components.representations.graph.edge import RealEdge
from autosubmit_api.builders.joblist_loader_builder import JobListLoaderBuilder, JobListLoaderDirector
from collections import Counter

class TestGraph(unittest.TestCase):
  def setUp(self):
    loader = JobListLoaderDirector(JobListLoaderBuilder("a29z")).build_loaded_joblist_loader()
    self.test_graph = GraphRepresentation("a29z", loader, Layout.STANDARD)           
  
  def tearDown(self):
    del self.test_graph
  
  def test_add_normal_edges(self):
    loader = JobListLoaderDirector(JobListLoaderBuilder("a0yh")).build_loaded_joblist_loader()
    graph = GraphRepresentation("a0yh", loader, Layout.STANDARD)    
    self.assertTrue(graph.job_count > 0)
    graph.add_normal_edges()     
    edge_count = 0
    for job in graph.jobs:
      edge_count += len(job.children_names)
    # print("Edge count: {}".format(edge_count))
    self.assertTrue(graph.edge_count == edge_count)
    edge_names = [edge._id for edge in graph.edges]
    counts = dict(Counter(edge_names))
    duplicates = {key:value for key, value in counts.items() if value > 1}
    self.assertTrue(len(duplicates) == 0)
    #print(duplicates)

  def test_level_update(self):    
    self.assertTrue(len(self.test_graph.jobs) > 0)
    self.test_graph.add_normal_edges() 
    self.test_graph.update_jobs_level()
    for job in self.test_graph.jobs:
      self.assertTrue((job.level > 0 and job.level <= 20)) # a29z test case

  def test_graphviz_coordinates(self):    
    self.assertTrue(len(self.test_graph.jobs) > 0)
    self.test_graph.add_normal_edges() 
    self.test_graph.reset_jobs_coordinates()
    self.test_graph.assign_graphviz_coordinates_to_jobs()    
    for job in self.test_graph.jobs:      
      # print("X: {}, Y: {}".format(job.x_coordinate, job.y_coordinate))
      self.assertTrue(job.x_coordinate != 0 or job.y_coordinate != 0)

  def test_graphviz_generated_coordinates(self):
    self.assertTrue(self.test_graph.job_count > 0)
    self.test_graph.add_normal_edges()
    self.test_graph.reset_jobs_coordinates()
    self.assertTrue(self.test_graph.edge_count > 0)
    self.test_graph.assign_graphviz_calculated_coordinates_to_jobs()
    for job in self.test_graph.jobs:
      self.assertTrue(job.x_coordinate != 0 or job.y_coordinate != 0)

      
  def test_laplacian_coordinates(self): 
    self.test_graph.add_normal_edges()    
    self.assertTrue(self.test_graph.job_count > 0)
    self.assertTrue(len(self.test_graph.job_dictionary) > 0)
    self.assertTrue(self.test_graph.edge_count > 0)
    self.test_graph.reset_jobs_coordinates()
    self.test_graph.assign_laplacian_coordinates_to_jobs()
    center_count = 0
    for job in self.test_graph.jobs:
      # print("{} -> X: {}, Y: {}".format(job.name, job.x_coordinate, job.y_coordinate))
      if job.x_coordinate == 0 and job.y_coordinate == 0:
        center_count += 1
      else:
        self.assertTrue(job.x_coordinate != 0  or job.y_coordinate != 0)
    self.assertTrue(center_count <= math.ceil(self.test_graph.job_count/2))

  def test_barycentric_coordinates(self):    
    self.test_graph.add_normal_edges() 
    self.assertTrue(self.test_graph.job_count > 0)
    self.assertTrue(len(self.test_graph.job_dictionary) > 0)
    self.assertTrue(self.test_graph.edge_count > 0)
    self.test_graph.reset_jobs_coordinates()
    self.test_graph.update_jobs_level()
    self.test_graph.assign_barycentric_coordinates_to_jobs()
    unique_coordinates = set()
    for job in self.test_graph.jobs:      
      # print("{} -> X: {}, Y: {}".format(job.name, job.x_coordinate, job.y_coordinate))
      self.assertTrue(job.x_coordinate > 0  or job.y_coordinate > 0)
      self.assertTrue((job.x_coordinate, job.y_coordinate) not in unique_coordinates)
      unique_coordinates.add((job.x_coordinate, job.y_coordinate))

  def test_wrong_layout(self):
    with self.assertRaises(ValueError):
      loader = JobListLoaderDirector(JobListLoaderBuilder("a29z")).build_loaded_joblist_loader()
      graph = GraphRepresentation("a29z", loader, "otherlayout")
      graph.perform_calculations()
  
  def test_calculate_average_post_time(self):
    loader = JobListLoaderDirector(JobListLoaderBuilder("a29z")).build_loaded_joblist_loader()
    graph = GraphRepresentation("a29z", loader, Layout.STANDARD)
    graph._calculate_average_post_time()
    print("\nAverage post time: {}".format(graph.average_post_time))
    self.assertTrue(graph.average_post_time > 0)

  def test_generate_node_date(self):
    self.test_graph.perform_calculations()    
    self.assertTrue(len(self.test_graph.nodes) > 0)
    for node in self.test_graph.nodes:
      self.assertTrue(len(node["status"]) > 0)
      self.assertTrue(len(node["label"]) > 0)
      self.assertTrue(len(node["platform_name"]) > 0)
      self.assertTrue(int(node["level"]) > 0)
      if node["status_code"] == Status.COMPLETED:
        self.assertTrue(int(node["minutes"]) > 0)
    self.assertTrue(self.test_graph.max_children_count > 0)
    self.assertTrue(self.test_graph.max_parent_count > 0)

  def test_grouped_by_date_member_dict(self):
    loader = JobListLoaderDirector(JobListLoaderBuilder("a29z")).build_loaded_joblist_loader()
    graph = GraphRepresentation("a29z", loader, Layout.STANDARD, GroupedBy.DATE_MEMBER)
    graph.perform_calculations()
    groups = graph._get_grouped_by_date_member_dict()
    self.assertTrue(len(groups) > 0)
    date_count = len(graph.joblist_loader.dates)
    member_count = len(graph.joblist_loader.members)
    self.assertTrue(len(groups) == int(date_count*member_count))
  
  def test_grouped_by_status(self):
    loader = JobListLoaderDirector(JobListLoaderBuilder("a29z")).build_loaded_joblist_loader()
    graph = GraphRepresentation("a29z", loader, Layout.STANDARD, GroupedBy.STATUS)
    graph.perform_calculations()
    groups = graph._get_grouped_by_status_dict()
    self.assertTrue(len(groups) > 0)

  def test_grouped_by_wrong_parameter(self):
    loader = JobListLoaderDirector(JobListLoaderBuilder("a29z")).build_loaded_joblist_loader()
    graph = GraphRepresentation("a29z", loader, Layout.STANDARD, "NONE")
    with self.assertRaises(ValueError):
      graph.perform_calculations()
  
  def test_perform_calculations(self):
    self.test_graph.perform_calculations()
    edge_count = 0
    for job in self.test_graph.jobs:
      edge_count += len(job.children_names)
      if job.status == Status.COMPLETED:
        self.assertTrue(job.out_path_local.startswith("/esarchive/"))
        self.assertTrue(job.err_path_local.startswith("/esarchive/"))
    self.assertTrue(self.test_graph.edge_count == edge_count)

  def test_specific_graph(self):
    loader = JobListLoaderDirector(JobListLoaderBuilder("a44k")).build_loaded_joblist_loader()
    graph = GraphRepresentation("a44k", loader, Layout.STANDARD)
    graph.perform_calculations()
    self.assertTrue(graph is not None)

if __name__ == '__main__':
  unittest.main()


  