import os
import time
from autosubmit_api.common.utils import get_experiments_from_folder
# from autosubmitAPIwu.job.job_utils import get_job_package_code
from autosubmit_api.config.basicConfig import BasicConfig
from autosubmit_api.history.database_managers.experiment_history_db_manager import ExperimentHistoryDbManager
# from autosubmit_api.components.jobs.joblist_loader import JobListLoader
from autosubmit_api.builders.joblist_loader_builder import JobListLoaderBuilder, JobListLoaderDirector
from autosubmit_api.builders.experiment_history_builder import ExperimentHistoryDirector, ExperimentHistoryBuilder
from autosubmit_api.history.experiment_history import ExperimentHistory
from autosubmit_api.history.platform_monitor.slurm_monitor import SlurmMonitor
from autosubmit_api.history.strategies import PlatformInformationHandler, SingleAssociationStrategy, StraightWrapperAssociationStrategy, TwoDimWrapperDistributionStrategy, GeneralizedWrapperDistributionStrategy

BasicConfig.read()

ignore_list = ["a4a6"]

def get_version17_wrapper_experiments():
  experiments = get_experiments_from_folder(BasicConfig.LOCAL_ROOT_DIR)
  wrapper_experiments = []
  normal_experiments = []
  for exp in experiments:
    try:
      pkl_path = os.path.join(BasicConfig.LOCAL_ROOT_DIR, exp, "pkl", "job_list_{0}.pkl".format(exp))
      if os.path.exists(pkl_path):
        time_diff = int(time.time()) - int(os.stat(pkl_path).st_mtime)
        if time_diff <= 86400:
          manager = ExperimentHistoryDbManager(exp, BasicConfig)      
          if manager.my_database_exists():            
            if manager._get_pragma_version() >= 17:
              experiment_run = manager.get_experiment_run_dc_with_max_id()          
              if experiment_run.get_wrapper_type():
                wrapper_experiments.append(exp)   
              else:
                normal_experiments.append(exp)
    except Exception as exp:
      pass
      # print(exp)
  return wrapper_experiments, normal_experiments


def update_old_data():
  wrapper_experiments, normal_experiments = get_version17_wrapper_experiments()
  all_experiments = wrapper_experiments + normal_experiments
  # print("Wrapper experiments:")
  for expid in wrapper_experiments:
    if expid in ignore_list:
      continue
    # print(expid)
    loader = JobListLoaderDirector(JobListLoaderBuilder(expid)).build_loaded_joblist_loader() # JobListLoader(expid)
    # loader.load_jobs()
    history = ExperimentHistoryDirector(ExperimentHistoryBuilder(expid)).build_reader_experiment_history() # ExperimentHistory(expid, BasicConfig.JOBDATA_DIR, BasicConfig.HISTORICAL_LOG_DIR)
    job_data_dcs = history.manager.get_all_last_job_data_dcs()
    for job_data_dc in job_data_dcs:
      job_info = loader.job_dictionary.get(job_data_dc.job_name, None)
      if job_info and job_info.package_code > 0:
        job_data_dc.submit = job_info.submit_ts
        job_data_dc.start = job_info.start_ts
        job_data_dc.finish = job_info.finish_ts
        # print(job_info.package_code)
        job_data_dc.rowtype = int(job_info.package_code)
        updated_dc=history.manager.update_job_data_dc_by_id(job_data_dc)
        print("updated {} in wrapper {}".format(updated_dc.job_name, updated_dc.wrapper_code))
  
  print("All experiments")
  for expid in all_experiments:
    if expid in ignore_list:
      continue 
     # print(expid)
    try:    
      loader = JobListLoaderDirector(JobListLoaderBuilder(expid)).build_loaded_joblist_loader() # JobListLoader(expid)
      # loader.load_jobs()
      history = ExperimentHistoryDirector(ExperimentHistoryBuilder(expid)).build_reader_experiment_history() # ExperimentHistory(expid, BasicConfig.JOBDATA_DIR, BasicConfig.HISTORICAL_LOG_DIR)
      job_data_dcs = history.manager.get_all_last_job_data_dcs()
      completed_job_data_dcs = sorted([job for job in job_data_dcs if job.status == "COMPLETED"], key=lambda x: x._id)
      job_distribution = {}
      for job_data_dc in completed_job_data_dcs:
        job_distribution.setdefault(job_data_dc.rowtype, []).append(job_data_dc)
      completed_job_data_dcs_to_process = []
      for rowtype in job_distribution:
        if rowtype == 2:
          completed_job_data_dcs_to_process.extend(job_distribution[rowtype])
        else:
          completed_job_data_dcs_to_process.append(job_distribution[rowtype][-1])

      for job_data_dc in completed_job_data_dcs_to_process:
        try:
          slurm_monitor = SlurmMonitor(job_data_dc.platform_output)          
          job_data_dcs_in_wrapper = history.manager.get_job_data_dcs_last_by_wrapper_code(job_data_dc.wrapper_code)
          job_data_dcs_completed_in_wrapper = sorted([job for job in job_data_dcs_in_wrapper if job.status == "COMPLETED"], key=lambda x: x._id)
          # print("****** {} *******".format(job_data_dc.job_name))
          # print("Jobs in wrapper {}".format(len(job_data_dcs_completed_in_wrapper)))
          job_data_dcs_to_update = []      
          if len(job_data_dcs_completed_in_wrapper) > 0:
            info_handler = PlatformInformationHandler(StraightWrapperAssociationStrategy(BasicConfig.HISTORICAL_LOG_DIR))
            job_data_dcs_to_update = info_handler.execute_distribution(job_data_dc, job_data_dcs_completed_in_wrapper, slurm_monitor)            
            if len(job_data_dcs_to_update) == 0:              
              info_handler.strategy = TwoDimWrapperDistributionStrategy(BasicConfig.HISTORICAL_LOG_DIR)
              job_data_dcs_to_update = info_handler.execute_distribution(job_data_dc, job_data_dcs_completed_in_wrapper, slurm_monitor)
            if len(job_data_dcs_to_update) == 0:              
              info_handler.strategy = GeneralizedWrapperDistributionStrategy(BasicConfig.HISTORICAL_LOG_DIR)
              job_data_dcs_to_update = info_handler.execute_distribution(job_data_dc, job_data_dcs_completed_in_wrapper, slurm_monitor)
          else:            
            info_handler = PlatformInformationHandler(SingleAssociationStrategy(BasicConfig.HISTORICAL_LOG_DIR))
            job_data_dcs_to_update = info_handler.execute_distribution(job_data_dc, job_data_dcs_completed_in_wrapper, slurm_monitor)       
          updates_count = history.manager.update_list_job_data_dc_by_each_id(job_data_dcs_to_update)   
          # if updates_count > 0:            
          #   for jdc in job_data_dcs_to_update:
          #     print("{} -> energy {}".format(jdc.job_name, jdc.energy))   
          # print(updates_count)
        except Exception as exp:
          # print(exp)
          pass        
    except Exception as exp:
      print("{} Exception: {}".format(expid, str(exp)))
      pass

    # for job in loader._jobs:
      # print("{} -> {}".format(job.name, job.package_code))


if __name__ == "__main__":
  # wrapper, experiments = get_version17_wrapper_experiments()
  # for expid in wrapper:
  #   print("Wrapper experiment: {}".format(expid))
  # for expid in experiments:
  #   print("Normal experiment: {}".format(expid))
  update_old_data()
