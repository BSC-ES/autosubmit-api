import os
import time
from autosubmit_api.bgtasks.bgtask import BackgroundTaskTemplate
from autosubmit_api.common import utils as common_utils
from autosubmit_api.components.jobs import utils as JUtils
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.experiment import common_db_requests as DbRequests
from autosubmit_api.experiment.common_requests import SAFE_TIME_LIMIT


def verify_last_completed(seconds=300):
    """
    Verifying last 300 seconds by default
    """
    # Basic info
    t0 = time.time()
    APIBasicConfig.read()
    # Current timestamp
    current_st = time.time()
    # Current latest detail
    td0 = time.time()
    latest_detail = DbRequests.get_latest_completed_jobs(seconds)
    t_data = time.time() - td0
    # Main Loop
    for job_name, detail in list(latest_detail.items()):
        tmp_path = os.path.join(
            APIBasicConfig.LOCAL_ROOT_DIR, job_name[:4], APIBasicConfig.LOCAL_TMP_DIR)
        detail_id, submit, start, finish, status = detail
        submit_time, start_time, finish_time, status_text_res = JUtils.get_job_total_stats(
            common_utils.Status.COMPLETED, job_name, tmp_path)
        submit_ts = int(time.mktime(submit_time.timetuple())) if len(
            str(submit_time)) > 0 else 0
        start_ts = int(time.mktime(start_time.timetuple())) if len(
            str(start_time)) > 0 else 0
        finish_ts = int(time.mktime(finish_time.timetuple())) if len(
            str(finish_time)) > 0 else 0
        if (finish_ts != finish):
            #print("\tMust Update")
            DbRequests.update_job_times(detail_id,
                                        int(current_st),
                                        submit_ts,
                                        start_ts,
                                        finish_ts,
                                        status,
                                        debug=False,
                                        no_modify_time=True)
        t1 = time.time()
        # Timer safeguard
        if (t1 - t0) > SAFE_TIME_LIMIT:
            raise Exception(
                "Time limit reached {0:06.2f} seconds on verify_last_completed while reading {1}. Time spent on reading data {2:06.2f} seconds.".format((t1 - t0), job_name, t_data))


class JobTimesUpdater(BackgroundTaskTemplate):
    id = "TASK_JBTMUPDTR"
    trigger_options = {"trigger": "interval", "minutes": 10}

    @classmethod
    def procedure(cls):
        verify_last_completed(1800)