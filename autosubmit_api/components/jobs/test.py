#!/usr/bin/env python

import unittest
from autosubmitAPIwu.components.jobs.joblist_loader import JobListLoader

class TestJobListLoader(unittest.TestCase):
  def setUp(self):
      pass
      
  def tearDown(self):
      pass
  
  def test_load(self):    
    loader = JobListLoader("a29z")
    loader.load_jobs()
    self.assertTrue(len(loader.jobs) > 0)
    for job in loader.jobs:
      job.do_print()  
  
  # def test_loader(self):
  #   tree = 

  # def test_load_out_err_files(self):
    

if __name__ == '__main__':
  unittest.main()
  

