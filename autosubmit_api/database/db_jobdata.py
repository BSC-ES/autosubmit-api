#!/usr/bin/env python

# Copyright 2015 Earth Sciences Department, BSC-CNS

# This file is part of Autosubmit.

# Autosubmit is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# Autosubmit is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with Autosubmit.  If not, see <http://www.gnu.org/licenses/>.

import os
import time
import textwrap
import traceback
import pysqlite3 as sqlite3
import collections
import portalocker
from datetime import datetime, timedelta
from json import loads
from time import mktime
# from networkx import DiGraph
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.monitor.monitor import Monitor
from autosubmit_api.autosubmit_legacy.job.job_utils import job_times_to_text, getTitle
from autosubmit_api.performance.utils import calculate_ASYPD_perjob
from autosubmit_api.components.jobs.job_factory import SimJob
from autosubmit_api.common.utils import get_jobs_with_no_outliers, Status, datechunk_to_year
# from autosubmitAPIwu.job.job_list
# import autosubmitAPIwu.experiment.common_db_requests as DbRequests
from bscearth.utils.date import Log
from typing import List


# Version 15 includes out err MaxRSS AveRSS and rowstatus
CURRENT_DB_VERSION = 15  # Used to be 10 or 0
DB_VERSION_SCHEMA_CHANGES = 12
DB_EXPERIMENT_HEADER_SCHEMA_CHANGES = 14
_debug = True
JobItem_10 = collections.namedtuple('JobItem', ['id', 'counter', 'job_name', 'created', 'modified', 'submit', 'start', 'finish',
                                                'status', 'rowtype', 'ncpus', 'wallclock', 'qos', 'energy', 'date', 'section', 'member', 'chunk', 'last', 'platform', 'job_id', 'extra_data'])
JobItem_12 = collections.namedtuple('JobItem', ['id', 'counter', 'job_name', 'created', 'modified', 'submit', 'start', 'finish',
                                                'status', 'rowtype', 'ncpus', 'wallclock', 'qos', 'energy', 'date', 'section', 'member', 'chunk', 'last', 'platform', 'job_id', 'extra_data', 'nnodes', 'run_id'])
JobItem_15 = collections.namedtuple('JobItem', ['id', 'counter', 'job_name', 'created', 'modified', 'submit', 'start', 'finish',
                                                'status', 'rowtype', 'ncpus', 'wallclock', 'qos', 'energy', 'date', 'section', 'member', 'chunk', 'last', 'platform', 'job_id', 'extra_data', 'nnodes', 'run_id', 'MaxRSS', 'AveRSS', 'out', 'err', 'rowstatus'])

ExperimentRunItem = collections.namedtuple('ExperimentRunItem', [
                                           'run_id', 'created', 'start', 'finish', 'chunk_unit', 'chunk_size', 'completed', 'total', 'failed', 'queuing', 'running', 'submitted'])
ExperimentRunItem_14 = collections.namedtuple('ExperimentRunItem', [
    'run_id', 'created', 'start', 'finish', 'chunk_unit', 'chunk_size', 'completed', 'total', 'failed', 'queuing', 'running', 'submitted', 'suspended', 'metadata'])

ExperimentRow = collections.namedtuple(
    'ExperimentRow', ['exp_id', 'expid', 'status', 'seconds'])

JobRow = collections.namedtuple(
    'JobRow', ['name', 'queue_time', 'run_time', 'status', 'energy', 'submit', 'start', 'finish', 'ncpus', 'run_id'])


class ExperimentRun():

    def __init__(self, run_id, created=None, start=0, finish=0, chunk_unit="NA", chunk_size=0, completed=0, total=0, failed=0, queuing=0, running=0, submitted=0, suspended=0, metadata="", modified=None):
        self.run_id = run_id
        self.created = created if created else datetime.today().strftime('%Y-%m-%d-%H:%M:%S')
        self.start = start
        self.finish = finish
        self.chunk_unit = chunk_unit
        self.chunk_size = chunk_size
        self.submitted = submitted
        self.queuing = queuing
        self.running = running
        self.completed = completed
        self.failed = failed
        self.total = total
        self.suspended = suspended
        self.metadata = metadata
        self.modified = modified

    def getSYPD(self, job_list):
        """
        Gets SYPD per run
        """
        outlier_free_list = []
        if job_list:
            performance_jobs = [SimJob.from_old_job_data(job_db) for job_db in job_list]
            outlier_free_list = get_jobs_with_no_outliers(performance_jobs)
        # print("{} -> {}".format(self.run_id, len(outlier_free_list)))
        if len(outlier_free_list) > 0:
            years_per_sim = datechunk_to_year(self.chunk_unit, self.chunk_size)
            # print(self.run_id)
            # print(years_per_sim)
            seconds_per_day = 86400
            number_SIM = len(outlier_free_list)
            # print(len(job_list))
            total_run_time = sum(job.run_time for job in outlier_free_list)
            # print("run {3} yps {0} n {1} run_time {2}".format(years_per_sim, number_SIM, total_run_time, self.run_id))
            if total_run_time > 0:
                return round((years_per_sim * number_SIM * seconds_per_day) / total_run_time, 2)
        return None

    def getASYPD(self, job_sim_list, job_post_list, package_jobs):
        """
        Gets ASYPD per run
        package_jobs package_name => { job_id => (queue_time, parents, job_id, start_time) }
        """
        SIM_no_outlier_list = []
        if job_sim_list and len(job_sim_list) > 0:
            performance_jobs = [SimJob.from_old_job_data(job_db) for job_db in job_sim_list]
            SIM_no_outlier_list = get_jobs_with_no_outliers(performance_jobs)
            valid_names = set([job.name for job in SIM_no_outlier_list])
            job_sim_list = [job for job in job_sim_list if job.job_name in valid_names]

        # print("Run Id {}".format(self.run_id))
        if job_sim_list and len(job_sim_list) > 0 and job_post_list and len(job_post_list) > 0:
            years_per_sim = datechunk_to_year(self.chunk_unit, self.chunk_size)
            seconds_per_day = 86400
            number_SIM = len(job_sim_list)
            number_POST = len(job_post_list)

            # print("SIM # {}".format(number_SIM))
            # print("POST # {}".format(number_POST))
            average_POST = round(sum(job.queuing_time(package_jobs.get(
                job.rowtype, None) if package_jobs is not None else None) + job.running_time() for job in job_post_list) / number_POST, 2)
            # print("Average POST {}".format(average_POST))
            # for job in job_sim_list:
                # print("{} : {} {}".format(job.job_name, job.start, job.submit))
                # print("Run time {} -> {}".format(job.job_name, job.running_time()))
                # print(job.job_name)
                # print(package_jobs.get(job.rowtype, None))
                # print("Queue time {}".format(job.queuing_time(package_jobs.get(
                #     job.rowtype, None) if package_jobs is not None else None)))
            sum_SIM = round(sum(job.queuing_time(package_jobs.get(
                job.rowtype, None) if package_jobs is not None else None) + job.running_time() for job in job_sim_list), 2)
            if (sum_SIM + average_POST) > 0:
                return round((years_per_sim * number_SIM * seconds_per_day) / (sum_SIM + average_POST), 2)
        return None


class JobData(object):
    """Job Data object
    """

    def __init__(self, _id, counter=1, job_name="None", created=None, modified=None, submit=0, start=0, finish=0, status="UNKNOWN", rowtype=1, ncpus=0, wallclock="00:00", qos="debug", energy=0, date="", section="", member="", chunk=0, last=1, platform="NA", job_id=0, extra_data=dict(), nnodes=0, run_id=None, MaxRSS=0.0, AveRSS=0.0, out='', err='', rowstatus=0):
        """[summary]

        Args:
            _id (int): Internal Id
            counter (int, optional): [description]. Defaults to 1.
            job_name (str, optional): [description]. Defaults to "None".
            created (datetime, optional): [description]. Defaults to None.
            modified (datetime, optional): [description]. Defaults to None.
            submit (int, optional): [description]. Defaults to 0.
            start (int, optional): [description]. Defaults to 0.
            finish (int, optional): [description]. Defaults to 0.
            status (str, optional): [description]. Defaults to "UNKNOWN".
            rowtype (int, optional): [description]. Defaults to 1.
            ncpus (int, optional): [description]. Defaults to 0.
            wallclock (str, optional): [description]. Defaults to "00:00".
            qos (str, optional): [description]. Defaults to "debug".
            energy (int, optional): [description]. Defaults to 0.
            date (str, optional): [description]. Defaults to "".
            section (str, optional): [description]. Defaults to "".
            member (str, optional): [description]. Defaults to "".
            chunk (int, optional): [description]. Defaults to 0.
            last (int, optional): [description]. Defaults to 1.
            platform (str, optional): [description]. Defaults to "NA".
            job_id (int, optional): [description]. Defaults to 0.
        """
        self._id = _id
        self.counter = counter
        self.job_name = job_name
        self.created = created if created else datetime.today().strftime('%Y-%m-%d-%H:%M:%S')
        self.modified = modified if modified else datetime.today().strftime('%Y-%m-%d-%H:%M:%S')
        self._submit = int(submit)
        self._start = int(start)
        self._finish = int(finish)
        # self._queue_time = 0
        # self._run_time = 0
        self.status = status
        self.rowtype = rowtype
        self.ncpus = ncpus
        self.wallclock = wallclock
        self.qos = qos if qos else "debug"
        self._energy = energy if energy else 0
        self.date = date if date else ""
        # member and section were confused in the database.
        self.section = section if section else ""
        self.member = member if member else ""
        self.chunk = chunk if chunk else 0
        self.last = last
        self._platform = platform if platform and len(
            platform) > 0 else "NA"
        self.job_id = job_id if job_id else 0
        try:
            self.extra_data = loads(extra_data)
        except Exception as exp:
            self.extra_data = ""
            pass
        self.nnodes = nnodes
        self.run_id = run_id
        self.MaxRSS = MaxRSS
        self.AveRSS = AveRSS
        self.out = out
        self.err = err
        self.rowstatus = rowstatus

        self.require_update = False
        self.metric_SYPD = None
        self.metric_ASYPD = None
        # self.title = getTitle(self.job_name, Monitor.color_status(
        #     Status.STRING_TO_CODE[self.status]), self.status)
        self.tree_parent = []

    @property
    def title(self):
        return getTitle(self.job_name, Monitor.color_status(Status.STRING_TO_CODE[self.status]), self.status)

    def calculateSYPD(self, years_per_sim):
        """
        """
        seconds_in_a_day = 86400
        # Make sure it is possible to generate
        # print("yps {0} date {1} chunk {2}".format(
        #     years_per_sim, self.date, self.chunk))
        if (years_per_sim > 0 and self.date is not None and len(self.date) > 0 and self.chunk > 0):
            # print("run {0}".format(self.running_time()))
            self.metric_SYPD = round(years_per_sim * seconds_in_a_day /
                                     self.running_time(), 2) if self.running_time() > 0 else None

    def calculateASYPD(self, chunk_unit, chunk_size, job_package_data, average_post_time):
        """
        Calculates ASYPD for a job in a run

        :param chunk_unit: chunk unit of the experiment
        :type chunk_unit: str
        :param chunk_size: chunk size of the experiment
        :type chunk_size: str
        :param job_package_data: jobs in the package (if self belongs to a package)
        :type: list()
        :param average_post_time: average queuing + running time of the post jobs in the run of self.
        :type average_post_time: float
        :return: void
        :rtype: void
        """
        result_ASYPD = calculate_ASYPD_perjob(
            chunk_unit, chunk_size, self.chunk, self.queuing_time(job_package_data) + self.running_time(), average_post_time, Status.STRING_TO_CODE[self.status])
        self.metric_ASYPD = result_ASYPD if result_ASYPD > 0 else None

    def delta_queue_time(self, job_data_in_package=None):
        """
        Retrieves queuing time in timedelta format HH:mm:ss
        """
        return str(timedelta(seconds=self.queuing_time(job_data_in_package)))

    def delta_running_time(self):
        return str(timedelta(seconds=self.running_time()))

    def submit_datetime(self):
        if self.submit > 0:
            return datetime.fromtimestamp(self.submit)
        return None

    def start_datetime(self):
        if self.start > 0:
            return datetime.fromtimestamp(self.start)
        # if self.last == 0 and self.submit > 0:
        #     return datetime.fromtimestamp(self.submit)
        return None

    def finish_datetime(self):
        if self.finish > 0:
            return datetime.fromtimestamp(self.finish)
        # if self.last == 0:
        #     if self.start > 0:
        #         return datetime.fromtimestamp(self.start)
        #     if self.submit > 0:
        #         return datetime.fromtimestamp(self.submit)
        return None

    def submit_datetime_str(self):
        o_datetime = self.submit_datetime()
        if o_datetime:
            return o_datetime.strftime('%Y-%m-%d-%H:%M:%S')
        else:
            return None

    def start_datetime_str(self):
        o_datetime = self.start_datetime()
        if o_datetime:
            return o_datetime.strftime('%Y-%m-%d-%H:%M:%S')
        else:
            return None

    def finish_datetime_str(self):
        o_datetime = self.finish_datetime()
        if o_datetime:
            return o_datetime.strftime('%Y-%m-%d-%H:%M:%S')
        else:
            return None

    def queuing_time(self, job_data_in_package=None):
        """
        Calculates the queuing time of the job.
        jobs_data_in_package dict job_id => (queue_time, parents, job_name, start_time, finish_time)

        Returns:
            int: queueing time
        """
        max_queue = queue = 0
        job_name_max_queue = None

        if job_data_in_package and len(job_data_in_package) > 0:
            # Only consider those jobs with starting time less than the start time of the job minus 20 seconds.

            jobs_times = [job_data_in_package[key]
                          for key in job_data_in_package if job_data_in_package[key][3] < (self._start - 20)]

            if jobs_times and len(jobs_times) > 0:
                # There are previous jobs
                # Sort by Queuing Time from Highest to Lowest
                jobs_times.sort(key=lambda a: a[0], reverse=True)
                # Select the maximum queue time
                max_queue, _, job_name_max_queue, start, finish = jobs_times[0]
                # Add the running time to the max queue time
                max_queue += (finish - start) if finish > start else 0

        if self.status in ["SUBMITTED", "QUEUING", "RUNNING", "COMPLETED", "HELD", "PREPARED", "FAILED"]:
            # Substract the total time from the max_queue job in the package
            # This adjustment should cover most of the wrapper types.
            # TODO: Test this mechanism against all wrapper types
            queue = int((self.start if self.start >
                         0 else time.time()) - self.submit) - int(max_queue)
            if queue > 0:
                return queue
        return 0

    def running_time(self):
        """Calculates the running time of the job.

        Returns:
            int: running time
        """
        if self.status in ["RUNNING", "COMPLETED", "FAILED"]:
            # print("Finish: {0}".format(self.finish))
            if self.start == 0:
                return 0

            run = int((self.finish if self.finish >
                       0 else time.time()) - self.start)
            # print("RUN {0}".format(run))
            if run > 0:
                return run
        return 0

    def energy_string(self):
        return str(int(self.energy / 1000)) + "K"

    @property
    def submit(self):
        return int(self._submit)

    @property
    def start(self):
        if int(self._start) > 0:
            return int(self._start)
        if self.last == 0:
            if int(self.submit) > 0:
                return int(self._submit)
        return int(self._start)

    @property
    def finish(self):
        if int(self._finish) > 0:
            return int(self._finish)
        if self.last == 0:
            if int(self._start) > 0:
                return int(self._start)
            if int(self._submit) > 0:
                return int(self._submit)
        return int(self._finish)

    @property
    def platform(self):
        return self._platform

    @property
    def energy(self):
        """
        Return as integer
        """
        return int(self._energy)

    @submit.setter
    def submit(self, submit):
        self._submit = int(submit)

    @start.setter
    def start(self, start):
        self._start = int(start)

    @finish.setter
    def finish(self, finish):
        self._finish = int(finish)

    @platform.setter
    def platform(self, platform):
        self._platform = platform if platform and len(platform) > 0 else "NA"

    @energy.setter
    def energy(self, energy):
        # print("Energy {0}".format(energy))
        if energy > 0:
            if (energy != self._energy):
                # print("Updating energy to {0} from {1}.".format(
                #     energy, self._energy))
                self.require_update = True
            self._energy = energy if energy else 0


class JobDataList():
    """Object that stores the list of jobs to be handled.
    """

    def __init__(self, expid):
        self.jobdata_list = list()
        self.expid = expid

    def add_jobdata(self, jobdata):
        self.jobdata_list.append(jobdata)

    def size(self):
        return len(self.jobdata_list)


class JobStepExtraData():
    def __init__(self, key, dict_data):
        self.key = key
        if isinstance(dict_data, dict):
            # dict_data["ncpus"] if dict_data and "ncpus" in dict_data.keys(
            self.ncpus = dict_data.get("ncpus", 0) if dict_data else 0
            # ) else 0
            self.nnodes = dict_data.get(
                "nnodes", 0) if dict_data else 0  # and "nnodes" in dict_data.keys(
            # ) else 0
            self.submit = int(mktime(datetime.strptime(dict_data["submit"], "%Y-%m-%dT%H:%M:%S").timetuple())) if dict_data and "submit" in list(dict_data.keys(
            )) else 0
            self.start = int(mktime(datetime.strptime(dict_data["start"], "%Y-%m-%dT%H:%M:%S").timetuple())) if dict_data and "start" in list(dict_data.keys(
            )) else 0
            self.finish = int(mktime(datetime.strptime(dict_data["finish"], "%Y-%m-%dT%H:%M:%S").timetuple())) if dict_data and "finish" in list(dict_data.keys(
            )) and dict_data["finish"] != "Unknown" else 0
            self.energy = parse_output_number(dict_data["energy"]) if dict_data and "energy" in list(dict_data.keys(
            )) else 0
            # if dict_data and "MaxRSS" in dict_data.keys(
            self.maxRSS = dict_data.get("MaxRSS", 0)
            # ) else 0
            # if dict_data and "AveRSS" in dict_data.keys(
            self.aveRSS = dict_data.get("AveRSS", 0)
            # ) else 0
        else:
            self.ncpus = 0
            self.nnodes = 0
            self.submit = 0
            self.start = 0
            self.finish = 0
            self.energy = 0
            self.maxRSS = 0
            self.aveRSS = 0


class MainDataBase():
    def __init__(self, expid):
        self.expid = expid
        self.conn = None
        self.conn_ec = None
        self.create_table_query = None
        self.db_version = None

    def create_connection(self, db_file):
        """
        Create a database connection to the SQLite database specified by db_file.
        :param db_file: database file name
        :return: Connection object or None
        """
        try:
            conn = sqlite3.connect(db_file)
            return conn
        except:
            return None

    def create_table(self):
        """ create a table from the create_table_sql statement
        :param conn: Connection object
        :param create_table_sql: a CREATE TABLE statement
        :return:
        """
        try:
            if self.conn:
                c = self.conn.cursor()
                c.execute(self.create_table_query)
            else:
                raise IOError("Not a valid connection")
        except IOError as exp:
            Log.warning(exp)
            return None
        except sqlite3.Error as e:
            if _debug == True:
                Log.info(traceback.format_exc())
            Log.warning("Error on create table : " + str(type(e).__name__))
            return None

    def create_index(self):
        """ Creates index from statement defined in child class
        """
        try:
            if self.conn:
                c = self.conn.cursor()
                c.execute(self.create_index_query)
                self.conn.commit()
            else:
                raise IOError("Not a valid connection")
        except IOError as exp:
            Log.warning(exp)
            return None
        except sqlite3.Error as e:
            if _debug == True:
                Log.info(traceback.format_exc())
            Log.debug(str(type(e).__name__))
            Log.warning("Error on create index . create_index")
            return None


class ExperimentGraphDrawing(MainDataBase):
    def __init__(self, expid):
        """
        Sets and validates graph drawing.
        :param expid: Name of experiment
        :type expid: str
        :param allJobs: list of all jobs objects (usually from job_list)
        :type allJobs: list()
        """
        MainDataBase.__init__(self, expid)
        APIBasicConfig.read()
        self.expid = expid
        self.folder_path = APIBasicConfig.LOCAL_ROOT_DIR
        self.database_path = os.path.join(
            self.folder_path, "as_metadata", "graph" , "graph_data_" + str(expid) + ".db")
        self.create_table_query = textwrap.dedent(
            '''CREATE TABLE
        IF NOT EXISTS experiment_graph_draw (
        id INTEGER PRIMARY KEY,
        job_name text NOT NULL,
        x INTEGER NOT NULL,
        y INTEGER NOT NULL
        );''')

        if not os.path.exists(self.database_path):
            os.umask(0)
            if not os.path.exists(os.path.dirname(self.database_path)):
                os.makedirs(os.path.dirname(self.database_path))
            os.open(self.database_path, os.O_WRONLY | os.O_CREAT, 0o777)
            self.conn = self.create_connection(self.database_path)
            self.create_table()
        else:
            self.conn = self.create_connection(self.database_path)
        self.lock_name = "calculation_in_progress.lock"
        self.current_position_dictionary = None
        self.current_jobs_set = set()
        self.coordinates = list()
        self.set_current_position()
        self.should_update = False
        self.locked = False
        self.test_locked()

    def test_locked(self):
        self.locked = True
        try:
            with portalocker.Lock(os.path.join(self.folder_path, self.lock_name), timeout=1) as fh:
                self.locked = False
                fh.flush()
                os.fsync(fh.fileno())
        except portalocker.AlreadyLocked:
            print("It is locked")
            self.locked = True
        except Exception as exp:
            self.locked = True

    def get_validated_data(self, allJobs):
        """
        Validates if should update current graph drawing.
        :return: None if graph drawing should be updated, otherwise, it returns the position data.
        :rype: None or dict()
        """
        job_names = {job.name for job in allJobs}
        # Validating content
        difference = job_names - self.current_jobs_set
        if difference and len(difference) > 0:
            # Intersection found. Graph Drawing database needs to be updated
            self.should_update = True
            # Clear database
            return None
        return self.current_position_dictionary
        # return None if self.should_update == True else self.current_position_dictionary

    def calculate_drawing(self, allJobs, independent=False, num_chunks=48, job_dictionary=None):
        """
        Called in a thread.
        :param allJobs: list of jobs (usually from job_list object)
        :type allJobs: list()
        :return: Last row Id
        :rtype: int
        """
        lock_name = "calculation_{}_in_progress.lock".format(self.expid) if independent == True else self.lock_name
        lock_path_file = os.path.join(self.folder_path, lock_name)
        try:
            with portalocker.Lock(lock_path_file, timeout=1) as fh:
                self.conn = self.create_connection(self.database_path)
                monitor = Monitor()
                graph = monitor.create_tree_list(
                    self.expid, allJobs, None, dict(), False, job_dictionary)
                if len(allJobs) > 1000:
                    # Logic: Start with 48 as acceptable number of chunks for Gmaxiter = 100
                    # Minimum Gmaxiter will be 10
                    maxiter = max(10, 148 - num_chunks)
                    # print("Experiment {} num_chunk {} maxiter {}".format(
                    #     self.expid, num_chunks, maxiter))
                    result = graph.create(
                        ['dot', '-Gnslimit=2', '-Gnslimit1=2', '-Gmaxiter={}'.format(maxiter), '-Gsplines=none', '-v'], format="plain")
                else:
                    result = graph.create('dot', format="plain")
                for u in result.split(b"\n"):
                    splitList = u.split(b" ")
                    if len(splitList) > 1 and splitList[0] == "node":
                        self.coordinates.append((splitList[1], int(
                            float(splitList[2]) * 90), int(float(splitList[3]) * -90)))
                        # self.coordinates[splitList[1]] = (
                        #     int(float(splitList[2]) * 90), int(float(splitList[3]) * -90))
                self.insert_coordinates()
                fh.flush()
                os.fsync(fh.fileno())
            os.remove(lock_path_file)
            return self.get_validated_data(allJobs)
        except portalocker.AlreadyLocked:
            message = "Already calculating graph drawing."
            print(message)
            return None
        except Exception as exp:
            print((traceback.format_exc()))
            os.remove(lock_path_file)
            print(("Exception while calculating coordinates {}".format(str(exp))))
            return None

    def insert_coordinates(self):
        """
        Prepares and inserts new coordinates.
        """
        try:
            # Start by clearing database
            self._clear_graph_database()
            result = None
            if self.coordinates and len(self.coordinates) > 0:
                result = self._insert_many_graph_coordinates(self.coordinates)
                return result
            return None
        except Exception as exp:
            print((str(exp)))
            return None

    def set_current_position(self):
        """
        Sets all registers in the proper variables.
        current_position_dictionary: JobName -> (x, y)
        current_jobs_set: JobName
        """
        current_table = self._get_current_position()
        if current_table and len(current_table) > 0:
            self.current_position_dictionary = {row[1]: (row[2], row[3]) for row in current_table}
            self.current_jobs_set = set(self.current_position_dictionary.keys())

    def _get_current_position(self):
        """
        Get all registers from experiment_graph_draw.\n
        :return: row content: id, job_name, x, y
        :rtype: 4-tuple (int, str, int, int)
        """
        try:
            if self.conn:
                # conn = create_connection(DB_FILE_AS_TIMES)
                self.conn.text_factory = str
                cur = self.conn.cursor()
                cur.execute(
                    "SELECT id, job_name, x, y FROM experiment_graph_draw")
                rows = cur.fetchall()
                return rows
            return None
        except Exception as exp:
            print((traceback.format_exc()))
            print((str(exp)))
            return None

    def _insert_many_graph_coordinates(self, values):
        """
        Create many graph coordinates
        :param conn:
        :param details:
        :return:
        """
        try:
            if self.conn:
                # exp_id = self._get_id_db()
                # conn = create_connection(DB_FILE_AS_TIMES)
                # creation_date = datetime.today().strftime('%Y-%m-%d-%H:%M:%S')
                sql = ''' INSERT INTO experiment_graph_draw(job_name, x, y) VALUES(?,?,?) '''
                # print(row_content)
                cur = self.conn.cursor()
                cur.executemany(sql, values)
                # print(cur)
                self.conn.commit()
                return cur.lastrowid
        except Exception as exp:
            print((traceback.format_exc()))
            Log.warning(
                "Error on Insert many graph drawing : {}".format(str(exp)))
            return None

    def _clear_graph_database(self):
        """
        Clear all content from graph drawing database
        """
        try:
            if self.conn:
                # conn = create_connection(DB_FILE_AS_TIMES)
                # modified_date = datetime.today().strftime('%Y-%m-%d-%H:%M:%S')
                sql = ''' DELETE FROM experiment_graph_draw '''
                cur = self.conn.cursor()
                cur.execute(sql, )
                self.conn.commit()
                return True
            return False
        except Exception as exp:
            print((traceback.format_exc()))
            print(("Error on Database clear: {}".format(str(exp))))
            return False

class JobDataStructure(MainDataBase):

    def __init__(self, expid, basic_config):
        """Initializes the object based on the unique identifier of the experiment.

        Args:
            expid (str): Experiment identifier
        """
        MainDataBase.__init__(self, expid)
        # BasicConfig.read()
        # self.expid = expid
        self.folder_path = basic_config.JOBDATA_DIR
        self.database_path = os.path.join(
            self.folder_path, "job_data_" + str(expid) + ".db")
        # self.conn = None
        self.db_version = None
        # self.jobdata_list = JobDataList(self.expid)
        self.create_index_query = textwrap.dedent('''
            CREATE INDEX IF NOT EXISTS ID_JOB_NAME ON job_data(job_name);
            ''')
        if not os.path.exists(self.database_path):
            self.conn = None
        else:
            self.conn = self.create_connection(self.database_path)
            self.db_version = self._select_pragma_version()
            # self.query_job_historic = None
            # Historic only working on DB 12 now
            self.query_job_historic = "SELECT id, counter, job_name, created, modified, submit, start, finish, status, rowtype, ncpus, wallclock, qos, energy, date, section, member, chunk, last, platform, job_id, extra_data, nnodes, run_id FROM job_data WHERE job_name=? ORDER BY counter DESC"

            if self.db_version < DB_VERSION_SCHEMA_CHANGES:
                try:
                    self.create_index()
                except Exception as exp:
                    print(exp)
                    pass

    def __str__(self):
        return '{} {}'.format("Data structure. Version:", self.db_version)

    def get_total_job_data(self, allJobs, job_worker_database=None):
        """ """
        if self.db_version >= 17:
            return self.get_current_job_data_last(), []
        else:
            job_data, warnings = self.process_current_run_collection(allJobs, job_worker_database)
            return job_data, warnings

    def process_current_run_collection(self, allJobs, job_worker_database=None):
        """Post-process for job_data.

        Returns:
            ([job_data], [warning_messaages]): job data processes, messages
        """
        start_time = time.time()
        current_job_data = None
        warning_messages = []
        experiment_run = self.get_max_id_experiment_run()
        # List of jobs from pkl -> Dictionary
        allJobsDict = {
            job.name: Status.VALUE_TO_KEY[job.status] for job in allJobs}
        # None if there is no experiment header
        if experiment_run and allJobsDict:
            # List of last runs of jobs
            current_job_data_last = self.get_current_job_data_last()
            if not current_job_data_last:
                warning_messages.append(
                    "Critical | This version of Autosubmit does not support the database that provides the energy information.")
            # Include only those that exist in the pkl and have the same status as in the pkl
            current_job_data = [job for job in current_job_data_last if allJobsDict.get(
                job.job_name, None) and allJobsDict[job.job_name] == job.status] if current_job_data_last else None
            # Start processing
            if current_job_data:
                # print("There is current.")
                # Dropping parents key
                for job in current_job_data:
                    if job.extra_data:
                        job.extra_data.pop('parents', None)
                # Internal map from name to object
                name_to_current_job = {
                    job.job_name: job for job in current_job_data}
                # Unique packages where rowtype > 2
                packages = set(
                    job.rowtype for job in current_job_data if job.rowtype > 2)
                # Start by processing packages
                for package in packages:
                    # print("Process {0}".format(package))
                    # All jobs in package
                    jobs_in_package = [
                        job for job in current_job_data if job.rowtype == package]
                    # Order package by submit order
                    jobs_in_package.sort(key=lambda x: x._id, reverse=True)
                    # Internal list of single-purpose objects
                    wrapper_jobs = []
                    sum_total_energy = 0
                    not_1_to_1 = True
                    keys_found = False
                    no_process = False
                    for job_data in jobs_in_package:
                        if not job_data.extra_data:
                            continue
                        # If it is a wrapper job step
                        #print("Own extra data")
                        # print(job_data.extra_data)
                        if job_data.extra_data.get("energy", None) and job_data.extra_data["energy"] != "NA":
                            name_to_current_job[job_data.job_name].energy = parse_output_number(
                                job_data.extra_data["energy"])
                            sum_total_energy += name_to_current_job[job_data.job_name].energy
                        else:
                            # Identify best source
                            description_job = max(
                                jobs_in_package, key=lambda x: len(str(x.extra_data)))
                            # Identify job steps
                            #print("Best source")
                            # print(description_job.extra_data)
                            keys_step = [
                                y for y in list(description_job.extra_data.keys()) if '.' in y and y[y.index('.') + 1:] not in ["batch", "extern"] and y != "parents"]
                            print([job.name for job in jobs_in_package])
                            print(keys_step)
                            if len(keys_step) > 0:
                                # Steps found
                                keys_step.sort(
                                    key=lambda x: int(x[x.index('.') + 1:]))
                                keys_found = True
                                # Find all job steps
                                for key in keys_step:
                                    # "submit" not in description_job.extra_data[key].keys():
                                    if description_job.extra_data[key].get(key, None) is None:
                                        keys_found = False
                                    break

                                for key in keys_step:
                                    wrapper_jobs.append(JobStepExtraData(
                                        key, description_job.extra_data[key]))

                                sum_total_energy = sum(
                                    jobp.energy for jobp in wrapper_jobs) * 1.0

                                # if sum_total_energy <= 0:
                                # print("Package {0} source job extra_data {1}".format(package,
                                #                                                      description_job.extra_data))

                                if len(jobs_in_package) == len(wrapper_jobs) and len(wrapper_jobs) > 0:
                                    # Approximation
                                    not_1_to_1 = False
                            else:
                                # Identify main step
                                # print(description_job.extra_data)
                                main_step = [
                                    y for y in list(description_job.extra_data.keys()) if '.' not in y and y != "parents"]
                                # print(main_step)
                                if len(main_step) > 0 and [main_step[0]] not in ['AveRSS', 'finish', 'ncpus', 'submit', 'MaxRSS', 'start', 'nnodes', 'energy']:
                                    # Check only first one
                                    main_step = [main_step[0]]
                                    # print(main_step)
                                    # If main step contains submit, its valid. Else, break, not valid,
                                    # print(job_data.job_name)

                                    for key in main_step:
                                        if key in list(description_job.extra_data.keys()) and isinstance(description_job.extra_data[key], dict) and "submit" not in list(description_job.extra_data[key].keys()):
                                            keys_found = False
                                        break
                                    # Build wrapper jobs
                                    for key in main_step:
                                        # key in description_job.extra_data.keys():
                                        if isinstance(description_job.extra_data, dict) and description_job.extra_data.get(key, None):
                                            wrapper_jobs.append(JobStepExtraData(
                                                key, description_job.extra_data[key]))
                                    # Total energy for main job
                                    sum_total_energy = sum(
                                        jobp.energy for jobp in wrapper_jobs) * 1.0

                                else:
                                    no_process = True
                                    warning_messages.append(
                                        "Wrapper | Wrapper {0} does not have information to perform any energy approximation.".format(package))
                            break
                    # Keys do not have enough information
                    if keys_found == False:
                        warning_messages.append(
                            "Wrapper | Wrapper {0} does not have complete sacct data available.".format(package))
                    # If it is not a 1 to 1 relationship between jobs in package and job steps
                    if sum_total_energy > 0:
                        if not_1_to_1 == True and no_process == False:
                            # It is not 1 to 1, so we perform approximation
                            warning_messages.append(
                                "Approximation | The energy results in wrapper {0} are an approximation. Total energy detected: {1}.".format(package, sum_total_energy))
                            # Completing job information if necessary
                            drop_jobs = []
                            for i in range(0, len(jobs_in_package)):
                                if jobs_in_package[i].running_time() <= 0:
                                    # Needs to be completed
                                    # jobs_in_package[i].job_name in job_worker_database.keys():
                                    if job_worker_database and job_worker_database.get(jobs_in_package[i].job_name, None):
                                        submit_t, start_t, finish_t, status, detail_id = job_worker_database[
                                            jobs_in_package[i].job_name]
                                        jobs_in_package[i].submit = submit_t
                                        jobs_in_package[i].start = start_t
                                        jobs_in_package[i].finish = finish_t
                                        if jobs_in_package[i].running_time() > 0:
                                            warning_messages.append("Completion | Job {0} (Package {1}) data has been corrected with data from worker database.".format(
                                                jobs_in_package[i].job_name, package))
                                        else:
                                            # jobs_in_package.pop(i)
                                            dropped_job = jobs_in_package[i]
                                            drop_jobs.append(i)
                                            warning_messages.append(
                                                "Completion | Job {0} (Package {1}) has no reliable information available and has been excluded from the calculation.".format(dropped_job.job_name, package))
                                    else:
                                        # Dropping job from package list
                                        # jobs_in_package.pop(i)
                                        dropped_job = jobs_in_package[i]
                                        drop_jobs.append(i)
                                        # Dropping job from result list
                                        # name_to_current_job.pop(
                                        #     dropped_job.job_name, None)
                                        warning_messages.append(
                                            "Completion | Job {0} (Package {1}) has no reliable information available and has been excluded from the calculation.".format(dropped_job.job_name, package))
                            for d in drop_jobs:
                                jobs_in_package.pop(d)
                            # After completion is finished, calculate total resources to be approximated
                            resources_total = sum(
                                z.ncpus * z.running_time() for z in jobs_in_package) * 1.0
                            if resources_total > 0:
                                for job_data in jobs_in_package:
                                    job_data_factor = (
                                        job_data.ncpus * job_data.running_time())
                                    if job_data_factor <= 0:
                                        warning_messages.append("Approximation | Job {0} requires {1} ncpus and has {2} running time, resulting in a 0 energy approximation. This job will be ignored.".format(
                                            job_data.job_name, job_data.ncpus, job_data.running_time()))
                                    name_to_current_job[job_data.job_name].energy = round(job_data_factor /
                                                                                          resources_total * sum_total_energy, 2)
                            else:
                                warning_messages.append(
                                    "Approximation | Aproximation for wrapper {0} failed.".format(package))
                        else:
                            if len(jobs_in_package) > 0 and len(wrapper_jobs) > 0 and len(jobs_in_package) == len(wrapper_jobs) and no_process == False:
                                # It is 1 to 1
                                for i in range(0, len(jobs_in_package)):
                                    name_to_current_job[jobs_in_package[i]
                                                        .job_name].energy = wrapper_jobs[i].energy
                                    name_to_current_job[jobs_in_package[i]
                                                        .job_name].submit = wrapper_jobs[i].submit
                                    name_to_current_job[jobs_in_package[i]
                                                        .job_name].start = wrapper_jobs[i].start
                                    name_to_current_job[jobs_in_package[i]
                                                        .job_name].finish = wrapper_jobs[i].finish
                            else:
                                warning_messages.append(
                                    "Approximation | Wrapper {0} did not have enough or precise information to calculate an exact mapping.".format(package))
                    else:
                        warning_messages.append(
                            "Approximation | Wrapper {0} does not have energy information, it will be ignored.".format(package))

                for job_data in current_job_data:
                    if job_data.rowtype == 2 and len(job_data.extra_data) > 0:
                        keys = [x for x in list(job_data.extra_data.keys())
                                if x != "parents" and '.' not in x]
                        if len(keys) > 0:
                            found_energy = job_data.extra_data[keys[0]]["energy"]
                            # Resort to batch if main is NA
                            found_energy = found_energy if found_energy != "NA" else (
                                job_data.extra_data[keys[0] + ".batch"]["energy"] if job_data.extra_data.get(keys[0] + ".batch", None) else found_energy)
                            job_data.energy = parse_output_number(found_energy)
                        else:
                            continue
                            # warning_messages.append(
                            #     "Single Job | Job {0} has no energy information available. {1} ".format(job_data.job_name, keys))
                # self.update_energy_values([job for job in current_job_data if job.require_update == True])
            # for job in current_job_data:
            #     if job.energy == 0:
            #         print("Job {:30} | energy {:15} | package {:5} | status {:15}".format(
            #             job.job_name, job.energy, job.rowtype, job.status))

            # for message in warning_messages:
            #     print(message)

        print(("Extra data query finished in {0} seconds.".format(
            time.time() - start_time)))

        if not current_job_data:
            warning_messages.append(
                "Energy | There is not enough information to compute a reliable result.")

        return current_job_data, warning_messages

    def update_energy_values(self, update_job_data):
        """Updating energy values

        Args:
            update_job_data ([type]): [description]

        Returns:
            [type]: [description]
        """
        try:
            #print("Updating {0}".format(len(update_job_data)))
            # (job_data.energy, datetime.today().strftime(
            #    '%Y-%m-%d-%H:%M:%S'), job_data._id)
            modified_date = datetime.today().strftime('%Y-%m-%d-%H:%M:%S')
            self._update_many_job_data(
                [(jobdata.energy, modified_date, jobdata._id) for jobdata in update_job_data])
            # for jobdata in update_job_data:
            #     # print("Job {0} requires update. Energy {1}.".format(
            #     #     jobdata.job_name, jobdata.energy))
            #     self._update_job_data(jobdata)
            self.conn.commit()
        except Exception as exp:
            print((traceback.format_exc()))
            print((
                "Autosubmit couldn't retrieve experiment run header. update_energy_values. Exception {0}".format(str(exp))))
            pass

    def get_historic_job_data_json(self, job_name):
        """
        Gets historic data in JSON format
        """
        result = []
        try:
            jobdata_historic = self.get_historic_job_data(job_name)
            if jobdata_historic:
                all_post_jobs = self.get_current_job_data_CF_POST()
                for jobdata in jobdata_historic:
                    package_info = None
                    experiment_run = None
                    # print("{} {}".format(jobdata.rowtype, jobdata.run_id))
                    # ONLY calculate metrics for COMPLETED jobs
                    if jobdata.run_id is not None:
                        experiment_run = self.get_experiment_run_by_id(
                            jobdata.run_id)
                    if jobdata.status == "COMPLETED":
                        if experiment_run:
                            years_per_sim = datechunk_to_year(
                                experiment_run.chunk_unit, experiment_run.chunk_size)
                            jobdata.calculateSYPD(years_per_sim)
                        if jobdata.rowtype > 2:
                            package_info = self.get_job_package_info(
                                jobdata.run_id, jobdata.rowtype)  # get package info
                        # ASYPD
                        if experiment_run:
                            average_post_time = 0
                            jobs_post_in_run = all_post_jobs.get(
                                experiment_run.run_id, None)
                            if jobs_post_in_run and len(jobs_post_in_run) > 0:
                                for jobpost in jobs_post_in_run:
                                    if jobpost.rowtype > 2:
                                        package_info_post_job = self.get_job_package_info(
                                            jobpost.run_id, jobpost.rowtype)
                                        average_post_time += ((jobpost.queuing_time(
                                            package_info_post_job) + jobpost.running_time()))
                                    else:
                                        average_post_time += (jobpost.queuing_time() +
                                                              jobpost.running_time())

                                average_post_time = average_post_time / \
                                    len(jobs_post_in_run)
                            jobdata.calculateASYPD(
                                experiment_run.chunk_unit, experiment_run.chunk_size, package_info, average_post_time)

                    result.append({"counter": jobdata.counter,
                                   "created": jobdata.created,
                                   "submit": jobdata.submit_datetime_str(),
                                   "start": jobdata.start_datetime_str(),
                                   "finish": jobdata.finish_datetime_str(),
                                   "queue_time": jobdata.delta_queue_time(job_data_in_package=package_info),
                                   "run_time": jobdata.delta_running_time(),
                                   "ncpus": jobdata.ncpus,
                                   "wallclock": jobdata.wallclock,
                                   "qos": jobdata.qos,
                                   "platform": jobdata.platform,
                                   "job_id": jobdata.job_id,
                                   "nodes": jobdata.nnodes,
                                   "energy": jobdata.energy_string() if jobdata.run_id is not None and jobdata.energy > 0 else "NA",
                                   "status": jobdata.status,
                                   "SYPD": jobdata.metric_SYPD,
                                   "ASYPD": jobdata.metric_ASYPD,
                                   "run_id": jobdata.run_id,
                                   "run_created": experiment_run.created if experiment_run else "NA"
                                   })
        except Exception as exp:
            print((traceback.format_exc()))
            print((str(exp)))
            return None
        return result

    def get_historic_job_data(self, job_name):
        """
        Get the historic job data for a certain job

        :param job_name: Name of Job
        :type job_name: str
        :return: JobData rows that match the job_name
        :rtype: list() of JobData objects
        """
        jobdata = []
        try:
            current_history = self._get_historic_job_data(job_name)
            if current_history:
                for item in current_history:
                    job_item = JobItem_10(
                        *item) if self.db_version < DB_VERSION_SCHEMA_CHANGES else JobItem_12(*item)
                    jobdata.append(JobData(job_item.id, job_item.counter, job_item.job_name, job_item.created, job_item.modified, job_item.submit, job_item.start, job_item.finish, job_item.status,
                                           job_item.rowtype, job_item.ncpus, job_item.wallclock, job_item.qos, job_item.energy, job_item.date, job_item.section, job_item.member, job_item.chunk, job_item.last, job_item.platform, job_item.job_id, job_item.extra_data, job_item.nnodes if self.db_version >= DB_VERSION_SCHEMA_CHANGES else 0, job_item.run_id if self.db_version >= DB_VERSION_SCHEMA_CHANGES else None))
        except Exception as exp:
            if _debug == True:
                print((traceback.format_exc()))
            print(("Error while retrieving job {0} information. {1}".format(
                job_name, str(exp))))
            return None
        return jobdata

    def get_max_id_experiment_run(self):
        """
        Get last (max) experiment run object.
        :return: ExperimentRun data
        :rtype: ExperimentRun object
        """
        try:
            # expe = list()
            if not os.path.exists(self.database_path):
                raise Exception("Job data folder not found {0} or the database version is outdated.".format(str(self.database_path)))
            if self.db_version < DB_VERSION_SCHEMA_CHANGES:
                print(("Job database version {0} outdated.".format(str(self.db_version))))
            if os.path.exists(self.database_path) and self.db_version >= DB_VERSION_SCHEMA_CHANGES:
                modified_time = int(os.stat(self.database_path).st_mtime)
                current_experiment_run = self._get_max_id_experiment_run()
                if current_experiment_run:
                    exprun_item = ExperimentRunItem_14(
                        *current_experiment_run) if self.db_version >= DB_EXPERIMENT_HEADER_SCHEMA_CHANGES else ExperimentRunItem(*current_experiment_run)
                    return ExperimentRun(exprun_item.run_id, exprun_item.created, exprun_item.start, exprun_item.finish, exprun_item.chunk_unit, exprun_item.chunk_size, exprun_item.completed, exprun_item.total, exprun_item.failed, exprun_item.queuing, exprun_item.running, exprun_item.submitted, exprun_item.suspended if self.db_version >= DB_EXPERIMENT_HEADER_SCHEMA_CHANGES else 0, exprun_item.metadata if self.db_version >= DB_EXPERIMENT_HEADER_SCHEMA_CHANGES else "", modified_time)
                else:
                    return None
            else:
                raise Exception("Job data folder not found {0} or the database version is outdated.".format(
                    str(self.database_path)))
        except Exception as exp:
            print((str(exp)))
            print((traceback.format_exc()))
            return None

    def get_experiment_runs(self):
        # type: () -> List[ExperimentRun]
        """
        Get list of experiment runs stored in database
        """
        try:
            # expe = list()
            if os.path.exists(self.folder_path) and self.db_version >= DB_VERSION_SCHEMA_CHANGES:
                result = []
                current_experiment_run = self._get_experiment_runs()
                if current_experiment_run:
                    for run in current_experiment_run:
                        exprun_item = ExperimentRunItem_14(
                            *run) if self.db_version >= DB_EXPERIMENT_HEADER_SCHEMA_CHANGES else ExperimentRunItem(*run)
                        result.append(ExperimentRun(exprun_item.run_id, exprun_item.created, exprun_item.start, exprun_item.finish, exprun_item.chunk_unit, exprun_item.chunk_size, exprun_item.completed, exprun_item.total, exprun_item.failed, exprun_item.queuing,
                                                    exprun_item.running, exprun_item.submitted, exprun_item.suspended if self.db_version >= DB_EXPERIMENT_HEADER_SCHEMA_CHANGES else 0, exprun_item.metadata if self.db_version >= DB_EXPERIMENT_HEADER_SCHEMA_CHANGES else ""))
                    return result
                else:
                    return None
            else:
                raise Exception("Job data folder not found {0} or the database version is outdated.".format(
                    str(self.database_path)))
        except Exception as exp:
            if _debug == True:
                Log.info(traceback.format_exc())
            Log.debug(traceback.format_exc())
            Log.warning(
                "Autosubmit couldn't retrieve experiment runs. get_experiment_runs. Exception {0}".format(str(exp)))
            return None

    def get_experiment_run_by_id(self, run_id):
        """
        Get experiment run stored in database by run_id
        """
        try:
            # expe = list()
            if os.path.exists(self.folder_path) and self.db_version >= DB_VERSION_SCHEMA_CHANGES:
                result = None
                current_experiment_run = self._get_experiment_run_by_id(run_id)
                if current_experiment_run:
                    # for run in current_experiment_run:
                    exprun_item = ExperimentRunItem_14(
                        *current_experiment_run) if self.db_version >= DB_EXPERIMENT_HEADER_SCHEMA_CHANGES else ExperimentRunItem(*current_experiment_run)
                    result = ExperimentRun(exprun_item.run_id, exprun_item.created, exprun_item.start, exprun_item.finish, exprun_item.chunk_unit, exprun_item.chunk_size, exprun_item.completed, exprun_item.total, exprun_item.failed, exprun_item.queuing,
                                           exprun_item.running, exprun_item.submitted, exprun_item.suspended if self.db_version >= DB_EXPERIMENT_HEADER_SCHEMA_CHANGES else 0, exprun_item.metadata if self.db_version >= DB_EXPERIMENT_HEADER_SCHEMA_CHANGES else "")
                    return result
                else:
                    return None
            else:
                raise Exception("Job data folder not found {0} or the database version is outdated.".format(
                    str(self.database_path)))
        except Exception as exp:
            if _debug == True:
                Log.info(traceback.format_exc())
            Log.debug(traceback.format_exc())
            Log.warning(
                "Autosubmit couldn't retrieve experiment run. get_experiment_run_by_id. Exception {0}".format(str(exp)))
            return None

    def get_job_package_info(self, run_id, package_id):
        try:
            current_collection = {}
            if self.conn:
                if package_id > 2:
                    data = self._get_job_package_info(run_id, package_id)
                    if data:
                        for item in data:
                            _id, job_name, submit, start, finish, job_id, extra_data = item
                            extra_data_process = None
                            # print(extra_data)
                            try:
                                extra_data_process = loads(extra_data)
                            except Exception as exp:
                                # print(exp)
                                extra_data_process = None
                            # print(type(extra_data_process))
                            current_collection[job_id] = (
                                start - submit, extra_data_process.get('parents', None) if type(extra_data_process) is dict else None, job_name, start, finish)
            # print(current_collection)
            return current_collection
        except Exception as exp:
            print((traceback.format_exc()))
            print((
                "Error on returning current job data. run_id {0}".format(run_id)))
            return None

    def get_job_packages_info_per_run_id(self, run_id):
        """
        Returns a dictionary PackageName => { JobName => (QueueTime, parents, job_name, start) }
        """
        try:
            package_to_jobs_map = {}
            if self.conn:
                data = self._get_job_packages_info_per_run_id(run_id)
                if data:
                    packages = set(item[7] for item in data)
                    for package in packages:
                        # print("Package {}".format(package))
                        current_collection = {}
                        included_set = set()
                        package_data = [x for x in data if x[7] == package]
                        for item in package_data:
                            _id, job_name, submit, start, finish, job_id, extra_data, rowtype = item
                            if job_name not in included_set:
                                # print("Job {} in package {}".format(
                                #     job_name, package))
                                included_set.add(job_name)
                                extra_data_process = None
                                # print(extra_data)
                                try:
                                    extra_data_process = loads(extra_data)
                                except Exception as exp:
                                    # print(exp)
                                    extra_data_process = None
                                # print(type(extra_data_process))
                                current_collection[job_name] = (
                                    start - submit, extra_data_process.get('parents', None) if extra_data_process is not None and type(extra_data_process) is dict else None, job_name, start, finish)
                        package_to_jobs_map[package] = current_collection
            # print(current_collection)
            return package_to_jobs_map
        except Exception as exp:
            print((traceback.format_exc()))
            print((
                "Error on returning current job data. run_id {0}".format(run_id)))
            return None

    def get_current_job_data(self, run_id, all_states=False):
        """
        Gets the job historical data for a run_id.
        :param run_id: Run identifier
        :type run_id: int
        :param all_states: False if only last=1 should be included, otherwise all rows
        :return: List of jobdata rows
        :rtype: list() of JobData objects
        """
        try:
            current_collection = []
            if self.db_version < DB_VERSION_SCHEMA_CHANGES:
                raise Exception("This function requieres a newer DB version.")
            if os.path.exists(self.folder_path):
                current_job_data = self._get_current_job_data(
                    run_id, all_states)
                if current_job_data:
                    for job_data in current_job_data:
                        if self.db_version >= CURRENT_DB_VERSION:
                            jobitem = JobItem_15(*job_data)
                            current_collection.append(JobData(jobitem.id, jobitem.counter, jobitem.job_name, jobitem.created, jobitem.modified, jobitem.submit, jobitem.start, jobitem.finish, jobitem.status, jobitem.rowtype, jobitem.ncpus,
                                                              jobitem.wallclock, jobitem.qos, jobitem.energy, jobitem.date, jobitem.section, jobitem.member, jobitem.chunk, jobitem.last, jobitem.platform, jobitem.job_id, jobitem.extra_data, jobitem.nnodes, jobitem.run_id, jobitem.MaxRSS, jobitem.AveRSS, jobitem.out, jobitem.err, jobitem.rowstatus))
                        else:
                            jobitem = JobItem_12(*job_data)
                            current_collection.append(JobData(jobitem.id, jobitem.counter, jobitem.job_name, jobitem.created, jobitem.modified, jobitem.submit, jobitem.start, jobitem.finish, jobitem.status, jobitem.rowtype, jobitem.ncpus,
                                                              jobitem.wallclock, jobitem.qos, jobitem.energy, jobitem.date, jobitem.section, jobitem.member, jobitem.chunk, jobitem.last, jobitem.platform, jobitem.job_id, jobitem.extra_data, jobitem.nnodes, jobitem.run_id))
                    return current_collection
            return None
        except Exception as exp:
            print((traceback.format_exc()))
            print((
                "Error on returning current job data. run_id {0}".format(run_id)))
            return None

    def get_all_current_job_data(self):
        try:
            current_collection = []
            if os.path.exists(self.folder_path):
                all_data = self._get_all_current_job_data()
                if all_data:
                    for job_data in all_data:
                        jobitem = JobItem_12(*job_data)
                        current_collection.append(JobData(jobitem.id, jobitem.counter, jobitem.job_name, jobitem.created, jobitem.modified, jobitem.submit, jobitem.start, jobitem.finish, jobitem.status, jobitem.rowtype, jobitem.ncpus,
                                                          jobitem.wallclock, jobitem.qos, jobitem.energy, jobitem.date, jobitem.section, jobitem.member, jobitem.chunk, jobitem.last, jobitem.platform, jobitem.job_id, jobitem.extra_data, jobitem.nnodes, jobitem.run_id))
                    return current_collection
            return None
        except Exception as exp:
            print((traceback.format_exc()))
            print("Error on returning all job data")
            return None

    def get_current_job_data_CF_SIM(self):
        """
        Gets run detail for SYPD calculation
        """
        try:
            current_collection = []
            if self.db_version < DB_VERSION_SCHEMA_CHANGES:
                raise Exception("This function requires a newer DB version.")
            if os.path.exists(self.folder_path):
                current_job_data = self._get_current_job_data_CF_SIM()
                if current_job_data:
                    included_set = set()
                    for job_data in current_job_data:
                        jobitem = JobItem_12(*job_data)
                        if (jobitem.job_name, jobitem.run_id) not in included_set:
                            included_set.add(
                                (jobitem.job_name, jobitem.run_id))

                            current_collection.append(JobData(jobitem.id, jobitem.counter, jobitem.job_name, jobitem.created, jobitem.modified, jobitem.submit, jobitem.start, jobitem.finish, jobitem.status, jobitem.rowtype, jobitem.ncpus,
                                                              jobitem.wallclock, jobitem.qos, jobitem.energy, jobitem.date, jobitem.section, jobitem.member, jobitem.chunk, jobitem.last, jobitem.platform, jobitem.job_id, jobitem.extra_data, jobitem.nnodes, jobitem.run_id))
                    # Outlier detection

                    # data = {run_id: [y.running_time() for y in current_collection if y.run_id == run_id]
                    #         for run_id in set([job.run_id for job in current_collection])}
                    # mean_sd = {run_id: (np.mean(data.get(run_id, [0])), np.std(data.get(run_id, [0])))
                    #            for run_id in set([job.run_id for job in current_collection])}
                    # threshold = 2

                    return {run_id: [x for x in current_collection if x.run_id == run_id] for run_id in set([job.run_id for job in current_collection])}

            return {}
        except Exception as exp:
            print((traceback.format_exc()))
            print(
                "Error on returning current job data for SYPD")
            return {}

    def get_current_job_data_CF_POST(self):
        """
        Gets all COMPLETED POST jobs in the database
        """
        try:
            current_collection = []
            if self.db_version < DB_VERSION_SCHEMA_CHANGES:
                raise Exception("This function requires a newer DB version.")
            if os.path.exists(self.folder_path):
                current_job_data = self._get_current_job_data_CF_POST()
                if current_job_data and len(current_job_data) > 0:
                    # Read Jobs in Experiment Run
                    included_set = set()
                    for job_data in current_job_data:
                        jobitem = JobItem_12(*job_data)
                        if (jobitem.job_name, jobitem.run_id) not in included_set:
                            included_set.add(
                                (jobitem.job_name, jobitem.run_id))
                            current_collection.append(JobData(jobitem.id, jobitem.counter, jobitem.job_name, jobitem.created, jobitem.modified, jobitem.submit, jobitem.start, jobitem.finish, jobitem.status, jobitem.rowtype, jobitem.ncpus,
                                                              jobitem.wallclock, jobitem.qos, jobitem.energy, jobitem.date, jobitem.section, jobitem.member, jobitem.chunk, jobitem.last, jobitem.platform, jobitem.job_id, jobitem.extra_data, jobitem.nnodes, jobitem.run_id))
                    # The tough part is that we need to identifiy the jobs in each package
                    return {run_id: [x for x in current_collection if x.run_id == run_id] for run_id in set([job.run_id for job in current_collection])}
            return {}
        except Exception as exp:
            print((traceback.format_exc()))
            print("Error on returning current job data for ASYPD")
            return {}

    def get_current_run_job_data_json(self, run_id):
        """ Gets run job data in JSON format

        Args:
            run_id (int): Experiment run identifier

        Returns:
            [list, None]: None if no data
        """
        result = []
        try:
            # Get all states
            run_id_job_data = self.get_current_job_data(run_id, True)

            if run_id_job_data:
                for jobdata in run_id_job_data:
                    # Member and Section were exchanged my mistake
                    result.append({"counter": jobdata.counter, "job_name": jobdata.job_name, "created": jobdata.created, "submit": jobdata.submit_datetime_str(), "start": jobdata.start_datetime_str(), "finish": jobdata.finish_datetime_str(
                    ), "queue_time": jobdata.delta_queue_time(), "run_time": jobdata.delta_running_time(), "queue_time_s": jobdata.queuing_time(), "running_time_s": jobdata.running_time(), "ncpus": jobdata.ncpus, "wallclock": jobdata.wallclock, "qos": jobdata.qos, "platform": jobdata.platform, "job_id": jobdata.job_id, "nodes": jobdata.nnodes, "energy": jobdata.energy if jobdata.run_id is not None and jobdata.energy > 0 else "NA", "status": jobdata.status, "date": jobdata.date, "section": jobdata.member, "member": jobdata.section, "chunk": jobdata.chunk, "status_code": Status.STRING_TO_CODE.get(jobdata.status, -1), "status_color": Monitor.color_status(Status.STRING_TO_CODE.get(jobdata.status, -1)), "titletag": job_times_to_text(jobdata.queuing_time(), jobdata.running_time(), jobdata.status)})
        except Exception as exp:
            print((str(exp)))
            return None
        return result

    def get_current_job_data_last(self):
        try:
            current_collection = []
            if self.db_version < DB_VERSION_SCHEMA_CHANGES:
                raise Exception("This function requieres a newer DB version.")
            if os.path.exists(self.folder_path):
                current_job_data = self._get_current_job_data_last()
                if current_job_data:
                    # print("Processing data")
                    time_0 = time.time()
                    # print(len(current_job_data))
                    #i = 0
                    for job_data in current_job_data:
                        # print(i)
                        if self.db_version >= CURRENT_DB_VERSION:
                            jobitem = JobItem_15(*job_data)
                            # If energy, then ignore extra_data
                            current_collection.append(JobData(jobitem.id, jobitem.counter, jobitem.job_name, jobitem.created, jobitem.modified, jobitem.submit, jobitem.start, jobitem.finish, jobitem.status, jobitem.rowtype, jobitem.ncpus,
                                                              jobitem.wallclock, jobitem.qos, jobitem.energy, jobitem.date, jobitem.section, jobitem.member, jobitem.chunk, jobitem.last, jobitem.platform, jobitem.job_id, None if jobitem.energy else jobitem.extra_data, jobitem.nnodes, jobitem.run_id, jobitem.MaxRSS, jobitem.AveRSS, jobitem.out, jobitem.err, jobitem.rowstatus))
                        else:
                            jobitem = JobItem_12(*job_data)
                            # If energy, then ignore extra_data
                            current_collection.append(JobData(jobitem.id, jobitem.counter, jobitem.job_name, jobitem.created, jobitem.modified, jobitem.submit, jobitem.start, jobitem.finish, jobitem.status, jobitem.rowtype, jobitem.ncpus,
                                                              jobitem.wallclock, jobitem.qos, jobitem.energy, jobitem.date, jobitem.section, jobitem.member, jobitem.chunk, jobitem.last, jobitem.platform, jobitem.job_id, None if jobitem.energy else jobitem.extra_data, jobitem.nnodes, jobitem.run_id))
                    # print("Processing data time {0}".format(
                    #     time.time() - time_0))
                    return current_collection
            return None
        except Exception as exp:
            print((traceback.format_exc()))
            print(
                "Error on returning current job data last.")
            return None

    def _get_historic_job_data(self, job_name):
        """

        """
        try:
            if self.conn:
                self.conn.text_factory = str
                cur = self.conn.cursor()
                cur.execute(self.query_job_historic, (job_name,))
                rows = cur.fetchall()
                return rows
            else:
                raise Exception("Not a valid connection.")
        except sqlite3.Error as e:
            if _debug == True:
                print((traceback.format_exc()))
            print(("Error while retrieving job {0} information. {1}".format(
                job_name, str(type(e).__name__))))
            return None

    def _get_experiment_runs(self):
        """[summary]
        """
        try:
            if self.conn:
                self.conn.text_factory = str
                cur = self.conn.cursor()
                if self.db_version >= DB_EXPERIMENT_HEADER_SCHEMA_CHANGES:
                    cur.execute(
                        "SELECT run_id,created,start,finish,chunk_unit,chunk_size,completed,total,failed,queuing,running,submitted,suspended, metadata FROM experiment_run WHERE total > 0 ORDER BY run_id DESC")
                else:
                    cur.execute(
                        "SELECT run_id,created,start,finish,chunk_unit,chunk_size,completed,total,failed,queuing,running,submitted FROM experiment_run WHERE total > 0 ORDER BY run_id DESC")
                rows = cur.fetchall()
                if len(rows) > 0:
                    return rows
                else:
                    return None
            else:
                raise Exception("Not a valid connection.")
        except sqlite3.Error as e:
            if _debug == True:
                print((traceback.format_exc()))
            print(("Error while retrieving runs {0} information. {1}".format(
                str(type(e).__name__), "_get_experiment_runs")))
            return None

    def _get_experiment_run_by_id(self, run_id):
        """
        :param run_id: Run Identifier
        :type run_id: int
        :return: First row that matches the run_id
        :rtype: Row as Tuple
        """
        try:
            if self.conn:
                self.conn.text_factory = str
                cur = self.conn.cursor()
                if self.db_version >= DB_EXPERIMENT_HEADER_SCHEMA_CHANGES:
                    cur.execute(
                        "SELECT run_id,created,start,finish,chunk_unit,chunk_size,completed,total,failed,queuing,running,submitted,suspended, metadata FROM experiment_run WHERE run_id=? and total > 0 ORDER BY run_id DESC", (run_id,))
                else:
                    cur.execute(
                        "SELECT run_id,created,start,finish,chunk_unit,chunk_size,completed,total,failed,queuing,running,submitted FROM experiment_run WHERE run_id=? and total > 0 ORDER BY run_id DESC", (run_id,))
                rows = cur.fetchall()
                if len(rows) > 0:
                    return rows[0]
                else:
                    return None
            else:
                raise Exception("Not a valid connection.")
        except sqlite3.Error as e:
            if _debug == True:
                print((traceback.format_exc()))
            print(("Error while retrieving run {0} information. {1}".format(
                run_id, "_get_experiment_run_by_id")))
            return None

    def _select_pragma_version(self):
        """ Retrieves user_version from database
        """
        try:
            if self.conn:
                self.conn.text_factory = str
                cur = self.conn.cursor()
                cur.execute("pragma user_version;")
                rows = cur.fetchall()
                # print("Result {0}".format(str(rows)))
                if len(rows) > 0:
                    # print(rows)
                    # print("Row " + str(rows[0]))
                    result, = rows[0]
                    # print(result)
                    return int(result) if result >= 0 else None
                else:
                    # Starting value
                    return None
        except sqlite3.Error as e:
            if _debug == True:
                Log.info(traceback.format_exc())
            Log.debug(traceback.format_exc())
            Log.warning("Error while retrieving version: " +
                        str(type(e).__name__))
            return None

    def _get_max_id_experiment_run(self):
        """Return the max id from experiment_run

        :return: max run_id, None
        :rtype: int, None
        """
        try:
            if self.conn:
                self.conn.text_factory = str
                cur = self.conn.cursor()
                if self.db_version >= DB_EXPERIMENT_HEADER_SCHEMA_CHANGES:
                    cur.execute(
                        "SELECT run_id,created,start,finish,chunk_unit,chunk_size,completed,total,failed,queuing,running,submitted,suspended, metadata from experiment_run ORDER BY run_id DESC LIMIT 0, 1")
                else:
                    cur.execute(
                        "SELECT run_id,created,start,finish,chunk_unit,chunk_size,completed,total,failed,queuing,running,submitted from experiment_run ORDER BY run_id DESC LIMIT 0, 1")
                rows = cur.fetchall()
                if len(rows) > 0:
                    return rows[0]
                else:
                    return None
            return None
        except sqlite3.Error as e:
            if _debug == True:
                Log.info(traceback.format_exc())
            Log.debug(traceback.format_exc())
            Log.warning("Error on select max run_id : " +
                        str(type(e).__name__))
            return None

    def _get_current_job_data(self, run_id, all_states=False):
        """
        Get JobData by run_id.
        :param run_id: Run Identifier
        :type run_id: int
        :param all_states: False if only last=1, True all
        :type all_states: bool
        """
        try:
            if self.conn:
                # print("Run {0} states {1} db {2}".format(
                #     run_id, all_states, self.db_version))
                self.conn.text_factory = str
                cur = self.conn.cursor()
                request_string = ""
                if all_states == False:
                    if self.db_version >= CURRENT_DB_VERSION:
                        request_string = "SELECT id, counter, job_name, created, modified, submit, start, finish, status, rowtype, ncpus, wallclock, qos, energy, date, section, member, chunk, last, platform, job_id, extra_data, nnodes, run_id, MaxRSS, AveRSS, out, err, rowstatus  from job_data WHERE run_id=? and last=1 and finish > 0 and rowtype >= 2 ORDER BY id"
                    else:
                        request_string = "SELECT id, counter, job_name, created, modified, submit, start, finish, status, rowtype, ncpus, wallclock, qos, energy, date, section, member, chunk, last, platform, job_id, extra_data, nnodes, run_id from job_data WHERE run_id=? and last=1 and finish > 0 and rowtype >= 2 ORDER BY id"

                else:
                    if self.db_version >= CURRENT_DB_VERSION:
                        request_string = "SELECT id, counter, job_name, created, modified, submit, start, finish, status, rowtype, ncpus, wallclock, qos, energy, date, section, member, chunk, last, platform, job_id, extra_data, nnodes, run_id, MaxRSS, AveRSS, out, err, rowstatus  from job_data WHERE run_id=? and rowtype >= 2 ORDER BY id"
                    else:
                        request_string = "SELECT id, counter, job_name, created, modified, submit, start, finish, status, rowtype, ncpus, wallclock, qos, energy, date, section, member, chunk, last, platform, job_id, extra_data, nnodes, run_id from job_data WHERE run_id=? and rowtype >= 2 ORDER BY id"

                cur.execute(request_string, (run_id,))
                rows = cur.fetchall()
                # print(rows)
                if len(rows) > 0:
                    return rows
                else:
                    return None
        except sqlite3.Error as e:
            if _debug == True:
                print((traceback.format_exc()))
            print(("Error on select job data: {0}".format(
                str(type(e).__name__))))
            return None

    def _get_all_current_job_data(self):
        """
        Returns all job_data in the job_data table of the historical database.
        """
        try:
            if self.conn:
                self.conn.text_factory = str
                cur = self.conn.cursor()
                try:
                    cur.execute("SELECT id, counter, job_name, created, modified, submit, start, finish, status, rowtype, ncpus, wallclock, qos, energy, date, section, member, chunk, last, platform, job_id, extra_data, nnodes, run_id from job_data")
                    print("Normal query successful.")
                except:
                    print("Error on historical retrieval. \tResort to no run_id query")
                    cur.execute("SELECT id, counter, job_name, created, modified, submit, start, finish, status, rowtype, ncpus, wallclock, qos, energy, date, section, member, chunk, last, platform, job_id, extra_data, 0 as nnodes, 0 as run_id from job_data")

                rows = cur.fetchall()
                if len(rows) > 0:
                    return rows
                else:
                    return None
        except sqlite3.Error as e:
            if _debug == True:
                print((traceback.format_exc()))
            print(("Error on select job data: {0}".format(
                str((type(e).__name__)))))
            return None

    def _get_current_job_data_CF_SIM(self):
        """
        Gets current job data for completed and failed jobs and SIM section (member in table)
        """
        try:
            if self.conn:
                # print("Run {0} states {1}".format(run_id, all_states))
                self.conn.text_factory = str
                cur = self.conn.cursor()
                cur.execute("SELECT id, counter, job_name, created, modified, submit, start, finish, status, rowtype, ncpus, wallclock, qos, energy, date, section, member, chunk, last, platform, job_id, extra_data, nnodes, run_id from job_data WHERE member = 'SIM' or section = 'SIM' and status in ('COMPLETED') ORDER BY id DESC")  # Only consider COMPLETED
                rows = cur.fetchall()
                # print(rows)
                if len(rows) > 0:
                    return rows
                else:
                    return None
        except sqlite3.Error as e:
            if _debug == True:
                print((traceback.format_exc()))
            print(("Error on select job CF SIM: {0}".format(
                str(type(e).__name__))))
            return None

    def _get_current_job_data_CF_POST(self):
        """
        Gets current job data for completed POST jobs (member in table)
        """
        try:
            if self.conn:
                self.conn.text_factory = str
                cur = self.conn.cursor()
                cur.execute("SELECT id, counter, job_name, created, modified, submit, start, finish, status, rowtype, ncpus, wallclock, qos, energy, date, section, member, chunk, last, platform, job_id, extra_data, nnodes, run_id from job_data WHERE member = 'POST' or section = 'POST' and status in ('COMPLETED') ORDER BY id DESC")  # Only consider COMPLETED
                rows = cur.fetchall()
                if len(rows) > 0:
                    return rows
                else:
                    return None
        except sqlite3.Error as e:
            if _debug == True:
                print((traceback.format_exc()))
            print(("Error on select job CF POST: {0}".format(
                str(type(e).__name__))))
            return None

    def _get_current_job_data_last(self):
        try:
            if self.conn:
                # print("Getting historic data.")
                self.conn.text_factory = str
                cur = self.conn.cursor()
                request_string = "SELECT id, counter, job_name, created, modified, submit, start, finish, status, rowtype, ncpus, wallclock, qos, energy, date, section, member, chunk, last, platform, job_id, extra_data, nnodes, run_id from job_data WHERE last=1 and finish > 0 and rowtype >= 2 ORDER BY id"
                if self.db_version >= CURRENT_DB_VERSION:
                    request_string = "SELECT id, counter, job_name, created, modified, submit, start, finish, status, rowtype, ncpus, wallclock, qos, energy, date, section, member, chunk, last, platform, job_id, extra_data, nnodes, run_id, MaxRSS, AveRSS, out, err, rowstatus from job_data WHERE last=1 and finish > 0 and rowtype >= 2 ORDER BY id"
                cur.execute(request_string)
                rows = cur.fetchall()
                # print("Retrieved historic.")
                return rows
        except sqlite3.Error as e:
            if _debug == True:
                print((traceback.format_exc()))
            print(("Error on select job data: {0}".format(
                str(type(e).__name__))))
            return None

    def _get_job_package_info(self, run_id, package_id):
        try:
            if self.conn:
                print("Getting historic package.")
                self.conn.text_factory = str
                cur = self.conn.cursor()
                cur.execute(
                    "SELECT id, job_name, submit, start, finish, job_id, extra_data from job_data where run_id=? and rowtype=? and status in ('COMPLETED')", (run_id, package_id,))
                rows = cur.fetchall()
                print("Retrieved historic package.")
                return rows
        except sqlite3.Error as e:
            if _debug == True:
                print((traceback.format_exc()))
            print(("Error on select job data: {0}".format(
                str(type(e).__name__))))
            return None

    def _get_job_packages_info_per_run_id(self, run_id):
        try:
            if self.conn:
                self.conn.text_factory = str
                cur = self.conn.cursor()
                cur.execute(
                    "SELECT id, job_name, submit, start, finish, job_id, extra_data, rowtype from job_data where run_id=? and rowtype > 2 and status in ('COMPLETED') ORDER BY id DESC", (run_id,))
                rows = cur.fetchall()
                return rows
        except sqlite3.Error as e:
            if _debug == True:
                print((traceback.format_exc()))
            print(("Error on select job data: {0}".format(
                str(type(e).__name__))))
            return None

    def _update_job_data(self, job_data):
        """Updateing processed job_data

        Args:
            job_data ([type]): [description]

        Returns:
            [type]: [description]
        """
        try:
            if self.conn:
                sql = ''' UPDATE job_data SET energy=?, modified=? WHERE id=? '''
                cur = self.conn.cursor()
                cur.execute(sql, (job_data.energy, datetime.today().strftime(
                    '%Y-%m-%d-%H:%M:%S'), job_data._id))
                # self.conn.commit()
                return True
            return None
        except sqlite3.Error as e:
            if _debug == True:
                print((traceback.format_exc()))
            print((traceback.format_exc()))
            print(("Error on Insert : {}".format(str(type(e).__name__))))
            return None

    def _update_many_job_data(self, job_data_list):
        try:
            if self.conn:
                sql = ''' UPDATE job_data SET energy=?, modified=? WHERE id=? '''
                cur = self.conn.cursor()
                cur.executemany(sql, job_data_list)
                # (job_data.energy, datetime.today().strftime(
                #    '%Y-%m-%d-%H:%M:%S'), job_data._id)
                # self.conn.commit()
                return True
            return None
        except Exception as exp:
            if _debug == True:
                print((traceback.format_exc()))
            # print(traceback.format_exc())
            print(("Error on _update_many_job_data : {}".format(
                str(exp))))
            return None


def parse_output_number(string_number):
    """
    Parses number in format 1.0K 1.0M 1.0G

    :param string_number: String representation of number
    :type string_number: str
    :return: number in float format
    :rtype: float
    """
    number = 0.0
    if (string_number):
        if string_number == "NA":
            return 0.0
        last_letter = string_number.strip()[-1]
        multiplier = 1.0
        if last_letter == "G":
            multiplier = 1000000000.0
            number = string_number[:-1]
        elif last_letter == "M":
            multiplier = 1000000.0
            number = string_number[:-1]
        elif last_letter == "K":
            multiplier = 1000.0
            number = string_number[:-1]
        else:
            number = string_number
        try:
            number = float(number) * multiplier
        except Exception as exp:
            number = 0.0
            pass
    return number
