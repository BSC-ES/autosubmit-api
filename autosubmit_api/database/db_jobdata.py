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
import traceback
import collections
from typing import List, Optional, Tuple
import portalocker
from datetime import datetime, timedelta
from json import loads
from autosubmit_api.logger import logger
from autosubmit_api.components.jobs.utils import generate_job_html_title

# from networkx import DiGraph
from autosubmit_api.config.basicConfig import APIBasicConfig
from autosubmit_api.monitor.monitor import Monitor
from autosubmit_api.performance.utils import calculate_ASYPD_perjob
from autosubmit_api.components.jobs.job_factory import SimJob
from autosubmit_api.common.utils import (
    get_jobs_with_no_outliers,
    Status,
    datechunk_to_year,
)

# from autosubmitAPIwu.job.job_list
# import autosubmitAPIwu.experiment.common_db_requests as DbRequests
from bscearth.utils.date import Log

from autosubmit_api.repositories.experiment_run import create_experiment_run_repository
from autosubmit_api.repositories.graph_layout import create_exp_graph_layout_repository
from autosubmit_api.repositories.job_data import create_experiment_job_data_repository


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
        except Exception:
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


class ExperimentGraphDrawing:
    def __init__(self, expid: str):
        """
        Sets and validates graph drawing.

        :param expid: Name of experiment
        """
        APIBasicConfig.read()
        self.expid = expid
        self.folder_path = APIBasicConfig.LOCAL_ROOT_DIR
        self.graph_data_repository = create_exp_graph_layout_repository(expid)
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
        except Exception:
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
        lock_name = "calculation_{}_in_progress.lock".format(self.expid) if independent is True else self.lock_name
        lock_path_file = os.path.join(self.folder_path, lock_name)
        try:
            with portalocker.Lock(lock_path_file, timeout=1) as fh:
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

    def _get_current_position(self) -> List[Tuple[int, str, int, int]]:
        """
        Get all registers from experiment_graph_draw.\n
        :return: row content: id, job_name, x, y
        :rtype: 4-tuple (int, str, int, int)
        """
        try:
            result = self.graph_data_repository.get_all()
            return [
                (item.id, item.job_name, item.x, item.y)
                for item in result
            ]
        except Exception as exp:
            print((traceback.format_exc()))
            print((str(exp)))
            return None

    def _insert_many_graph_coordinates(
        self, values: List[Tuple[str, int, int]]
    ) -> Optional[int]:
        """
        Create many graph coordinates
        """
        try:
            _vals = [
                {"job_name": item[0], "x": item[1], "y": item[2]} for item in values
            ]
            logger.debug(_vals)
            return self.graph_data_repository.insert_many(_vals)
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
            self.graph_data_repository.delete_all()
        except Exception as exp:
            print((traceback.format_exc()))
            print(("Error on Database clear: {}".format(str(exp))))
            return False
        return True

class JobDataStructure:
    def __init__(self, expid: str, basic_config: APIBasicConfig):
        """Initializes the object based on the unique identifier of the experiment.

        Args:
            expid (str): Experiment identifier
        """
        self.expid = expid
        self.experiment_run_data_repository = create_experiment_run_repository(expid)
        self.experiment_job_data_repository = create_experiment_job_data_repository(
            expid
        )

    def __str__(self):
        return f"Run and job data of experiment {self.expid}"

    def get_max_id_experiment_run(self) -> Optional[ExperimentRun]:
        """
        Get last (max) experiment run object.
        :return: ExperimentRun data
        :rtype: ExperimentRun object
        """
        try:
            current_experiment_run = self.experiment_run_data_repository.get_last_run()
            return ExperimentRun(
                current_experiment_run.run_id,
                current_experiment_run.created,
                current_experiment_run.start,
                current_experiment_run.finish,
                current_experiment_run.chunk_unit,
                current_experiment_run.chunk_size,
                current_experiment_run.completed,
                current_experiment_run.total,
                current_experiment_run.failed,
                current_experiment_run.queuing,
                current_experiment_run.running,
                current_experiment_run.submitted,
                current_experiment_run.suspended,
                current_experiment_run.metadata,
                current_experiment_run.modified,
            )
        except Exception as exc:
            print((str(exc)))
            print((traceback.format_exc()))
            return None

    def get_experiment_run_by_id(self, run_id: int) -> Optional[ExperimentRun]:
        """
        Get experiment run stored in database by run_id
        """
        try:
            current_experiment_run = self.experiment_run_data_repository.get_run_by_id(
                run_id
            )
            return ExperimentRun(
                current_experiment_run.run_id,
                current_experiment_run.created,
                current_experiment_run.start,
                current_experiment_run.finish,
                current_experiment_run.chunk_unit,
                current_experiment_run.chunk_size,
                current_experiment_run.completed,
                current_experiment_run.total,
                current_experiment_run.failed,
                current_experiment_run.queuing,
                current_experiment_run.running,
                current_experiment_run.submitted,
                current_experiment_run.suspended,
                current_experiment_run.metadata,
                current_experiment_run.modified,
            )
        except Exception as exc:
            if _debug is True:
                Log.info(traceback.format_exc())
            Log.debug(traceback.format_exc())
            Log.warning(
                "Autosubmit couldn't retrieve experiment run. get_experiment_run_by_id. Exception {0}".format(
                    str(exc)
                )
            )
            return None

    def get_current_job_data(self, run_id: int) -> Optional[List[JobData]]:
        """
        Gets the job historical data for a run_id.
        :param run_id: Run identifier
        :type run_id: int
        """
        try:
            current_job_data = (
                self.experiment_job_data_repository.get_last_job_data_by_run_id(run_id)
            )

            current_collection = []
            for job_data in current_job_data:
                current_collection.append(
                    JobData(
                        _id=job_data.id,
                        counter=job_data.counter,
                        job_name=job_data.job_name,
                        created=job_data.created,
                        modified=job_data.modified,
                        submit=job_data.submit,
                        start=job_data.start,
                        finish=job_data.finish,
                        status=job_data.status,
                        rowtype=job_data.rowtype,
                        ncpus=job_data.ncpus,
                        wallclock=job_data.wallclock,
                        qos=job_data.qos,
                        energy=job_data.energy,
                        date=job_data.date,
                        section=job_data.section,
                        member=job_data.member,
                        chunk=job_data.chunk,
                        last=job_data.last,
                        platform=job_data.platform,
                        job_id=job_data.job_id,
                        extra_data=job_data.extra_data,
                        nnodes=job_data.nnodes,
                        run_id=job_data.run_id,
                        MaxRSS=job_data.MaxRSS,
                        AveRSS=job_data.AveRSS,
                        out=job_data.out,
                        err=job_data.err,
                        rowstatus=job_data.rowstatus,
                    )
                )

            return current_collection
        except Exception:
            print((traceback.format_exc()))
            print(("Error on returning current job data. run_id {0}".format(run_id)))
            return None
