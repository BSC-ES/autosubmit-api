import unittest
import os
from autosubmitAPIwu.statistics.statistics import Statistics
from autosubmitAPIwu.monitor.monitor import Monitor
from autosubmitAPIwu.job.job_common import Status
from autosubmitAPIwu.job.job_utils import SubJobManager, SubJob
from autosubmitAPIwu.config.basicConfig import BasicConfig
from autosubmitAPIwu.config.config_common import AutosubmitConfig
from bscearth.utils.config_parser import ConfigParserFactory
from autosubmitAPIwu.autosubmit import Autosubmit
from autosubmitAPIwu.job.job_list import JobList
import autosubmitAPIwu.experiment.common_db_requests as DbRequests
import autosubmitAPIwu.database.db_structure as DbStructure
from autosubmitAPIwu.database.db_jobdata import JobDataStructure, ExperimentGraphDrawing
import statistics

class TestStatistics(unittest.TestCase):
  def setUp(self):
    self.expid = "a49z"

  def test_normal_execution(self):
    print("Testing normal execution")
    expid = self.expid
    period_fi = ""
    period_ini = ""
    ft = "Any"
    results = None
    subjobs = list()
    BasicConfig.read()
    path_structure = BasicConfig.STRUCTURES_DIR
    path_local_root = BasicConfig.LOCAL_ROOT_DIR
    as_conf = AutosubmitConfig(expid, BasicConfig, ConfigParserFactory())
    as_conf.reload()
    job_list = Autosubmit.load_job_list(expid, as_conf, False)
    jobs_considered = [job for job in job_list.get_job_list() if job.status not in [
            Status.READY, Status.WAITING]]
    job_to_package, package_to_jobs, _, _ = JobList.retrieve_packages(
            BasicConfig, expid, [job.name for job in job_list.get_job_list()])
    db_file = os.path.join(path_local_root, "ecearth.db")
    conn = DbRequests.create_connection(db_file)
    # Job information from worker database
    job_times = DbRequests.get_times_detail_by_expid(
        conn, expid)
    # Job information from job historic data
    job_data, warning_messages = JobDataStructure(
        expid).get_total_job_data(job_list.get_job_list(), job_times)
    print("Structure")
    current_table_structure = {}
    if (job_to_package):
        current_table_structure = DbStructure.get_structure(
            expid, path_structure)
    # Model jobs
    for job in job_list.get_job_list():
        job_info = JobList.retrieve_times(
            job.status, job.name, job._tmp_path, make_exception=False, job_times=job_times, seconds=True, job_data_collection=job_data)
        time_total = (job_info.queue_time +
                      job_info.run_time) if job_info else 0
        subjobs.append(
            SubJob(job.name,
                    job_to_package.get(job.name, None),
                    job_info.queue_time if job_info else 0,
                    job_info.run_time if job_info else 0,
                    time_total,
                    job_info.status if job_info else Status.UNKNOWN)
        )

    manager = SubJobManager(subjobs, job_to_package,
                            package_to_jobs, current_table_structure)

    if len(jobs_considered) > 0:
      print("Get results")
      statistics = Statistics(jobs_considered, period_ini, period_fi, manager.get_collection_of_fixes_applied())
      statistics.get_statistics()
      statistics.calculate_summary()
    else:
        raise Exception("Autosubmit API couldn't find jobs that match your search critearia (Section: {0}) in the period from {1} to {2}.".format(
            ft, period_ini, period_fi))
    return results

if __name__ == '__main__':
  unittest.main()