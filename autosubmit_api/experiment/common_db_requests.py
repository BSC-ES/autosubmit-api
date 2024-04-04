import os
import traceback
import sqlite3
from datetime import datetime
from autosubmit_api.logger import logger
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.database import tables
from autosubmit_api.database.common import create_as_times_db_engine

APIBasicConfig.read()
DB_FILES_STATUS = os.path.join(
    APIBasicConfig.LOCAL_ROOT_DIR, "as_metadata", "test", APIBasicConfig.FILE_STATUS_DB
)  # "/esarchive/autosubmit/as_metadata/test/status.db"


# STATUS ARCHIVE # Might be removed soon


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
    except Exception as exc:
        logger.error(exc)


def insert_archive_status(status, alatency, abandwidth, clatency, cbandwidth, rtime):

    try:
        with create_connection(DB_FILES_STATUS) as conn:
            sql = """ INSERT INTO archive_status(status, avg_latency, avg_bandwidth, current_latency, current_bandwidth, response_time, modified ) VALUES(?,?,?,?,?,?,?)"""
            cur = conn.cursor()
            cur.execute(
                sql,
                (
                    int(status),
                    alatency,
                    abandwidth,
                    clatency,
                    cbandwidth,
                    rtime,
                    datetime.today().strftime("%Y-%m-%d-%H:%M:%S"),
                ),
            )
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
        with create_connection(DB_FILES_STATUS) as conn:
            sql = "SELECT status, avg_latency, avg_bandwidth, current_latency, current_bandwidth, response_time, modified FROM archive_status order by rowid DESC LIMIT 1"
            cur = conn.cursor()
            cur.execute(sql)
            rows = cur.fetchall()
            status, alatency, abandwidth, clatency, cbandwidth, rtime, date = rows[0]
            return (status, alatency, abandwidth, clatency, cbandwidth, rtime, date)
    except Exception as exp:
        print((traceback.format_exc()))
        print(("Error on Get Last : " + str(exp)))
        return (False, None, None, None, None, None, None)


# SELECTS


def get_experiment_status():
    """
    Gets table experiment_status as dictionary
    conn is expected to reference as_times.db
    """
    experiment_status = dict()
    try:
        with create_as_times_db_engine().connect() as conn:
            cursor = conn.execute(tables.experiment_status_table.select())
            for row in cursor:
                experiment_status[row.name] = row.status
    except Exception as exc:
        logger.error(f"Exception while reading experiment_status: {exc}")
        logger.error(traceback.format_exc())
    return experiment_status


def get_specific_experiment_status(expid):
    """
    Gets the current status from database.\n
    :param expid: Experiment name
    :type expid: str
    :return: name of experiment and status
    :rtype: 2-tuple (name, status)
    """
    try:
        with create_as_times_db_engine().connect() as conn:
            row = conn.execute(
                tables.experiment_status_table.select().where(
                    tables.experiment_status_table.c.name == expid
                )
            ).one_or_none()
    except Exception as exc:
        logger.error(f"Exception while reading experiment_status for {expid}: {exc}")
        logger.error(traceback.format_exc())
    if row:
        return (row.name, row.status)
    return (expid, "NOT RUNNING")
