import unittest
import common.utils_for_testing as TestUtils
from builders.experiment_history_builder import ExperimentHistoryDirector, ExperimentHistoryBuilder

class TestJobHistory(unittest.TestCase):

  def setUp(self):
    self.basic_config = TestUtils.get_mock_basic_config()

  def test_get_job_history_gets_correct_number_of_cases(self):
    # Arrange
    sut = ExperimentHistoryDirector(ExperimentHistoryBuilder("a3tb")).build_reader_experiment_history(self.basic_config)
    # Act
    job_history = sut.get_historic_job_data("a3tb_19930501_fc01_3_SIM")
    # Assert
    self.assertEqual(len(job_history), 5) # 5 rows in database

  def test_get_job_history_gets_correct_queuing_times(self):
    # Arrange
    sut = ExperimentHistoryDirector(ExperimentHistoryBuilder("a3tb")).build_reader_experiment_history(self.basic_config)
    # Act
    job_history = sut.get_historic_job_data("a3tb_19930501_fc01_3_SIM")
    counter_to_queue_timedelta_str = {int(job["counter"]): job["queue_time"] for job in job_history}
    # Assert
    self.assertEqual(counter_to_queue_timedelta_str[18], "0:03:28")
    self.assertEqual(counter_to_queue_timedelta_str[19], "0:00:04")
    self.assertEqual(counter_to_queue_timedelta_str[20], "0:00:05")
    self.assertEqual(counter_to_queue_timedelta_str[24], "0:01:18")
    self.assertEqual(counter_to_queue_timedelta_str[25], "0:02:35")

  def test_get_job_history_gets_correct_running_times(self):
    # Arrange
    sut = ExperimentHistoryDirector(ExperimentHistoryBuilder("a3tb")).build_reader_experiment_history(self.basic_config)
    # Act
    job_history = sut.get_historic_job_data("a3tb_19930501_fc01_3_SIM")
    counter_to_run_timedelta_str = {int(job["counter"]): job["run_time"] for job in job_history}
    # Assert
    self.assertEqual(counter_to_run_timedelta_str[18], "0:00:54")
    self.assertEqual(counter_to_run_timedelta_str[19], "0:00:53")
    self.assertEqual(counter_to_run_timedelta_str[20], "0:00:52")
    self.assertEqual(counter_to_run_timedelta_str[24], "0:23:16")
    self.assertEqual(counter_to_run_timedelta_str[25], "0:07:58")

  def test_get_job_history_gets_correct_SYPD(self):
    # Arrange
    sut = ExperimentHistoryDirector(ExperimentHistoryBuilder("a3tb")).build_reader_experiment_history(self.basic_config)
    # Act
    job_history = sut.get_historic_job_data("a3tb_19930501_fc01_3_SIM")
    counter_to_SYPD = {int(job["counter"]): job["SYPD"] for job in job_history}
    # Assert
    self.assertEqual(counter_to_SYPD[18], None)
    self.assertEqual(counter_to_SYPD[19], None)
    self.assertEqual(counter_to_SYPD[20], None)
    self.assertEqual(counter_to_SYPD[24], round(86400*(1.0/12.0)/1396, 2))
    self.assertEqual(counter_to_SYPD[25], round(86400*(1.0/12.0)/478, 2))

  def test_get_job_history_gets_correct_ASYPD(self):
    # Arrange
    sut = ExperimentHistoryDirector(ExperimentHistoryBuilder("a3tb")).build_reader_experiment_history(self.basic_config)
    # Act
    job_history = sut.get_historic_job_data("a3tb_19930501_fc01_3_SIM")
    counter_to_ASYPD = {int(job["counter"]): job["ASYPD"] for job in job_history}
    # Assert
    self.assertEqual(counter_to_ASYPD[18], None)
    self.assertEqual(counter_to_ASYPD[19], None)
    self.assertEqual(counter_to_ASYPD[20], None)
    self.assertEqual(counter_to_ASYPD[24], round(86400*(1.0/12.0)/(1396 + 78), 2))
    self.assertEqual(counter_to_ASYPD[25], round(86400*(1.0/12.0)/(478 + 155), 2))

if __name__ == "__main__":
  unittest.main()