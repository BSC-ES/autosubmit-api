import unittest
from workers.populate_details.populate import DetailsProcessor
import common.utils_for_testing as TestUtils

class TestPopulate(unittest.TestCase):
  def setUp(self):
    pass

  def test_retrieve_correct_experiments(self):
    # Arrange
    sut = DetailsProcessor(TestUtils.get_mock_basic_config())
    # Act
    experiments = sut._get_experiments()
    names = [experiment.name for experiment in experiments]
    # Assert
    self.assertIn("a28v", names)
    self.assertIn("a3tb", names)


  def test_get_details_from_experiment(self):
    # Arrange
    sut = DetailsProcessor(TestUtils.get_mock_basic_config())
    # Act
    details = sut._get_details_data_from_experiment("a28v")
    # Assert
    self.assertIsNotNone(details)
    self.assertEqual("wuruchi", details.owner)
    self.assertIsInstance(details.created, str)
    self.assertIsInstance(details.model, str)
    self.assertIsInstance(details.branch, str)
    self.assertEqual("marenostrum4", details.hpc)


  def test_get_all_experiment_details_equals_number_of_test_cases(self):
    # Arrange
    sut = DetailsProcessor(TestUtils.get_mock_basic_config())
    # Act
    processed_data = sut._get_all_details()
    # Assert
    self.assertEqual(len(processed_data), 2) # There are 2 cases in the test_cases folder


  def test_process_inserts_the_details(self):
    # Arrange
    sut = DetailsProcessor(TestUtils.get_mock_basic_config())
    # Act
    number_rows = sut.process()
    # Assert
    self.assertEqual(number_rows, 2)


if __name__ == '__main__':
  unittest.main()