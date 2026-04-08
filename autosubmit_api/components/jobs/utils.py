#!/usr/bin/env python

import datetime
import os
import subprocess
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

from bscearth.utils.date import parse_date

from autosubmit_api.common.utils import Status
from autosubmit_api.persistance.experiment import ExperimentPaths

if TYPE_CHECKING:
    from autosubmit_api.repositories.job_data import ExperimentJobDataModel
    from autosubmit_api.repositories.jobs import JobData


wrapped_title_format = (
    " <span class='badge' style='background-color:#94b8b8'>Wrapped {0} </span>"
)
source_tag = " <span class='badge' style='background-color:#80d4ff'>SOURCE</span>"
target_tag = " <span class='badge' style='background-color:#99ff66'>TARGET</span>"
sync_tag = (
    " <span class='badge' style='background-color:#0066ff; color:white'>SYNC</span>"
)
checkmark_tag = " <span class='badge' style='background-color:#4dffa6'>&#10004;</span>"

completed_tag_with_anchors = (
    " <span class='badge' style='background-color:%B'> %C / %T COMPLETED</span>"
)
running_tag_with_anchors = (
    " <span class='badge' style='background-color:green; color:#fff'>%R RUNNING</span>"
)
queuing_tag_with_anchors = (
    " <span class='badge' style='background-color:pink'>%Q QUEUING</span>"
)
failed_tag_with_anchors = (
    " <span class='badge' style='background-color:red'>%F FAILED</span>"
)
held_tag_with_anchors = (
    " <span class='badge' style='background-color:#fa8072; color:#fff'>%H HELD</span>"
)

# Status.HELD, Status.PREPARED
SUBMIT_STATUS = {
    Status.COMPLETED,
    Status.FAILED,
    Status.QUEUING,
    Status.RUNNING,
    Status.SUBMITTED,
}
START_STATUS = {Status.COMPLETED, Status.FAILED, Status.RUNNING}
FINISH_STATUS = {Status.COMPLETED, Status.FAILED}


def is_a_completed_retrial(fields: List[str]) -> bool:
    """Identifies one line of _TOTAL_STATS file"""
    if len(fields) == 4:
        if fields[3] == "COMPLETED":
            return True
    return False


def get_corrected_submit_time_by_status(status_code: int, submit_time: str) -> str:
    if status_code in SUBMIT_STATUS:
        return submit_time
    return None


def get_corrected_start_time_by_status(status_code: int, start_time: str) -> str:
    if status_code in START_STATUS:
        return start_time
    return None


def get_corrected_finish_time_by_status(status_code: int, finish_time: str) -> str:
    if status_code in FINISH_STATUS:
        return finish_time
    return None


def get_status_text_color(status_code: int) -> str:
    if status_code in [Status.RUNNING, Status.FAILED, Status.HELD]:
        return "#fff"
    return "#000"


def get_folder_checkmark(completed_count: int, jobs_in_folder_count: int) -> str:
    if completed_count == jobs_in_folder_count:
        return checkmark_tag
    return ""


def get_folder_completed_tag(completed_count: int, jobs_in_folder_count: int) -> str:
    tag = ""
    if completed_count == jobs_in_folder_count:
        tag = "<span class='badge' style='background-color:yellow'>"
    else:
        tag = "<span class='badge' style='background-color:#ffffb3'>"
    return "{0} {1} / {2} COMPLETED</span>".format(
        tag, completed_count, jobs_in_folder_count
    )


def get_folder_running_tag(running_count: int) -> str:
    if running_count > 0:
        return " <span class='badge' style='background-color:green; color:#fff'>{0} RUNNING</span>".format(
            running_count
        )
    return ""


def get_folder_queuing_tag(queuing_count: int) -> str:
    if queuing_count > 0:
        return " <span class='badge' style='background-color:pink'>{0} QUEUING</span>".format(
            queuing_count
        )
    return ""


def get_folder_failed_tag(failed_count: int) -> str:
    if failed_count > 0:
        return " <span class='badge' style='background-color:red'>{0} FAILED</span>".format(
            failed_count
        )
    return ""


def get_folder_held_tag(held_count: int) -> str:
    if held_count > 0:
        return " <span class='badge' style='background-color:#fa8072; color:#fff'>{0} HELD</span>".format(
            held_count
        )
    return ""


def get_date_folder_tag(title: str, startdate_count: int) -> str:
    # set the proper color
    if title == "COMPLETED":
        color = "yellow"
    if title == "WAITING":
        color = "#aaa"
    if title == "SUSPENDED":
        color = "orange"
    tag = "<span class='badge' style='background-color:{0}'>".format(color)
    return "{0} {1} / {2} {3} </span>".format(
        tag, startdate_count, startdate_count, title
    )


def get_folder_date_member_title(
    expid: str,
    formatted_date: str,
    member: str,
    date_member_jobs_count: int,
    counters: Dict[int, int],
) -> str:
    return "{0}_{1}_{2} {3}{4}{5}{6}{7}{8}".format(
        expid,
        formatted_date,
        member,
        get_folder_completed_tag(counters[Status.COMPLETED], date_member_jobs_count),
        get_folder_failed_tag(counters[Status.FAILED]),
        get_folder_running_tag(counters[Status.RUNNING]),
        get_folder_queuing_tag(counters[Status.QUEUING]),
        get_folder_held_tag(counters[Status.HELD]),
        get_folder_checkmark(counters[Status.COMPLETED], date_member_jobs_count),
    )


def get_folder_package_title(
    package_name: str, jobs_count: int, counters: Dict[int, int]
) -> str:
    return "Wrapper: {0} {1}{2}{3}{4}{5}{6}".format(
        package_name,
        get_folder_completed_tag(counters[Status.COMPLETED], jobs_count),
        get_folder_failed_tag(counters[Status.FAILED]),
        get_folder_running_tag(counters[Status.RUNNING]),
        get_folder_queuing_tag(counters[Status.QUEUING]),
        get_folder_held_tag(counters[Status.HELD]),
        get_folder_checkmark(counters[Status.COMPLETED], jobs_count),
    )


def convert_int_default(value, default_value=None):
    try:
        return int(value)
    except Exception:
        return default_value


def get_job_total_stats(
    status_code: int, name: str, tmp_path: str
) -> Tuple[datetime.datetime, datetime.datetime, datetime.datetime, str]:
    """
    Receives job data and returns the data from its TOTAL_STATS file in an ordered way.
    Function migrated from the legacy JobList class method _job_running_check()
    :param status_code: Status of job
    :param name: Name of job
    :param tmp_path: Path to the tmp folder of the experiment
    :return: submit time, start time, end time, status
    :rtype: 4-tuple in datetime format
    """
    values = list()
    status_from_job = str(Status.VALUE_TO_KEY[status_code])
    now = datetime.datetime.now()
    submit_time = now
    start_time = now
    finish_time = now
    current_status = status_from_job
    path = os.path.join(tmp_path, name + "_TOTAL_STATS")
    if os.path.exists(path):
        last_line = subprocess.check_output(["tail", "-1", path], text=True)

        values = last_line.split()
        try:
            if status_code in [Status.RUNNING]:
                submit_time = parse_date(values[0]) if len(values) > 0 else now
                start_time = parse_date(values[1]) if len(values) > 1 else submit_time
                finish_time = now
            elif status_code in [Status.QUEUING, Status.SUBMITTED, Status.HELD]:
                submit_time = parse_date(values[0]) if len(values) > 0 else now
                start_time = (
                    parse_date(values[1])
                    if len(values) > 1 and values[0] != values[1]
                    else now
                )
            elif status_code in [Status.COMPLETED]:
                submit_time = parse_date(values[0]) if len(values) > 0 else now
                start_time = parse_date(values[1]) if len(values) > 1 else submit_time
                if len(values) > 3:
                    finish_time = parse_date(values[len(values) - 2])
                else:
                    finish_time = submit_time
            else:
                submit_time = parse_date(values[0]) if len(values) > 0 else now
                start_time = parse_date(values[1]) if len(values) > 1 else submit_time
                finish_time = parse_date(values[2]) if len(values) > 2 else start_time
        except Exception:
            start_time = now
            finish_time = now
            # NA if reading fails
            current_status = "NA"

    current_status = (
        values[3] if (len(values) > 3 and len(values[3]) != 14) else status_from_job
    )
    # TOTAL_STATS last line has more than 3 items, status is different from pkl, and status is not "NA"
    if len(values) > 3 and current_status != status_from_job and current_status != "NA":
        current_status = "SUSPICIOUS"
    return (submit_time, start_time, finish_time, current_status)


def job_times_to_text(minutes_queue: int, minutes_running: int, status: str):
    """
    Return text correpsonding to queue and running time.
    Function migrated from the legacy job.utils
    :param minutes_queue: seconds queuing (actually using seconds)
    :type minutes_queue: int
    :param minutes_running: seconds running (actually using seconds)
    :type minutes_running: int
    :param status: current status
    :type status: string
    :return: string
    """
    if status in ["COMPLETED", "FAILED", "RUNNING"]:
        running_text = (
            "( "
            + str(datetime.timedelta(seconds=minutes_queue))
            + " ) + "
            + str(datetime.timedelta(seconds=minutes_running))
        )
    elif status in ["SUBMITTED", "QUEUING", "HELD", "HOLD"]:
        running_text = "( " + str(datetime.timedelta(seconds=minutes_queue)) + " )"
    elif status in ["NA"]:
        running_text = " <small><i><b>NA</b></i></small>"
    else:
        running_text = ""

    if status == "SUSPICIOUS":
        running_text = running_text + " <small><i><b>SUSPICIOUS</b></i></small>"
    return running_text


def generate_job_html_title(job_name: str, status_color: str, status_text: str) -> str:
    return (
        job_name
        + " <span class='badge' style='background-color: "
        + status_color
        + "'>#"
        + status_text
        + "</span>"
    )


def get_fixed_experiment_times(
    expid: str,
    current_job: "JobData",
    job_last_data: Optional["ExperimentJobDataModel"],
) -> Tuple[int, int, int]:
    # If status is SUSPENDED, set submit/start/finish to 0
    if current_job.status == Status.SUSPENDED or job_last_data is None:
        submit = 0
        start = 0
        finish = 0
    else:
        submit = job_last_data.submit
        start = job_last_data.start
        finish = job_last_data.finish

    # If the status from the historical DB is different from the jobs repo, try other method to get the times
    if not job_last_data or (
        job_last_data
        and job_last_data.status != Status.VALUE_TO_KEY.get(current_job.status)
    ):
        # Try to get the times from the TOTAL_STATS file
        if current_job.status in [
            Status.RUNNING,
            Status.SUBMITTED,
            Status.QUEUING,
            Status.FAILED,
        ]:
            submit, start, finish, _ = get_job_total_stats(
                status_code=current_job.status,
                name=current_job.name,
                tmp_path=ExperimentPaths(expid).tmp_dir,
            )
            submit = int(submit.timestamp())
            start = (
                int(start.timestamp())
                if current_job.status in [Status.RUNNING, Status.FAILED]
                else 0
            )
            finish = (
                int(finish.timestamp()) if current_job.status in [Status.FAILED] else 0
            )
        else:
            submit = start = finish = 0

    return submit, start, finish
