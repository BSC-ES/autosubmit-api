from time import sleep

import os

from bscearth.utils.log import Log
from autosubmitAPIwu.job.job_common import Status


class Platform(object):
    """
    Class to manage the connections to the different platforms.
    """

    def __init__(self, expid, name, config):
        """

        :param config:
        :param expid:
        :param name:
        """
        self.expid = expid
        self.name = name
        self.config = config
        self.tmp_path = os.path.join(self.config.LOCAL_ROOT_DIR, self.expid, self.config.LOCAL_TMP_DIR)
        self._serial_platform = None
        self._serial_queue = None
        self._default_queue = None
        self.processors_per_node = None
        self.scratch_free_space = None
        self.custom_directives = None
        self.host = ''
        self.user = ''
        self.project = ''
        self.budget = ''
        self.reservation = ''
        self.exclusivity = ''
        self.type = ''
        self.scratch = ''
        self.temp_dir = ''
        self.root_dir = ''
        self.service = None
        self.scheduler = None
        self.directory = None
        self.hyperthreading = 'false'
        self.max_wallclock = ''
        self.max_processors = None
        self._allow_arrays = False
        self._allow_wrappers = False
        self._allow_python_jobs = True

    @property
    def serial_platform(self):
        """
        Platform to use for serial jobs
        :return: platform's object
        :rtype: platform
        """
        if self._serial_platform is None:
            return self
        return self._serial_platform

    @serial_platform.setter
    def serial_platform(self, value):
        self._serial_platform = value

    @property
    def queue(self):
        """
        Queue to use for jobs
        :return: queue's name
        :rtype: str
        """
        if self._default_queue is None:
            return ''
        return self._default_queue

    @queue.setter
    def queue(self, value):
        self._default_queue = value

    @property
    def serial_queue(self):
        """
        Queue to use for serial jobs
        :return: queue's name
        :rtype: str
        """
        if self._serial_queue is None:
            return self.queue
        return self._serial_queue

    @serial_queue.setter
    def serial_queue(self, value):
        self._serial_queue = value

    @property
    def allow_arrays(self):
        return self._allow_arrays is True

    @property
    def allow_wrappers(self):
        return self._allow_wrappers is True

    @property
    def allow_python_jobs(self):
        return self._allow_python_jobs is True

    def add_parameters(self, parameters, main_hpc=False):
        """
        Add parameters for the current platform to the given parameters list

        :param parameters: parameters list to update
        :type parameters: dict
        :param main_hpc: if it's True, uses HPC instead of NAME_ as prefix for the parameters
        :type main_hpc: bool
        """
        if main_hpc:
            prefix = 'HPC'
            parameters['SCRATCH_DIR'.format(prefix)] = self.scratch
        else:
            prefix = self.name + '_'

        parameters['{0}ARCH'.format(prefix)] = self.name
        parameters['{0}HOST'.format(prefix)] = self.host
        parameters['{0}QUEUE'.format(prefix)] = self.queue
        parameters['{0}USER'.format(prefix)] = self.user
        parameters['{0}PROJ'.format(prefix)] = self.project
        parameters['{0}BUDG'.format(prefix)] = self.budget
        parameters['{0}RESERVATION'.format(prefix)] = self.reservation
        parameters['{0}EXCLUSIVITY'.format(prefix)] = self.exclusivity
        parameters['{0}TYPE'.format(prefix)] = self.type
        parameters['{0}SCRATCH_DIR'.format(prefix)] = self.scratch
        parameters['{0}TEMP_DIR'.format(prefix)] = self.temp_dir
        parameters['{0}ROOTDIR'.format(prefix)] = self.root_dir

        parameters['{0}LOGDIR'.format(prefix)] = self.get_files_path()

    def send_file(self, filename):
        """
        Sends a local file to the platform
        :param filename: name of the file to send
        :type filename: str
        """
        raise NotImplementedError

    def move_file(self, src, dest):
        """
        Moves a file on the platform
        :param src: source name
        :type src: str
        :param dest: destination name
        :type dest: str
        """
        raise NotImplementedError

    def get_file(self, filename, must_exist=True, relative_path=''):
        """
        Copies a file from the current platform to experiment's tmp folder

        :param filename: file name
        :type filename: str
        :param must_exist: If True, raises an exception if file can not be copied
        :type must_exist: bool
        :param relative_path: relative path inside tmp folder
        :type relative_path: str
        :return: True if file is copied successfully, false otherwise
        :rtype: bool
        """
        raise NotImplementedError

    def get_files(self, files, must_exist=True, relative_path=''):
        """
        Copies some files from the current platform to experiment's tmp folder

        :param files: file names
        :type files: [str]
        :param must_exist: If True, raises an exception if file can not be copied
        :type must_exist: bool
        :param relative_path: relative path inside tmp folder
        :type relative_path: str
        :return: True if file is copied successfully, false otherwise
        :rtype: bool
        """
        for filename in files:
            self.get_file(filename, must_exist, relative_path)

    def delete_file(self, filename):
        """
        Deletes a file from this platform

        :param filename: file name
        :type filename: str
        :return: True if succesful or file does no exists
        :rtype: bool
        """
        raise NotImplementedError

    def get_logs_files(self, exp_id, remote_logs):
        """
        Get the given LOGS files
        
        :param exp_id: experiment id
        :type exp_id: str
        :param remote_logs: names of the log files
        :type remote_logs: (str, str)
        """
        (job_out_filename, job_err_filename) = remote_logs
        self.get_files([job_out_filename, job_err_filename], False, 'LOG_{0}'.format(exp_id))

    def get_completed_files(self, job_name, retries=0):
        """
        Get the COMPLETED file of the given job


        :param job_name: name of the job
        :type job_name: str
        :param retries: Max number of tries to get the file
        :type retries: int
        :return: True if successful, false otherwise
        :rtype: bool
        """
        while True:
            if self.get_file('{0}_COMPLETED'.format(job_name), False):
                return True
            if retries == 0:
                return False
            retries -= 1
            sleep(3)

    def remove_stat_file(self, job_name):
        """
        Removes *STAT* files from remote

        :param job_name: name of job to check
        :type job_name: str
        :return: True if successful, False otherwise
        :rtype: bool
        """
        filename = job_name + '_STAT'
        if self.delete_file(filename):
            Log.debug('{0}_STAT have been removed', job_name)
            return True
        return False

    def remove_completed_file(self, job_name):
        """
        Removes *COMPLETED* files from remote

        :param job_name: name of job to check
        :type job_name: str
        :return: True if successful, False otherwise
        :rtype: bool
        """
        filename = job_name + '_COMPLETED'
        if self.delete_file(filename):
            Log.debug('{0} been removed', filename)
            return True
        return False

    def get_stat_file(self, job_name, retries=0):
        """
        Copies *STAT* files from remote to local

        :param retries: number of intents to get the completed files
        :type retries: int
        :param job_name: name of job to check
        :type job_name: str
        :return: True if succesful, False otherwise
        :rtype: bool
        """
        filename = job_name + '_STAT'
        stat_local_path = os.path.join(self.config.LOCAL_ROOT_DIR, self.expid, self.config.LOCAL_TMP_DIR, filename)
        if os.path.exists(stat_local_path):
            os.remove(stat_local_path)

        while True:
            if self.get_file(filename, False):
                Log.debug('{0}_STAT file have been transfered', job_name)
                return True
            if retries == 0:
                break
            retries -= 1
            # wait five seconds to check get file
            sleep(5)

        Log.debug('Something did not work well when transferring the STAT file')
        return False

    def get_files_path(self):
        """
        Get the path to the platform's LOG directory

        :return: platform's LOG directory
        :rtype: str
        """
        if self.type == "local":
            path = os.path.join(self.root_dir, self.config.LOCAL_TMP_DIR, 'LOG_{0}'.format(self.expid))
        else:
            path = os.path.join(self.root_dir, 'LOG_{0}'.format(self.expid))
        return path

    def submit_job(self, job, scriptname):
        """
        Submit a job from a given job object.

        :param job: job object
        :type job: autosubmit.job.job.Job
        :param scriptname: job script's name
        :rtype scriptname: str
        :return: job id for the submitted job
        :rtype: int
        """
        raise NotImplementedError

    def check_job(self, jobid, default_status=Status.COMPLETED, retries=5):
        """
        Checks job running status

        :param retries: retries
        :param jobid: job id
        :type jobid: str
        :param default_status: status to assign if it can be retrieved from the platform
        :type default_status: autosubmit.job.job_common.Status
        :return: current job status
        :rtype: autosubmit.job.job_common.Status
        """
        raise NotImplementedError
