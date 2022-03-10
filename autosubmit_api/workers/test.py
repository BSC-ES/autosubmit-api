import unittest

import autosubmitAPIwu.workers.process_graph_drawings as ProcessGraph
from autosubmitAPIwu.builders.configuration_facade_builder import ConfigurationFacadeDirector, AutosubmitConfigurationFacadeBuilder

class TestGraphDraw(unittest.TestCase):
  def setUp(self):
    pass

  def test_graph_drawing_generator(self):
    EXPID = "a29z"
    autosubmit_configuration_facade = ConfigurationFacadeDirector(AutosubmitConfigurationFacadeBuilder(EXPID)).build_autosubmit_configuration_facade()
    result = ProcessGraph._process_graph(EXPID, autosubmit_configuration_facade.chunk_size)
    self.assertTrue(result == None)
  

if __name__ == "__main__":
  unittest.main()