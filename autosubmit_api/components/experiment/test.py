#!/usr/bin/env python

import unittest
from mock import Mock
from autosubmit_api.components.experiment.pkl_organizer import PklOrganizer

class TestPklOrganizer(unittest.TestCase):
  
  def setUp(self):
    self.configuration_facade = Mock() #
    self.configuration_facade.pkl_path = "autosubmit_api/components/experiment/test_case/a29z/pkl/job_list_a29z.pkl"    
    self.configuration_facade.get_autosubmit_version.return_value = "3.13.0"    
    self.pkl_organizer = PklOrganizer(self.configuration_facade)
    self.assertTrue(len(self.pkl_organizer.current_content) == 590)
    self.assertTrue(len(self.pkl_organizer.sim_jobs) == 0)
    self.assertTrue(len(self.pkl_organizer.post_jobs) == 0)
    self.assertTrue(len(self.pkl_organizer.transfer_jobs) == 0)
    self.assertTrue(len(self.pkl_organizer.clean_jobs) == 0)
    self.assertTrue(len(self.pkl_organizer.dates) == 0)
    self.assertTrue(len(self.pkl_organizer.members) == 0)
    self.assertTrue(len(self.pkl_organizer.sections) == 0)

  def tearDown(self):
    del self.pkl_organizer

  def test_identify_configuration(self):        
    self.pkl_organizer.identify_dates_members_sections()
    self.assertTrue(len(self.pkl_organizer.dates) == 2)
    self.assertTrue(len(self.pkl_organizer.members) == 7)
    self.assertTrue(len(self.pkl_organizer.sections) == 9)

  def test_distribute_jobs(self):
    self.pkl_organizer.distribute_jobs()
    self.assertTrue(len(self.pkl_organizer.sim_jobs) == 168)
    self.assertTrue(len(self.pkl_organizer.post_jobs) == 168)
    self.assertTrue(len(self.pkl_organizer.transfer_jobs) == 42)
    self.assertTrue(len(self.pkl_organizer.clean_jobs) == 168)
    
  def test_validate_warnings(self):
    self.pkl_organizer.distribute_jobs()
    self.assertTrue(len(self.pkl_organizer.get_completed_section_jobs("TRANSFER")) == 0) # There are no COMPLETED TRANSFER Jobs
    self.pkl_organizer._validate_current()
    self.assertTrue(self.pkl_organizer.warnings[0].startswith("RSYPD"))
  

if __name__ == '__main__':
  unittest.main()

  