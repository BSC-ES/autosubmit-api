import unittest
import autosubmit_api.history.test as test_history
import autosubmit_api.history.test_strategies as test_energy_strategies
import autosubmit_api.history.test_job_history as test_job_history
import autosubmit_api.history.platform_monitor.test as test_platform
import autosubmit_api.history.database_managers.test as test_history_database_managers
import autosubmit_api.components.experiment.test as test_experiment_components
import autosubmit_api.history.platform_monitor.test as test_slurm_monitor
import autosubmit_api.components.representations.graph.test as test_graph_representation
import autosubmit_api.workers.populate_details.test as test_populate_details


if __name__ == '__main__':
  runner = unittest.TextTestRunner()
  runner.run(unittest.makeSuite(test_history.TestExperimentHistory))
  # runner.run(unittest.makeSuite(test_energy_strategies.Test2DWrapperDistributionStrategy))
  # runner.run(unittest.makeSuite(test_history.TestLogging))
  # runner.run(unittest.makeSuite(test_platform.TestSlurmMonitor))
  # runner.run(unittest.makeSuite(test_history_database_managers.TestExperimentHistoryDbManager))
  # runner.run(unittest.makeSuite(test_history_database_managers.TestExperimentStatusDatabaseManager))
  # runner.run(unittest.makeSuite(test_experiment_components.TestPklOrganizer))
  # runner.run(unittest.makeSuite(test_slurm_monitor.TestSlurmMonitor))
  # runner.run(unittest.makeSuite(test_graph_representation.TestGraph))
  # runner.run(unittest.makeSuite(test_populate_details.TestPopulate))
  # runner.run(unittest.makeSuite(test_job_history.TestJobHistory))

  

