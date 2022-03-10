#!/usr/bin/env python

import unittest
import autosubmitAPIwu.common.utils_for_testing as UtilsForTesting
from mock import Mock
from autosubmitAPIwu.components.representations.tree.tree import TreeRepresentation
from autosubmitAPIwu.components.jobs.joblist_loader import JobListLoader
from autosubmitAPIwu.components.experiment.pkl_organizer import PklOrganizer
from autosubmitAPIwu.components.experiment.configuration_facade import AutosubmitConfigurationFacade
# from autosubmitAPIwu.config.basicConfig import BasicConfig
from bscearth.utils.config_parser import ConfigParserFactory
from autosubmitAPIwu.config.config_common import AutosubmitConfig

from autosubmitAPIwu.job.job_common import Status
from autosubmitAPIwu.components.jobs.joblist_helper import JobListHelper
from autosubmitAPIwu.config.basicConfig import BasicConfig

class TestTreeRepresentation(unittest.TestCase):
  def setUp(self):
    # BasicConfig.read()
    basic_config = UtilsForTesting.get_mock_basic_config()
    self.EXPID = "a28v"
    self.autosubmit_config = AutosubmitConfig(self.EXPID, basic_config, ConfigParserFactory())
    self.autosubmit_config.reload()
    self.configuration_facade = AutosubmitConfigurationFacade(self.EXPID, basic_config, self.autosubmit_config)
    self.pkl_organizer = PklOrganizer(self.configuration_facade)
    self.pkl_organizer.identify_dates_members_sections()
    self.simple_jobs = self.pkl_organizer.get_simple_jobs(self.configuration_facade.tmp_path)
    self.job_list_helper = JobListHelper(self.EXPID, self.simple_jobs, basic_config)
    self.job_list_loader = JobListLoader(self.EXPID, self.configuration_facade, self.pkl_organizer, self.job_list_helper)
    self.job_list_loader.load_jobs()
      
  def tearDown(self):
      pass

  def test_full_tree_representation(self):
    tree_representation = TreeRepresentation(self.EXPID, self.job_list_loader)
    tree_representation.perform_calculations()
    self.assertTrue(len(tree_representation.nodes) == 783)
    self.assertTrue(len(tree_representation.joblist_loader.package_names) == 10)
  
  def test_date_member_distribution(self):
    tree_representation = TreeRepresentation(self.EXPID, self.job_list_loader)
    tree_representation._distribute_into_date_member_groups()    
    distribution_count = sum(len(tree_representation._date_member_distribution[item]) for item in tree_representation._date_member_distribution)
    self.assertTrue(distribution_count + len(tree_representation._no_date_no_member_jobs) == 783)        
    self.assertTrue(len(tree_representation._date_member_distribution) == 1)      
    self.assertTrue(len(self.job_list_loader.dates) == len(tree_representation._distributed_dates))
    self.assertTrue(len(self.job_list_loader.members) == len(tree_representation._distributed_members))

  

  # def test_load(self):    
  #   tree = TreeRepresentation("a3zk") 
  #   tree.setup()
  #   tree._distribute_into_date_member_groups()
  #   for key, jobs in tree._date_member_distribution.items():
  #     print(key)
  #     for job in jobs:
  #       print(job.name)
  #       print(job.do_print())
  #   print("Others:")
  #   for job in tree._no_date_no_member_jobs:
  #     print(job.name)
    

  # def test_gen_dm_folders(self):
  #   tree = TreeRepresentation("a29z") 
  #   tree.setup()
  #   tree._distribute_into_date_member_groups()
    # tree._distribute_into_date_member_groups()

  # def test_tree_loader(self):
  #   tree = TreeRepresentation("a44a")
  #   tree.setup()
  #   self.assertTrue(tree.joblist_loader.pkl_organizer.is_wrapper_type_in_pkl == True)
  #   self.assertTrue(len(tree.joblist_loader.pkl_organizer.current_content) > 0)    
  #   tree.perform_calculations()
  #   print("Number of jobs {}".format(len(tree.nodes)))
  #   self.assertTrue(len(tree.nodes) == 54)

  # def test_generate_complete(self):
  #   tree = TreeRepresentation("a29z")
  #   tree.setup()
  #   tree.perform_calculations()              
  #   for job in tree.joblist_loader.jobs:      
  #     if job.status == Status.COMPLETED:
  #       self.assertTrue(job.out_path_local.startswith("/esarchive/"))
  #       self.assertTrue(job.err_path_local.startswith("/esarchive/"))
      #   print(job.out_path_local)
      #   print(job.err_path_local)
      # else:
      #   print(job.name)
    # self.assertTrue(self.test_graph.edge_count == edge_count)

if __name__ == '__main__':
  unittest.main()
  

