#!/usr/bin/env python

import unittest
import common.utils_for_testing as UtilsForTesting
from mock import Mock
from components.representations.tree.tree import TreeRepresentation
from components.jobs.joblist_loader import JobListLoader
from components.experiment.pkl_organizer import PklOrganizer
from components.experiment.configuration_facade import AutosubmitConfigurationFacade
# from autosubmitAPIwu.config.basicConfig import BasicConfig
from bscearth.utils.config_parser import ConfigParserFactory
from config.config_common import AutosubmitConfigResolver

from common.utils import Status
from components.jobs.joblist_helper import JobListHelper
from config.basicConfig import APIBasicConfig

class TestTreeRepresentation(unittest.TestCase):
  def setUp(self):
    # BasicConfig.read()
    basic_config = UtilsForTesting.get_mock_basic_config()
    self.EXPID = "a28v"
    self.autosubmit_config = AutosubmitConfigResolver(self.EXPID, basic_config, ConfigParserFactory())
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



if __name__ == '__main__':
  unittest.main()
