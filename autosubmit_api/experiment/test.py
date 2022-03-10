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

import unittest

from autosubmit_api.experiment.common_requests import get_job_history, get_experiment_data

class TestCommonRequests(unittest.TestCase):
  def setUp(self):
    pass

  def test_get_history(self):
    result = get_job_history("a3z4", "a3z4_19951101_fc8_1_SIM")
    print(result)
    self.assertTrue(result != None)

  def test_get_experiment_data(self):
    result = get_experiment_data("a29z")
    print(result)
    result2 = get_experiment_data("a4a0")
    print(result2)
    result3 = get_experiment_data("a2am")
    print(result3)
    self.assertTrue(result != None)
    self.assertTrue(result2 != None)
    self.assertTrue(result3 != None)

if __name__ == "__main__":
  unittest.main()