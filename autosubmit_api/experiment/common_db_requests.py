import os
import sys
import string
import time
import pickle
import textwrap
import traceback
import sqlite3
import copy
from datetime import datetime
from collections import OrderedDict
from typing import List, Tuple, Dict

from ..config.basicConfig import BasicConfig
BasicConfig.read()

DB_FILE_AS_TIMES = os.path.join(BasicConfig.DB_DIR, BasicConfig.AS_TIMES_DB) # "/esarchive/autosubmit/as_times.db"
DB_FILES_STATUS = os.path.join(BasicConfig.LOCAL_ROOT_DIR, "as_metadata", "test", BasicConfig.FILE_STATUS_DB) # "/esarchive/autosubmit/as_metadata/test/status.db"
# PATH_DB_DATA = "/esarchive/autosubmit/as_metadata/data/"


def prepare_status_db():
    """
    Creates table of experiment status if it does not exist.
    :return: Map from experiment name to (Id of experiment, Status, Seconds)
    :rtype: Dictionary Key: String, Value: Integer, String, Integer
    """
    conn = create_connection(DB_FILE_AS_TIMES)
    create_table_query = textwrap.dedent(
        '''CREATE TABLE
    IF NOT EXISTS experiment_status (
    exp_id integer PRIMARY KEY,
    name text NOT NULL,
    status text NOT NULL,
    seconds_diff integer NOT NULL,
    modified text NOT NULL,
    FOREIGN KEY (exp_id) REFERENCES experiment (id)
    );''')
    # drop_table_query = ''' DROP TABLE experiment_status '''
    # create_table(conn, drop_table_query)
    create_table(conn, create_table_query)
    current_table = _get_exp_status()
    current_table_expid = dict()
    # print(current_table)
    # print(type(current_table))
    for item in current_table:
        exp_id, expid, status, seconds = item
        current_table_expid[expid] = (exp_id, status, seconds)
    return current_table_expid


def prepare_completed_times_db():
    """
    Creates two tables:
    "experiment_times" that stores general information about experiments' jobs completed updates
    "job_times" that stores information about completed time for jobs in the database as_times.db
    Then retrieves all the experiments data from "experiment_times".
    :return: Dictionary that maps experiment name to experiment data.
    :rtype: Dictionary: Key String, Value 6-tuple (exp_id, name, created, modified, total_jobs, completed_jobs)
    """
    conn = create_connection(DB_FILE_AS_TIMES)
    create_table_header_query = textwrap.dedent(
        '''CREATE TABLE
    IF NOT EXISTS experiment_times (
    exp_id integer PRIMARY KEY,
    name text NOT NULL,
    created int NOT NULL,
    modified int NOT NULL,
    total_jobs int NOT NULL,
    completed_jobs int NOT NULL,
    FOREIGN KEY (exp_id) REFERENCES experiment (id)
    );''')

    create_table_detail_query = textwrap.dedent(
        '''CREATE TABLE
    IF NOT EXISTS job_times (
    detail_id integer PRIMARY KEY AUTOINCREMENT,
    exp_id integer NOT NULL,
    job_name text NOT NULL,
    created integer NOT NULL,
    modified integer NOT NULL,
    submit_time int NOT NULL,
    start_time int NOT NULL,
    finish_time int NOT NULL,
    status text NOT NULL,
    FOREIGN KEY (exp_id) REFERENCES experiment (id)
    );''')

    drop_table_header_query = ''' DROP TABLE experiment_times '''
    drop_table_details_query = ''' DROP TABLE job_times '''
    # create_table(conn, drop_table_details_query)
    # create_table(conn, drop_table_header_query)
    # return
    create_table(conn, create_table_header_query)
    create_table(conn, create_table_detail_query)
    current_table = _get_exp_times()
    current_table_expid = dict()

    for item in current_table:
        try:
            exp_id, name, created, modified, total_jobs, completed_jobs = item
            current_table_expid[name] = (exp_id, int(created), int(
                modified), int(total_jobs), int(completed_jobs))
        except Exception as ex:
            print((traceback.format_exc()))
            print(item)
            print((str(name) + " ~ " + str(created) + "\t" + str(modified)))

    return current_table_expid

# STATUS ARCHIVE


def insert_archive_status(status, alatency, abandwidth, clatency, cbandwidth, rtime):

    try:
        conn = create_connection(DB_FILES_STATUS)
        sql = ''' INSERT INTO archive_status(status, avg_latency, avg_bandwidth, current_latency, current_bandwidth, response_time, modified ) VALUES(?,?,?,?,?,?,?)'''
        # print(row_content)
        cur = conn.cursor()
        cur.execute(sql, (int(status), alatency, abandwidth, clatency,
                          cbandwidth, rtime, datetime.today().strftime('%Y-%m-%d-%H:%M:%S')))
        # print(cur)
        conn.commit()
        return cur.lastrowid
    except Exception as exp:
        print((traceback.format_exc()))
        print(("Error on Insert : " + str(exp)))


def get_last_read_archive_status():
    """

    :return: status, avg. latency, avg. bandwidth, current latency, current bandwidth, response time, date
    :rtype: 7-tuple
    """
    try:
        conn = create_connection(DB_FILES_STATUS)
        sql = "SELECT status, avg_latency, avg_bandwidth, current_latency, current_bandwidth, response_time, modified FROM archive_status order by rowid DESC LIMIT 1"
        cur = conn.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        status, alatency, abandwidth, clatency, cbandwidth, rtime, date = rows[0]
        return (status, alatency, abandwidth, clatency, cbandwidth, rtime, date)
        # print(rows)
    except Exception as exp:
        print((traceback.format_exc()))
        print(("Error on Get Last : " + str(exp)))
        return (False, None, None, None, None, None, None)

# INSERTIONS


def insert_experiment_times_header(expid, timest, total_jobs, completed_jobs, debug=False, log=None):
    """
    Inserts into experiment times header. Requires ecearth.db connection.
    :param expid: Experiment name
    :type expid: String
    :param timest: timestamp of the pkl last modified date
    :type timest: Integer
    :param total_jobs: Total number of jobs
    :type total_jobs: Integer
    :param completed_jobs: Number of completed jobs
    :type completed_jobs: Integer
    :param debug: Flag (testing purposes)
    :type debug: Boolean
    :param conn_ecearth: ecearth.db connection
    :type conn: sqlite3 connection
    :return: exp_id of the experiment (not the experiment name)
    :rtype: Integer
    """
    try:
        current_id = _get_id_db(create_connection(BasicConfig.DB_PATH), expid)
        if (current_id):
            if (debug == True):
                print(("INSERTING INTO EXPERIMENT_TIMES " + str(current_id) + "\t" + str(expid) +
                      "\t" + str(timest) + "\t" + str(total_jobs) + "\t" + str(completed_jobs)))
                return current_id
            row_content = (current_id, expid, int(timest), int(timest), total_jobs, completed_jobs)
            result = _create_exp_times(row_content)
            return current_id
        else:
            return -1
    except sqlite3.Error as e:
        print(("Error on Insert : " + str(type(e).__name__)))
        print(current_id)


def _create_exp_times(row_content):
    """
    Create experiment times
    :param conn:
    :param details:
    :return:
    """
    try:
        conn = create_connection(DB_FILE_AS_TIMES)
        sql = ''' INSERT INTO experiment_times(exp_id, name, created, modified, total_jobs, completed_jobs) VALUES(?,?,?,?,?,?) '''
        # print(row_content)
        cur = conn.cursor()
        cur.execute(sql, row_content)
        # print(cur)
        conn.commit()
        return cur.lastrowid
    except sqlite3.Error as e:
        print(("Error on Insert : " + str(type(e).__name__)))
        print(row_content)


def create_job_times(conn, exp_id, job_name, timest, submit_time, start_time, finish_time, status, debug=False):
    """
    Create job_times detail register.
    :param conn: connection to as_times.db
    :type conn: sqlite3 connection
    :param exp_id: Id of experiment (not name)
    :type exp_id: Integer
    :param job_name: Name of job
    :type job_name: String
    :param timest: Timestamp of the last modified date of the pkl file
    :type timest: Integer
    :param submit_time: Timestamp of the submit time of the job
    :type submit_time: Integer
    :param start_time: Timestamp of the start time of the job
    :type start_time: Integer
    :param finish_time: Timestamp of the finish time of the job
    :type finish_time: Integer
    :param status: Status of the job
    :type status: String
    :param debug: Flag for testing purposes
    :type debug: Boolean
    :return: Id of detail
    :rtype: Integer
    """

    try:
        if (debug == True):
            print(("INSERTING INTO JOB_TIMES " + str(exp_id) + " ~ " + str(job_name) + " ~ " + str(timest) +
                  "\t" + str(submit_time) + "\t" + str(start_time) + "\t" + str(finish_time) + "\t" + str(status)))
            return
        sql = ''' INSERT INTO job_times(exp_id, job_name, created, modified, submit_time, start_time, finish_time, status) VALUES(?,?,?,?,?,?,?,?) '''
        cur = conn.cursor()
        cur.execute(sql, (exp_id, job_name, timest, timest,
                          submit_time, start_time, finish_time, status))
        # Commit outside the loop
        conn.commit()
        return cur.lastrowid
    except sqlite3.Error as e:
        print((traceback.format_exc()))
        print(("Error on Insert : " + str(type(e).__name__)))
        print((exp_id, job_name, timest, timest,
               submit_time, start_time, finish_time, status))


def create_many_job_times(list_job):
    try:
        conn = create_connection(DB_FILE_AS_TIMES)
        sql = ''' INSERT INTO job_times(exp_id, job_name, created, modified, submit_time, start_time, finish_time, status) VALUES(?,?,?,?,?,?,?,?) '''
        # print(row_content)
        cur = conn.cursor()
        cur.executemany(sql, list_job)
        # print(cur)
        # Commit outside the loop
        conn.commit()
    except sqlite3.Error as e:
        print((traceback.format_exc()))
        print(("Error on Insert : " + str(type(e).__name__)))
        # print((exp_id, job_name, timest, timest,
        #        submit_time, start_time, finish_time, status))


def _insert_into_ecearth_details(exp_id, user, created, model, branch, hpc):
    """
    Inserts into the details table of ecearth.db
    :return: Id
    :rtype: int
    """
    conn = create_connection(BasicConfig.DB_PATH)
    if conn:
        try:
            sql = ''' INSERT INTO details(exp_id, user, created, model, branch, hpc) VALUES(?,?,?,?,?,?) '''
            cur = conn.cursor()
            cur.execute(sql, (exp_id, user, created, model, branch, hpc))
            conn.commit()
            return cur.lastrowid
        except Exception as exp:
            print(exp)
    return False


def insert_experiment_status(conn, expid, seconds_diff):
    """
    Inserts into table of status if it does not exist and updates status. Requires conn to ecearth.db.\n
    :param conn: ecearth.db connection
    :type conn: sqlite3 connection object
    :param expid: Experiment name
    :type expid: str
    :param seconds_diff: time limit in seconds
    :type seconds_diff: int
    :return: Experiment id
    :rtype: int
    """
    # print("Looking {}".format(expid))
    current_id = _get_id_db(conn, expid)
    conn = create_connection(DB_FILE_AS_TIMES)
    if (current_id):
        try:
            # print("Inserting {} {}".format(current_id, expid))
            row_content = (current_id, expid, "RUNNING", int(
                seconds_diff), datetime.today().strftime('%Y-%m-%d-%H:%M:%S'))
            result = _create_exp_status(row_content)
        except sqlite3.Error as exp:
            print(("error on insert_experiment_status {0} {1}".format(
                current_id, expid)))
            print((traceback.format_exc()))
            return current_id
        # print(row_content)

    return current_id


def create_connection(db_file):
    # type: (str) -> sqlite3.Connection
    """
    Create a database connection to the SQLite database specified by db_file.
    :param db_file: database file name
    :return: Connection object or None
    """
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except Exception as exp:
        print(exp)


def create_table(conn, create_table_sql):
    """ create a table from the create_table_sql statement
    :param conn: Connection object
    :param create_table_sql: a CREATE TABLE statement
    :return:
    """
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except Exception as e:
        print(e)


# SELECTS

def get_completed_times_detail():
    """
    Gets all details in job times as a Dictionary of dictionaries
    """
    # experiments = get_exps(conn)
    try:
        # conn = create_connection(DB_FILE_AS_TIMES)
        all_detail = _get_all_job_times()
        exps = dict()
        for item in all_detail:
            detail_id, exp_id, job_name, created, modified, submit_time, start_time, finish_time, status = item
            if exp_id not in list(exps.keys()):
                exps[exp_id] = dict()
            exps[exp_id][job_name] = (
                submit_time, start_time, finish_time, status, detail_id)
        return exps
    except Exception as ex:
        print((traceback.format_exc()))


def get_times_detail(exp_id):
    """
    Gets the current detail of the experiment from job_times
    :param exp_id: Id of the experiment
    :type exp_id: Integer
    :return: Dictionary Key: Job Name, Values: 5-tuple (submit time, start time, finish time, status, detail id)
    :rtype: dict
    """
    # conn = create_connection(DB_FILE_AS_TIMES)
    try:
        current_table_detail = dict()
        current_table = _get_job_times(exp_id)
        if current_table is None:
            return None
        for item in current_table:
            detail_id, exp_id, job_name, created, modified, submit_time, start_time, finish_time, status = item
            current_table_detail[job_name] = (
                submit_time, start_time, finish_time, status, detail_id)
        return current_table_detail
    except Exception as exp:
        print((traceback.format_exc()))
        return None


def get_times_detail_by_expid(conn, expid):
    """
    Gets the detail of times of the experiment by expid (name of experiment).\n
    :param conn: ecearth.db connection
    :rtype conn: sqlite3 connection
    :param expid: Experiment name
    :type expid: str
    :return: Dictionary Key: Job Name, Values: 5-tuple (submit time, start time, finish time, status, detail id)
    :rtype: dict
    """
    # conn = create_connection(DB_FILE_AS_TIMES)
    exp_id = _get_id_db(conn, expid)
    if (exp_id):
        return get_times_detail(exp_id)
    else:
        return None


def get_experiment_status():
    """
    Gets table experiment_status as dictionary
    conn is expected to reference as_times.db
    """
    # conn = create_connection(DB_FILE_AS_TIMES)
    experiment_status = dict()
    current_table = _get_exp_status()
    for item in current_table:
        exp_id, name, status, seconds_diff = item
        experiment_status[name] = status
    return experiment_status


def get_currently_running_experiments():
    """
    Gets the list of currently running experiments ordered by total_jobs
    Connects to AS_TIMES
    :return: map of expid -> total_jobs
    :rtype: OrderedDict() str -> int
    """
    experiment_running = OrderedDict()
    current_running = _get_exp_only_active()
    if current_running:
        for item in current_running:
            name, status, total_jobs = item
            experiment_running[name] = total_jobs
    return experiment_running


def get_specific_experiment_status(expid):
    """
    Gets the current status from database.\n
    :param expid: Experiment name
    :type expid: str
    :return: name of experiment and status
    :rtype: 2-tuple (name, status)
    """
    exp_id, name, status, seconds_diff = _get_specific_exp_status(expid)
    print(("{} {} {} {}".format(exp_id, name, status, seconds_diff)))
    return (name, status)


def get_experiment_times():
    # type: () -> Dict[str, Tuple[int, int, int]]
    """
    Gets table experiment_times as dictionary
    conn is expected to reference as_times.db
    """
    # conn = create_connection(DB_FILE_AS_TIMES)
    experiment_times = dict()
    current_table = _get_exp_times()
    for item in current_table:
        exp_id, name, created, modified, total_jobs, completed_jobs = item
        experiment_times[name] = (total_jobs, completed_jobs, modified)
        # if extended == True:
        #     experiment_times[name] = (total_jobs, completed_jobs, created, modified)
    return experiment_times


def get_experiment_times_by_expid(expid):
    """[summary]
    :return: exp_id, total number of jobs, number of completed jobs
    :rtype 3-tuple: (int, int, int)
    """
    current_row = _get_exp_times_by_expid(expid)
    if current_row:
        exp_id, name, created, modified, total_jobs, completed_jobs = current_row
        return (exp_id, total_jobs, completed_jobs)
    return None


def get_experiment_times_group():
    """
    Gets table experiment_times as dictionary id -> name
    conn is expected to reference as_times.db
    """
    experiment_times = dict()
    current_table = _get_exp_times()
    for item in current_table:
        exp_id, name, created, modified, total_jobs, completed_jobs = item
        if name not in list(experiment_times.keys()):
            experiment_times[name] = list()
        experiment_times[name].append(exp_id)
        # if extended == True:
        #     experiment_times[name] = (total_jobs, completed_jobs, created, modified)
    return experiment_times


def get_exps(conn):
    """
    Get exp ids
    :param conn: ecearth.db connection
    :param expid:
    :return:
    """
    # SQLite always return a unicode object, but we can change this
    # behaviour with the next sentence
    conn.text_factory = str
    cur = conn.cursor()
    cur.execute(
        "SELECT name FROM experiment WHERE autosubmit_version IS NOT NULL")
    rows = cur.fetchall()
    return rows


def _get_exps_complete(conn):
    """
    Get exp all row information
    :param conn: ecearth.db connection
    :param expid:
    :return:
    """
    # SQLite always return a unicode object, but we can change this
    # behaviour with the next sentence
    conn.text_factory = str
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM experiment WHERE autosubmit_version IS NOT NULL")
    rows = cur.fetchall()
    return rows


def get_exps_base():
    """
    Get exp name and id from experiment table in ecearth.db
    :param conn: ecearth.db connection
    :param expid:
    :return:
    """
    conn = create_connection(BasicConfig.DB_PATH)
    result = dict()
    conn.text_factory = str
    cur = conn.cursor()
    cur.execute(
        "SELECT name, id FROM experiment WHERE autosubmit_version IS NOT NULL")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    if (rows):
        for row in rows:
            _name, _id = row
            result[_name] = _id
    else:
        return None
    return result


def get_exps_detailed_complete():
    """
    Get information from details table
    :param conn: ecearth.db connection
    :param expid:
    :return: Dictionary exp_id -> (user, created, model, branch, hpc)
    """
    all_details = _get_exps_detailed_complete(create_connection(BasicConfig.DB_PATH))
    result = dict()
    if (all_details):
        for item in all_details:
            exp_id, user, created, model, branch, hpc = item
            result[exp_id] = (user, created, model, branch, hpc)
    return result


def get_latest_completed_jobs(seconds=300):
    """
    Get latest completed jobs
    """
    result = dict()
    latest_completed_detail = _get_latest_completed_jobs(seconds)
    if (latest_completed_detail):
        for item in latest_completed_detail:
            detail_id, exp_id, job_name, created, modified, submit_time, start_time, finish_time, status = item
            result[job_name] = (detail_id, submit_time,
                                start_time, finish_time, status)
    return result


def _get_exps_detailed_complete(conn):
    """
    Get information from details table
    :param conn: ecearth.db connection
    :param expid:
    :return:
    """
    conn.text_factory = str
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM details")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def _get_exp_times():
    # type: () -> List[Tuple[int, str, int, int, int, int]]
    """
    Get all experiments from table experiment_times.\n
    :return: Row content (exp_id, name, created, modified, total_jobs, completed_jobs)
    :rtype: 6-tuple (int, str, int, int, int, int)
    """
    try:
        conn = create_connection(os.path.join(BasicConfig.DB_DIR, BasicConfig.AS_TIMES_DB))
        conn.text_factory = str
        cur = conn.cursor()
        cur.execute(
            "SELECT exp_id, name, created, modified, total_jobs, completed_jobs FROM experiment_times")
        rows = cur.fetchall()
        conn.close()
        return rows
    except Exception as exp:
        print((traceback.format_exc()))
        return list()


def _get_exp_times_by_expid(expid):
    """
    Returns data from experiment_time table by expid.

    :param expid: expid/name
    :type expid: str
    :return: Row content (exp_id, name, created, modified, total_jobs, completed_jobs)
    :rtype: 6-tuple (int, str, str, str, int, int)
    """
    try:
        conn = create_connection(os.path.join(BasicConfig.DB_DIR, BasicConfig.AS_TIMES_DB))
        conn.text_factory = str
        cur = conn.cursor()
        cur.execute(
            "SELECT exp_id, name, created, modified, total_jobs, completed_jobs FROM experiment_times WHERE name=?", (expid,))
        rows = cur.fetchall()
        conn.close()
        return rows[0] if len(rows) > 0 else None
    except Exception as exp:
        print((traceback.format_exc()))
        return None


def _get_job_times(exp_id):
    """
    Get exp job times detail for a given expid from job_times.
    :param exp_id: Experiment id (not name)
    :type exp_id: Integer
    :return: Detail content
    :rtype: list of 9-tuple: (detail_id, exp_id, job_name, created, modified, submit_time, start_time, finish_time, status)
    """
    try:
        conn = create_connection(os.path.join(BasicConfig.DB_DIR, BasicConfig.AS_TIMES_DB))
        cur = conn.cursor()
        cur.execute("SELECT detail_id, exp_id, job_name, created, modified, submit_time, start_time, finish_time, status FROM job_times WHERE exp_id=?", (exp_id,))
        rows = cur.fetchall()
        conn.close()
        return rows
    except Exception as ex:
        print((traceback.format_exc()))
        print((str(exp_id)))
        print((str(ex)))
        return None


def _get_latest_completed_jobs(seconds=300):
    """
    get latest completed jobs, defaults at 300 seconds, 5 minutes
    """
    current_ts = time.time()
    try:
        conn = create_connection(os.path.join(BasicConfig.DB_DIR, BasicConfig.AS_TIMES_DB))
        cur = conn.cursor()
        cur.execute("SELECT detail_id, exp_id, job_name, created, modified, submit_time, start_time, finish_time, status FROM job_times WHERE (? - modified)<=? AND status='COMPLETED'", (current_ts, seconds))
        rows = cur.fetchall()
        conn.close()
        return rows
    except Exception as ex:
        print((traceback.format_exc()))
        print((str(seconds)))
        print((str(ex)))
        return None


def _get_all_job_times():
    """
    Get content from job_times detail for all experiments.\n
    :return: (detail_id, exp_id, job_name, created, modified, submit, start, finish_time, status)
    :rtype: 9-tuple (int, int, str, int, int, int, int, int, str)
    """
    try:
        conn = create_connection(os.path.join(BasicConfig.DB_DIR, BasicConfig.AS_TIMES_DB))
        cur = conn.cursor()
        cur.execute(
            "SELECT detail_id, exp_id, job_name, created, modified, submit_time, start_time, finish_time, status FROM job_times")
        rows = cur.fetchall()
        conn.close()
        return rows
    except Exception as exp:
        print("Error while trying to _get_all_job_times")
        print((traceback.format_exc()))
        return None


def _delete_from_job_times_detail(detail_id):
    """
    Deletes a job that is no longer included in the experiment.

    :param detail_id: id of row
    :type detail_id: int
    """
    try:
        conn = create_connection(os.path.join(BasicConfig.DB_DIR, BasicConfig.AS_TIMES_DB))
        cur = conn.cursor()
        #print("Cursor defined")
        cur.execute(
            "DELETE FROM job_times WHERE detail_id=?", (detail_id,))
        # print(cur.rowcount)
        cur.close()
        conn.commit()
        conn.close()

        # No reliable way to get any feedback from cursor at this point, so let's just return 1
        return True
    except Exception as exp:
        print(("Error while trying to delete " +
              str(detail_id) + " from job_times."))
        print((traceback.format_exc()))
        return None


def _delete_many_from_job_times_detail(detail_list):
    try:
        conn = create_connection(os.path.join(BasicConfig.DB_DIR, BasicConfig.AS_TIMES_DB))
        cur = conn.cursor()
        #print("Cursor defined")
        cur.executemany(
            "DELETE FROM job_times WHERE detail_id=?", detail_list)
        # print(cur.rowcount)
        cur.close()
        conn.commit()
        conn.close()
        # No reliable way to get any feedback from cursor at this point, so let's just return 1
        return True
    except Exception as exp:
        # print("Error while trying to delete " +
        #       str(detail_id) + " from job_times.")
        print((traceback.format_exc()))
        return None


def delete_experiment_data(exp_id):
    # type: (int) -> bool
    """
    Deletes experiment data from experiment_times and job_times in as_times.db

    :param exp_id: Id of experiment
    :type exp_id: int
    """
    deleted_e = _delete_from_experiment_times(exp_id)
    deleted_j = _delete_from_job_times(exp_id)
    print(("Main exp " + str(deleted_e) + "\t" + str(deleted_j)))
    if deleted_e and deleted_j:
        return True
    return False


def _delete_from_experiment_times(exp_id):
    """
    Deletes an experiment from experiment_times in as_times.db

    :param exp_id: Id of experiment
    :type exp_id: int
    """
    try:
        conn = create_connection(os.path.join(BasicConfig.DB_DIR, BasicConfig.AS_TIMES_DB))
        cur = conn.cursor()
        cur.execute("DELETE FROM experiment_times WHERE exp_id=?", (exp_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as exp:
        print(("Error while trying to delete " +
              str(exp_id) + " from experiment_times."))
        print((traceback.format_exc()))
        return None


def _delete_from_job_times(exp_id):
    """
    Deletes an experiment from job_times in as_times.db

    :param exp_id: Id of experiment
    :type exp_id: int
    """
    try:
        conn = create_connection(os.path.join(BasicConfig.DB_DIR, BasicConfig.AS_TIMES_DB))
        cur = conn.cursor()
        cur.execute("DELETE FROM job_times WHERE exp_id=?", (exp_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as exp:
        print(("Error while trying to delete " +
              str(exp_id) + " from job_times."))
        print((traceback.format_exc()))
        return None


def _get_exp_status():
    """
    Get all registers from experiment_status.\n
    :return: row content: exp_id, name, status, seconds_diff
    :rtype: 4-tuple (int, str, str, int)
    """
    try:
        conn = create_connection(os.path.join(BasicConfig.DB_DIR, BasicConfig.AS_TIMES_DB))
        conn.text_factory = str
        cur = conn.cursor()
        cur.execute(
            "SELECT exp_id, name, status, seconds_diff FROM experiment_status")
        rows = cur.fetchall()
        return rows
    except Exception as exp:
        print((traceback.format_exc()))
        return dict()


def _get_exp_only_active():
    """
    Get all registers of experiments ACTIVE
    """
    try:
        conn = create_connection(os.path.join(BasicConfig.DB_DIR, BasicConfig.AS_TIMES_DB))
        conn.text_factory = str
        cur = conn.cursor()
        cur.execute("select name, status, total_jobs from currently_running")
        rows = cur.fetchall()
        return rows
    except Exception as exp:
        print((traceback.format_exc()))
        print(exp)
        return None


def _get_specific_exp_status(expid):
    """
    Get all registers from experiment_status.\n
    :return: row content: exp_id, name, status, seconds_diff
    :rtype: 4-tuple (int, str, str, int)
    """
    try:
        # print("Honk")
        conn = create_connection(os.path.join(BasicConfig.DB_DIR, BasicConfig.AS_TIMES_DB))
        cur = conn.cursor()
        cur.execute(
            "SELECT exp_id, name, status, seconds_diff FROM experiment_status WHERE name=?", (expid,))
        row = cur.fetchone()
        if row == None:
            return (0, expid, "NOT RUNNING", 0)
        # print(row)
        return row
    except Exception as exp:
        print((traceback.format_exc()))
        return (0, expid, "NOT RUNNING", 0)


def _get_exp_status_running():
    """
    Get RUNNING experiments from from experiment_status.\n
    :return: row content: exp_id, name, status, seconds_diff
    :rtype: 4-tuple (int, str, str, int)
    """
    try:
        conn = create_connection(os.path.join(BasicConfig.DB_DIR, BasicConfig.AS_TIMES_DB))
        conn.text_factory = str
        cur = conn.cursor()
        cur.execute(
            "SELECT exp_id, name, status, seconds_diff FROM experiment_status WHERE status='RUNNING'")
        rows = cur.fetchall()
        return rows
    except sqlite3.Error as e:
        print("Error on _get_exp_status_running")


def _create_exp_status(row_content):
    """
    Create experiment status
    :param conn:
    :param details:
    :return:
    """
    try:
        conn = create_connection(os.path.join(BasicConfig.DB_DIR, BasicConfig.AS_TIMES_DB))
        sql = ''' INSERT INTO experiment_status(exp_id, name, status, seconds_diff, modified) VALUES(?,?,?,?,?) '''
        # print(row_content)
        cur = conn.cursor()
        cur.execute(sql, row_content)
        # print(cur)
        conn.commit()
        return cur.lastrowid
    except sqlite3.Error as e:
        print(row_content)
        print(("Error on Insert : " + str(type(e).__name__)))


def _get_id_db(conn, expid):
    """
    Get exp_id of the experiment (different than the experiment name).
    :param conn: ecearth.db connection
    :type conn: sqlite3 connection
    :param expid: Experiment name
    :type expid: String
    :return: Id of the experiment
    :rtype: Integer or None
    """
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM experiment WHERE name=?", (expid,))
        row = cur.fetchone()
        return row[0]
    except Exception as exp:
        print(("Couldn't get exp_id for {0}".format(expid)))
        return None


# UPDATES


def update_exp_status(expid, status, seconds_diff):
    """
    Update existing experiment_status.
    :param expid: Experiment name
    :type expid: String
    :param status: Experiment status
    :type status: String
    :param seconds_diff: Indicator of how long it has been active since the last time it was checked
    :type seconds_diff: Integer
    :return: Id of register
    :rtype: Integer
    """
    try:
        conn = create_connection(os.path.join(BasicConfig.DB_DIR, BasicConfig.AS_TIMES_DB))
        sql = ''' UPDATE experiment_status SET status = ?, seconds_diff = ?, modified = ? WHERE name = ? '''
        cur = conn.cursor()
        cur.execute(sql, (status, seconds_diff,
                          datetime.today().strftime('%Y-%m-%d-%H:%M:%S'), expid))
        conn.commit()
        return cur.lastrowid
    except sqlite3.Error as e:
        print(("Error while trying to update " +
              str(expid) + " in experiment_status."))
        print((traceback.format_exc()))
        print(("Error on Update: " + str(type(e).__name__)))


def _update_ecearth_details(exp_id, user, created, model, branch, hpc):
    """
    Updates ecearth.db table details.
    """
    conn = create_connection(BasicConfig.DB_PATH)
    if conn:
        try:
            sql = ''' UPDATE details SET user=?, created=?, model=?, branch=?, hpc=? where exp_id=? '''
            cur = conn.cursor()
            cur.execute(sql, (user, created, model, branch, hpc, exp_id))
            conn.commit()
            return True
        except Exception as exp:
            print(exp)
            return False
    return False


def update_experiment_times(exp_id, modified, completed_jobs, total_jobs, debug=False):
    """
    Update existing experiment times header
    """
    try:
        conn = create_connection(os.path.join(BasicConfig.DB_DIR, BasicConfig.AS_TIMES_DB))
        if (debug == True):
            print(("UPDATE experiment_times " + str(exp_id) + "\t" +
                  str(completed_jobs) + "\t" + str(total_jobs)))
            return
        sql = ''' UPDATE experiment_times SET modified = ?, completed_jobs = ?, total_jobs = ? WHERE exp_id = ? '''
        cur = conn.cursor()
        cur.execute(sql, (int(modified), completed_jobs, total_jobs, exp_id))
        conn.commit()
        # print("Updated header")
        return exp_id
    except sqlite3.Error as e:
        print(("Error while trying to update " +
              str(exp_id) + " in experiment_times."))
        print((traceback.format_exc()))
        print(("Error on Update: " + str(type(e).__name__)))


def update_experiment_times_only_modified(exp_id, modified):
    try:
        conn = create_connection(os.path.join(BasicConfig.DB_DIR, BasicConfig.AS_TIMES_DB))
        sql = ''' UPDATE experiment_times SET modified = ? WHERE exp_id = ? '''
        cur = conn.cursor()
        cur.execute(sql, (int(modified), exp_id))
        conn.commit()
        # print("Updated header")
        return exp_id
    except sqlite3.Error as e:
        print(("Error while trying to update " +
              str(exp_id) + " in experiment_times."))
        print((traceback.format_exc()))
        print(("Error on Update: " + str(type(e).__name__)))


def update_job_times(detail_id, modified, submit_time, start_time, finish_time, status, debug=False, no_modify_time=False):
    """
    Update single experiment job detail \n
    :param conn: Connection to as_times.db. \n
    :type conn: sqlite3 connection. \n
    :param detail_id: detail_id in as_times.job_times. \n
    :type detail_id: Integer. \n
    :param modified: Timestamp of current date of pkl \n
    :type modified: Integer. \n
    """
    try:
        conn = create_connection(os.path.join(BasicConfig.DB_DIR, BasicConfig.AS_TIMES_DB))
        if (debug == True):
            print(("UPDATING JOB TIMES " + str(detail_id) + " ~ " + str(modified) + "\t" +
                  str(submit_time) + "\t" + str(start_time) + "\t" + str(finish_time) + "\t" + str(status)))
            return
        if no_modify_time == False:
            sql = ''' UPDATE job_times SET modified = ?, submit_time = ?, start_time = ?, finish_time = ?, status = ? WHERE detail_id = ? '''
            cur = conn.cursor()
            cur.execute(sql, (modified, submit_time, start_time,
                              finish_time, status, detail_id))
            # Commit outside the loop
            conn.commit()
            cur.close()
            conn.close()
        else:
            sql = ''' UPDATE job_times SET submit_time = ?, start_time = ?, finish_time = ?, status = ? WHERE detail_id = ? '''
            cur = conn.cursor()
            cur.execute(sql, (submit_time, start_time,
                              finish_time, status, detail_id))
            # Commit outside the loop
            conn.commit()
            cur.close()
            conn.close()

    except sqlite3.Error as e:
        print(("Error while trying to update " +
              str(detail_id) + " in job_times."))
        print((traceback.format_exc()))
        print(("Error on Update: " + str(type(e).__name__)))


def update_many_job_times(list_jobs):
    try:
        conn = create_connection(os.path.join(BasicConfig.DB_DIR, BasicConfig.AS_TIMES_DB))
        sql = ''' UPDATE job_times SET modified = ?, submit_time = ?, start_time = ?, finish_time = ?, status = ? WHERE detail_id = ? '''
        cur = conn.cursor()
        cur.executemany(sql, list_jobs)
        # Commit outside the loop
        conn.commit()
        cur.close()
        conn.close()
    except sqlite3.Error as e:
        print("Error while trying to update many in update_many_job_times.")
        print((traceback.format_exc()))
        print(("Error on Update: " + str(type(e).__name__)))
