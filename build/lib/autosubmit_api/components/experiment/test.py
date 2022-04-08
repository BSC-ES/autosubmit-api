#!/usr/bin/env python

import unittest
from mock import Mock
from autosubmit_api.components.jobs.job_factory import SimJob
from autosubmit_api.components.experiment.pkl_organizer import PklOrganizer
from autosubmit_api.builders.configuration_facade_builder import ConfigurationFacadeDirector, AutosubmitConfigurationFacadeBuilder
from autosubmit_api.common.utils_for_testing import get_mock_basic_config

class TestConfigurationFacade(unittest.TestCase):
  def setUp(self):
    pass

  def test_configfacade_build_object(self):
    basic_config = get_mock_basic_config()

    sut = ConfigurationFacadeDirector(AutosubmitConfigurationFacadeBuilder("a28v")).build_autosubmit_configuration_facade(basic_config)

    self.assertTrue(sut.chunk_size == 1)
    self.assertTrue(sut.chunk_unit == "month")    
    self.assertTrue(sut.current_years_per_sim == float(1.0/12.0))
    
    self.assertTrue(sut.sim_processors == 5040)
    self.assertTrue(sut.get_owner_id() > 0)
    self.assertTrue(sut.get_autosubmit_version() == "3.13.0")
    self.assertTrue(sut.get_main_platform() == "marenostrum4")
    self.assertTrue(sut.get_project_type() == "git")
    self.assertTrue(sut.get_model() == "https://earth.bsc.es/gitlab/es/auto-ecearth3.git")
    self.assertTrue(sut.get_branch() == "3.2.2_Primavera_Stream2_production_T1279-ORCA12")    
    self.assertTrue(sut.get_platform_qos("marenostrum4", 5040) == "class_a")


  def test_configfacade_update_sims_updated(self):    
    sim_jobs = [SimJob(), SimJob(), SimJob(), SimJob(), SimJob()]
    basic_config = get_mock_basic_config()

    sut = ConfigurationFacadeDirector(AutosubmitConfigurationFacadeBuilder("a28v")).build_autosubmit_configuration_facade(basic_config)
    sut.update_sim_jobs(sim_jobs)

    for job in sim_jobs:
      self.assertTrue(job.ncpus == 5040)
      self.assertTrue(job.years_per_sim == float(1.0/12.0))
  
  def test_get_queue_serial(self):
    basic_config = get_mock_basic_config()

    sut = ConfigurationFacadeDirector(AutosubmitConfigurationFacadeBuilder("a28v")).build_autosubmit_configuration_facade(basic_config)

    self.assertTrue(sut.get_platform_qos("cca-intel", 5040) == "np")
    self.assertTrue(sut.get_platform_qos("cca-intel", 1) == "ns")
    

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

  