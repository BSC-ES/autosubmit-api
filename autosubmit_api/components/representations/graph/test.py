#!/usr/bin/env python

import unittest
import math
import autosubmit_api.common.utils_for_testing  as TestUtils

from autosubmit_api.common.utils import Status
from autosubmit_api.components.representations.graph.graph import GraphRepresentation, GroupedBy, Layout
from autosubmit_api.builders.joblist_loader_builder import JobListLoaderBuilder, JobListLoaderDirector
from collections import Counter

CASE_NO_WRAPPERS = "a3tb" # Job count = 55
CASE_WITH_WRAPPERS = "a28v"
class TestGraph(unittest.TestCase):
  def setUp(self):
    pass

  def tearDown(self):
    pass

  def get_loader(self, expid):
    return JobListLoaderDirector(JobListLoaderBuilder(expid)).build_loaded_joblist_loader(TestUtils.get_mock_basic_config())

  def get_standard_case_with_no_calculations(self):
    # type: () -> GraphRepresentation
    """  """
    loader = JobListLoaderDirector(JobListLoaderBuilder(CASE_NO_WRAPPERS)).build_loaded_joblist_loader(TestUtils.get_mock_basic_config())
    return GraphRepresentation(CASE_NO_WRAPPERS, loader, Layout.STANDARD)

  def get_wrapper_case_with_no_calculations(self):
    # type: () -> GraphRepresentation
    loader = JobListLoaderDirector(JobListLoaderBuilder(CASE_WITH_WRAPPERS)).build_loaded_joblist_loader(TestUtils.get_mock_basic_config())
    return GraphRepresentation(CASE_WITH_WRAPPERS, loader, Layout.STANDARD)

  def test_jobs_exist_and_equal_to_known_count(self):
    # Arrange
    sut = self.get_standard_case_with_no_calculations()
    # Act: Graph constructos gets the jobs from the loader
    # Assert
    self.assertGreater(sut.job_count, 0)
    self.assertEqual(sut.job_count, 55)

  def test_added_edges_same_as_parent_chilren_relations(self):
    # Arrange
    sut = self.get_standard_case_with_no_calculations()
    relations_count = 0
    for job in sut.jobs:
      relations_count += len(job.children_names)
    # Act
    sut.add_normal_edges()
    # Assert
    self.assertTrue(sut.edge_count == relations_count)


  def test_level_updated(self):
    # Arrange
    sut = self.get_standard_case_with_no_calculations()
    # Act
    sut.add_normal_edges()
    sut.update_jobs_level()
    # Assert
    self.assertEqual(sut.job_dictionary["a3tb_LOCAL_SETUP"].level, 1)
    self.assertEqual(sut.job_dictionary["a3tb_REMOTE_SETUP"].level, 3)
    self.assertEqual(sut.job_dictionary["a3tb_19930501_fc01_1_SAVEIC"].level, 6)

  def test_graphviz_coordinates_are_added(self):
    sut = self.get_standard_case_with_no_calculations()

    sut.add_normal_edges()
    sut.reset_jobs_coordinates()
    sut.assign_graphviz_coordinates_to_jobs()

    for job in sut.jobs:
      self.assertTrue(job.x_coordinate != 0 or job.y_coordinate != 0)

  def test_graphviz_generated_coordinates(self):
    sut = self.get_standard_case_with_no_calculations()

    sut.add_normal_edges()
    sut.reset_jobs_coordinates()
    sut.assign_graphviz_calculated_coordinates_to_jobs()

    for job in sut.jobs:
      self.assertTrue(job.x_coordinate != 0 or job.y_coordinate != 0)


  def test_laplacian_generates_coordinates(self):
    sut = self.get_standard_case_with_no_calculations()

    sut.add_normal_edges()
    sut.reset_jobs_coordinates()
    sut.assign_laplacian_coordinates_to_jobs()
    center_count = 0
    for job in sut.jobs:
      if job.x_coordinate == 0 and job.y_coordinate == 0:
        center_count += 1

    self.assertTrue(center_count <= math.ceil(sut.job_count/2))

  def test_barycentric_generates_unique_coordinates(self):
    sut = self.get_standard_case_with_no_calculations()

    sut.add_normal_edges()
    sut.reset_jobs_coordinates()
    sut.update_jobs_level()
    sut.assign_barycentric_coordinates_to_jobs()

    unique_coordinates = set()
    for job in sut.jobs:
      self.assertTrue(job.x_coordinate > 0  or job.y_coordinate > 0)
      self.assertNotIn((job.x_coordinate, job.y_coordinate), unique_coordinates)
      #self.assertTrue((job.x_coordinate, job.y_coordinate) not in unique_coordinates)
      unique_coordinates.add((job.x_coordinate, job.y_coordinate))

  def test_wrong_layout_fails(self):
    with self.assertRaises(ValueError):
      # Arrange
      loader = JobListLoaderDirector(JobListLoaderBuilder("a28v")).build_loaded_joblist_loader(TestUtils.get_mock_basic_config())
      graph = GraphRepresentation("a29z", loader, "otherlayout")
      # Act
      graph.perform_calculations()
      # Assert

  def test_calculate_average_post_time_is_zero(self):
    sut = self.get_standard_case_with_no_calculations()

    sut._calculate_average_post_time()

    self.assertEqual(sut.average_post_time, 0.0)

  def test_calculated_average_post_time_is_defined_value(self):
    # sut = self.get_wrapper_case_with_no_calculations()

    # sut._calculate_average_post_time()

    # self.assertEqual()
    # TODO: Add a case that includes COMPLETED POST sections
    pass

  def test_generates_node_data(self):
    sut = self.get_standard_case_with_no_calculations()

    sut.perform_calculations()

    self.assertGreater(len(sut.nodes), 0)
    for node in sut.nodes:
      self.assertIsNotNone(node["status"])
      self.assertIsNotNone(node["label"])
      self.assertIsNotNone(node["platform_name"])
      self.assertGreater(int(node["level"]), 0)
      if node["status_code"] == Status.COMPLETED:
        self.assertGreater(int(node["minutes"]), 0)
    self.assertGreater(sut.max_children_count, 0)
    self.assertGreater(sut.max_parent_count, 0)

  def test_generates_date_members_groups_correct_number(self):
    sut = self.get_standard_case_with_no_calculations()

    sut.perform_calculations()
    groups = sut._get_grouped_by_date_member_dict()

    self.assertGreater(len(groups), 0)
    self.assertEqual(len(groups), int(len(sut.joblist_loader.dates)*len(sut.joblist_loader.members)))

  def test_grouped_by_status_generates_correct_groups(self):
    sut = self.get_standard_case_with_no_calculations()

    sut.perform_calculations()
    groups = sut._get_grouped_by_status_dict()

    self.assertTrue('WAITING' in groups)
    self.assertTrue('COMPLETED' in groups)
    self.assertTrue('SUSPENDED' in groups)

  def test_grouped_by_wrong_parameter_fails(self):
    with self.assertRaises(ValueError):
      loader = self.get_loader(CASE_NO_WRAPPERS)
      sut = GraphRepresentation(CASE_NO_WRAPPERS, loader, Layout.STANDARD, "wrong-parameter")

      sut.perform_calculations()

  def test_out_err_files_are_generated_for_completed_jobs(self):
    sut = self.get_standard_case_with_no_calculations()
    basic_config = sut.joblist_helper.basic_config

    sut.perform_calculations()

    for job in sut.jobs:
      if job.name in ['a3tb_19930101_fc01_1_SIM']:
        self.assertTrue(job.out_file_path.startswith(basic_config.LOCAL_ROOT_DIR))
        self.assertTrue(job.err_file_path.startswith(basic_config.LOCAL_ROOT_DIR))
      else:
        self.assertIsNone(job.out_file_path)
        self.assertIsNone(job.err_file_path)



if __name__ == '__main__':
  unittest.main()
