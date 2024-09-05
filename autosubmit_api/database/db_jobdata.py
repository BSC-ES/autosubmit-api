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
import sqlite3
import collections
import portalocker
from datetime import datetime, timedelta
from json import loads
from time import mktime
from autosubmit_api.components.jobs.utils import generate_job_html_title
# from networkx import DiGraph
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.monitor.monitor import Monitor
from autosubmit_api.performance.utils import calculate_ASYPD_perjob
from autosubmit_api.components.jobs.job_factory import SimJob
from autosubmit_api.common.utils import get_jobs_with_no_outliers, Status, datechunk_to_year
# from autosubmitAPIwu.job.job_list
# import autosubmitAPIwu.experiment.common_db_requests as DbRequests
from bscearth.utils.date import Log

from autosubmit_api.persistance.experiment import ExperimentPaths


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
        return generate_job_html_title(self.job_name, Monitor.color_status(Status.STRING_TO_CODE[self.status]), self.status)

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
        except Exception:
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
                self.conn.commit()
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
        exp_paths = ExperimentPaths(expid)
        self.folder_path = APIBasicConfig.LOCAL_ROOT_DIR
        self.database_path = exp_paths.graph_data_db
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
                    if len(splitList) > 1 and splitList[0].decode() == "node":

                        self.coordinates.append((splitList[1].decode(), int(
                            float(splitList[2].decode()) * 90), int(float(splitList[3].decode()) * -90)))
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

    def __init__(self, expid: str, basic_config: APIBasicConfig):
        """Initializes the object based on the unique identifier of the experiment.

        Args:
            expid (str): Experiment identifier
        """
        MainDataBase.__init__(self, expid)
        # BasicConfig.read()
        # self.expid = expid
        self.folder_path = basic_config.JOBDATA_DIR
        exp_paths = ExperimentPaths(expid)
        self.database_path = exp_paths.job_data_db
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
