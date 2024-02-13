import datetime
import os
import pwd
import time
import subprocess
import traceback
import socket
import pickle
from autosubmit_api.builders.configuration_facade_builder import AutosubmitConfigurationFacadeBuilder, ConfigurationFacadeDirector
from autosubmit_api.components.experiment.pkl_organizer import PklOrganizer
from autosubmit_api.components.jobs.utils import get_job_total_stats
from autosubmit_api.config.config_common import AutosubmitConfigResolver
from autosubmit_api.experiment import common_db_requests as DbRequests
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.common.utils import Status
from bscearth.utils.config_parser import ConfigParserFactory


SAFE_TIME_LIMIT = 300


def process_completed_times(time_condition=60):
    """
    Tests for completed jobs of all autosubmit experiments and updates their completion times data in job_times and experiment_times.
    :param time_condition: Time difference in seconds that qualifies a experiment as out of date.
    :type time_condition: Integer
    """
    try:
        t0 = time.time()
        DEBUG = False
        APIBasicConfig.read()
        path = APIBasicConfig.LOCAL_ROOT_DIR
        # Time test for data retrieval
        # All experiment from file system
        currentDirectories = subprocess.Popen(['ls', '-t', path],
                                              stdout=subprocess.PIPE,
                                              stderr=subprocess.STDOUT) if (os.path.exists(path)) else None
        stdOut, _ = currentDirectories.communicate() if currentDirectories else (None, None)
        # Building connection to ecearth

        current_table = dict() # REMOVED: DbRequests.prepare_completed_times_db()
        # Build list of all folder in /esarchive/autosubmit which should be considered as experiments (although some might not be)
        # Pre process
        _preprocess_completed_times()
        experiments = stdOut.split() if stdOut else []
        counter = 0

        # Get current `details` from ecearth.db  and convert to set for effcient contain test
        details_table_ids_set = set(DbRequests.get_exps_detailed_complete().keys())
        # Get current `experiments` from ecearth.db
        experiments_table = DbRequests.get_exps_base()

        for expid in experiments:
            # Experiment names should be 4 char long
            if (len(expid) != 4):
                counter += 1
                continue
            # Experiment names must correspond to an experiment that contains a .pkl file
            exp_str = expid.decode("UTF-8")
            full_path = os.path.join(path, exp_str, "pkl", "job_list_" + exp_str + ".pkl")
            timest = 0
            if os.path.exists(full_path):
                # get time of last modification
                timest = int(os.stat(full_path).st_mtime)
            else:
                counter += 1
                continue
            counter += 1
            experiments_table_exp_id = experiments_table.get(exp_str, None)
            if current_table.get(exp_str, None) is None:
                # Pkl exists but is not registered in the table
                # INSERT
                # print("Pkl of " + exp_str + " exists but not in the table: INSERT")
                current_id = _process_pkl_insert_times(exp_str, full_path, timest, APIBasicConfig, DEBUG)
                _process_details_insert_or_update(exp_str, experiments_table_exp_id, experiments_table_exp_id in details_table_ids_set)
            else:
                exp_id, created, modified, total_jobs, completed_jobs = current_table[exp_str]
                time_diff = int(timest - modified)
                # print("Pkl of " + exp_str + " exists")
                current_id = _process_pkl_insert_times(exp_str, full_path, timest, APIBasicConfig, DEBUG)
                if time_diff > time_condition:
                    # Update table
                    _process_pkl_update_times(exp_str, full_path, timest, APIBasicConfig, exp_id, DEBUG)
                    _process_details_insert_or_update(exp_str, experiments_table_exp_id, experiments_table_exp_id in details_table_ids_set)
                DbRequests.update_experiment_times_only_modified(exp_id, timest)
            t1 = time.time()
            # Timer safeguard
            if (t1 - t0) > SAFE_TIME_LIMIT:
                raise Exception(
                    "Time limit reached {0:06.2f} seconds on process_completed_times while processing {1}. Time spent on reading data {2:06.2f} seconds.".format((t1 - t0), exp_str, (t1 - t0)))
    except Exception as ex:
        print((traceback.format_exc()))
        print(str(ex))


def _describe_experiment(experiment_id):
    user = ""
    created = ""
    model = ""
    branch = ""
    hpc = ""
    APIBasicConfig.read()
    exp_path = os.path.join(APIBasicConfig.LOCAL_ROOT_DIR, experiment_id)
    if not os.path.exists(exp_path):
        return user, created, model, branch, hpc

    user = os.stat(exp_path).st_uid
    try:
        user = pwd.getpwuid(user).pw_name
    except:
        pass

    created = datetime.datetime.fromtimestamp(
        os.path.getmtime(exp_path))

    try:
        as_conf = AutosubmitConfigResolver(
            experiment_id, APIBasicConfig, ConfigParserFactory())
        as_conf.reload()

        project_type = as_conf.get_project_type()
        if project_type != "none":
            if not as_conf.check_proj():
                return False
        if (as_conf.get_svn_project_url()):
            model = as_conf.get_svn_project_url()
            branch = as_conf.get_svn_project_url()
        else:
            model = as_conf.get_git_project_origin()
            branch = as_conf.get_git_project_branch()
        if model is "":
            model = "Not Found"
        if branch is "":
            branch = "Not Found"
        hpc = as_conf.get_platform()
    except:
        pass
    return user, created, model, branch, hpc


def _process_details_insert_or_update(expid, exp_id, current_details):
  """
  Decides whether the experiment should be inserted or updated in the details table.
  :param expid: name of experiment e.g: a001
  :type expid: str
  :param exp_id: id of experiment e.g: 1
  :type exp_id: int
  :param current_details: True if it exp_id exists in details table, False otherwise
  :rtype: bool
  :result: True if successful, False otherwise
  :rtype: bool
  """
  result = False
  if exp_id:
    try:
      user, created, model, branch, hpc = _describe_experiment(expid)
      if current_details:
          # Update
          result = DbRequests._update_ecearth_details(exp_id, user, created, model, branch, hpc)
      else:
          # Insert
          _Id = DbRequests._insert_into_ecearth_details(exp_id, user, created, model, branch, hpc)
          result = True if _Id else False
    except Exception as exp:
        print(exp)
  return result


def _preprocess_completed_times():
  """
  Preprocess table to get rid of possible conflicts
  :param current_table: table experiment_times from as_times.db
  """
  current_table = DbRequests.get_experiment_times_group()
  for name, _ids in list(current_table.items()):
      if len(_ids) > 1:
          print((str(name) + " has more than 1 register."))
          for i in range(0, len(_ids) - 1):
              _id = _ids[i]
              deleted_outdated = DbRequests.delete_experiment_data(_id)

def _process_pkl_update_times(expid, path_pkl, timest_pkl, BasicConfig, exp_id, debug=False):
    """
    Updates register in job_times and experiment_times for the given experiment.
    :param expid: Experiment name
    :type expid: String
    :param path_pkl: path to the pkl file (DEPRECATED)
    :type path_pkl: String
    :param timest_pkl: Timestamp of the last modified date of the pkl file
    :type timest_pkl: Integer
    :param BasicConfig: Configuration of AS
    :type BasicConfig: Object
    :param exp_id: Id of experiment
    :type exp_id: Integer
    :param debug: Flag (testing purposes)
    :type debug: Boolean
    :return: Nothing
    """
    # debug = True
    try:
        found_in_pkl = list()
        BasicConfig.read()

        tmp_path = os.path.join(BasicConfig.LOCAL_ROOT_DIR, expid, BasicConfig.LOCAL_TMP_DIR)
        job_times_db = dict()
        total_jobs = 0
        completed_jobs = 0
        fd = None
        # t_start = time.time()
        # Get current detail from database
        experiment_times_detail = DbRequests.get_times_detail(exp_id)
        # t_seconds = time.time() - t_start
        must_update_header = False

        to_update = []
        to_create = []

        # Read PKL
        autosubmit_config_facade = ConfigurationFacadeDirector(
            AutosubmitConfigurationFacadeBuilder(expid)).build_autosubmit_configuration_facade()
        pkl_organizer = PklOrganizer(autosubmit_config_facade)
        for job_item in pkl_organizer.current_content:
            total_jobs += 1
            status_code = job_item.status
            job_name = job_item.name
            found_in_pkl.append(job_name)
            status_text = str(Status.VALUE_TO_KEY[status_code])
            if (status_code == Status.COMPLETED):
                completed_jobs += 1
            if (experiment_times_detail) and job_name in list(experiment_times_detail.keys()):
                # If job in pkl exists in database, retrieve data from database
                submit_time, start_time, finish_time, status_text_in_table, detail_id = experiment_times_detail[job_name]
                if (status_text_in_table != status_text):
                    # If status has changed
                    submit_time, start_time, finish_time, _ = get_job_total_stats(status_code, job_name, tmp_path)
                    submit_ts = int(time.mktime(submit_time.timetuple())) if len(str(submit_time)) > 0 else 0
                    start_ts = int(time.mktime(start_time.timetuple())) if len(str(start_time)) > 0 else 0
                    finish_ts = int(time.mktime(finish_time.timetuple())) if len(str(finish_time)) > 0 else 0
                    # UPDATE
                    must_update_header = True
                    to_update.append((int(timest_pkl),
                                        submit_ts,
                                        start_ts,
                                        finish_ts,
                                        status_text,
                                        detail_id))

            else:
                # Insert only if it is not WAITING nor READY
                if (status_code not in [Status.WAITING, Status.READY]):
                    submit_time, start_time, finish_time, status_text = get_job_total_stats(status_code, job_name, tmp_path)
                    must_update_header = True
                    to_create.append((exp_id,
                                        job_name,
                                        int(timest_pkl),
                                        int(timest_pkl),
                                        int(time.mktime(submit_time.timetuple())) if len(str(submit_time)) > 0 else 0,
                                        int(time.mktime(start_time.timetuple())) if len(str(start_time)) > 0 else 0,
                                        int(time.mktime(finish_time.timetuple())) if len(str(finish_time)) > 0 else 0,
                                        status_text))


        # Update Many
        if len(to_update) > 0:
            DbRequests.update_many_job_times(to_update)
        # Create Many
        if len(to_create) > 0:
            DbRequests.create_many_job_times(to_create)

        if must_update_header == True:
            exp_id = DbRequests.update_experiment_times(exp_id, int(timest_pkl), completed_jobs, total_jobs, debug)

        # Reviewing for deletes:
        if len(found_in_pkl) > 0 and (experiment_times_detail):
            detail_list = []
            for key in experiment_times_detail:
                if key not in found_in_pkl:
                    # Delete Row
                    submit_time, start_time, finish_time, status_text_in_table, detail_id = experiment_times_detail[key]
                    detail_list.append((detail_id,))
            if len(detail_list) > 0:
                DbRequests._delete_many_from_job_times_detail(detail_list)

    except (socket.error, EOFError):
        # print(str(expid) + "\t EOF Error")
        pass
    except Exception as ex:
        print(expid)
        print((traceback.format_exc()))


def _process_pkl_insert_times(expid, path_pkl, timest_pkl, BasicConfig, debug=False):
    """
    Process Pkl contents and insert information into database if status of jobs is not WAITING (to save space).
    :param conn: Connection to database
    :type conn: Sqlite3 connection object
    :param expid: Experiment name
    :type expid: String
    :param path_pkl: Path to the pkl file
    :type path_pkl: String
    :param timest_pkl: Timestamp of the pkl modified date
    :type timest_pkl: Integer
    :param BasicConfig: Configuration data of AS
    :type BasicConfig: Object
    :param debug: Flag (proper name should be test)
    :type debug: Boolean
    """
    # BasicConfig.read()
    # path = BasicConfig.LOCAL_ROOT_DIR
    # db_file = os.path.join(path, DbRequests.DB_FILE_AS_TIMES)
    # Build tmp path to search for TOTAL_STATS files
    tmp_path = os.path.join(BasicConfig.LOCAL_ROOT_DIR, expid, BasicConfig.LOCAL_TMP_DIR)
    job_times = dict()  # Key: job_name
    total_jobs = 0
    completed_jobs = 0
    status_code = Status.UNKNOWN
    status_text = str(Status.VALUE_TO_KEY[status_code])
    try:
        # Read PKL
        autosubmit_config_facade = ConfigurationFacadeDirector(
            AutosubmitConfigurationFacadeBuilder(expid)).build_autosubmit_configuration_facade()
        pkl_organizer = PklOrganizer(autosubmit_config_facade)
        for job_item in pkl_organizer.current_content:
            total_jobs += 1
            status_code = job_item.status
            job_name = job_item.name
            status_text = str(Status.VALUE_TO_KEY[status_code])
            if (status_code == Status.COMPLETED):
                completed_jobs += 1
            job_times[job_name] = status_code
    except:
        pass

    try:
        # Insert header
        current_id = DbRequests.insert_experiment_times_header(expid, int(timest_pkl), total_jobs, completed_jobs, debug)
        if(current_id > 0):
            # Insert detail
            to_insert_many = []
            for job_name in job_times:
                # Inserting detail. Do not insert WAITING or READY jobs.
                status_code = job_times[job_name]
                if (status_code not in [Status.WAITING, Status.READY]):
                    submit_time, start_time, finish_time, status_text = get_job_total_stats(status_code, job_name, tmp_path)
                    to_insert_many.append((current_id,
                                           job_name,
                                           int(timest_pkl),
                                           int(timest_pkl),
                                           int(time.mktime(submit_time.timetuple())) if len(
                                               str(submit_time)) > 0 else 0,
                                           int(time.mktime(start_time.timetuple())) if len(
                                               str(start_time)) > 0 else 0,
                                           int(time.mktime(finish_time.timetuple())) if len(
                                               str(finish_time)) > 0 else 0,
                                           status_text))
            if len(to_insert_many) > 0:
                DbRequests.create_many_job_times(to_insert_many)
        else:
            pass

        return current_id
    except Exception as ex:
        print(expid)
        print((traceback.format_exc()))
        return 0
