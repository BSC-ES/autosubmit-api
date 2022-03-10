import datetime
import subprocess
from time import sleep

import os
import radical.saga as saga

from bscearth.utils.log import Log
from bscearth.utils.date import date2str
from autosubmitAPIwu.job.job_common import Status, Type
from autosubmitAPIwu.platforms.platform import Platform


class SagaPlatform(Platform):
    """
    Class to manage the connections to the different platforms with the SAGA library.
    """

    def __init__(self, expid, name, config):
        """

        :param config:
        :param expid:
        :param name:
        """
        Platform.__init__(self, expid, name, config)
        self._attributes = None

    def send_file(self, filename):
        """
        Sends a local file to the platform
        :param filename: name of the file to send
        :type filename: str
        """
        self.delete_file(filename)
        if self.type == 'ecaccess':
            try:
                subprocess.check_call(['ecaccess-file-mkdir', '{0}:{1}'.format(self.host, self.root_dir)])
                subprocess.check_call(['ecaccess-file-mkdir', '{0}:{1}'.format(self.host, self.get_files_path())])
                destiny_path = os.path.join(self.get_files_path(), filename)
                subprocess.check_call(['ecaccess-file-put', os.path.join(self.tmp_path, filename),
                                       '{0}:{1}'.format(self.host, destiny_path)])
                subprocess.check_call(['ecaccess-file-chmod', '740', '{0}:{1}'.format(self.host, destiny_path)])
                return
            except subprocess.CalledProcessError:
                raise Exception("Could't send file {0} to {1}:{2}".format(os.path.join(self.tmp_path, filename),
                                                                          self.host, self.get_files_path()))
        # noinspection PyTypeChecker
        out = saga.filesystem.File("file://{0}".format(os.path.join(self.tmp_path, filename)),
                                   session=self.service.session)
        if self.type == 'local':
            out.copy("file://{0}".format(os.path.join(self.tmp_path, 'LOG_' + self.expid, filename)),
                     saga.filesystem.CREATE_PARENTS)
        else:
            workdir = self.get_workdir(self.get_files_path())
            out.copy(workdir.get_url())
            workdir.close()
        out.close()

    def get_workdir(self, path):
        """
        Creates and returns a DIrectory object for the current workdir

        :param path: path to the workdir
        :type path: str
        :return: working directory object
        :rtype: saga.file.Directory
        """
        if not path:
            raise Exception("Workdir invalid")

        sftp_directory = 'sftp://{0}{1}'.format(self.host, path)
        try:
            # noinspection PyTypeChecker
            return saga.filesystem.Directory(sftp_directory, session=self.service.session)
        except saga.BadParameter:
            try:
                # noinspection PyTypeChecker
                return saga.filesystem.Directory(sftp_directory,
                                                 saga.filesystem.CREATE,
                                                 session=self.service.session)
            except saga.BadParameter:
                new_directory = os.path.split(path)[1]
                parent = self.get_workdir(os.path.dirname(path))
                parent.make_dir(new_directory)
                parent.close()
                # noinspection PyTypeChecker
                return saga.filesystem.Directory(sftp_directory, session=self.service.session)

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

        local_path = os.path.join(self.tmp_path, relative_path)
        if not os.path.exists(local_path):
            os.makedirs(local_path)

        file_path = os.path.join(local_path, filename)
        if os.path.exists(file_path):
            os.remove(file_path)

        if self.type == 'ecaccess':
            try:
                subprocess.check_call(['ecaccess-file-get', '{0}:{1}'.format(self.host,
                                                                             os.path.join(self.get_files_path(),
                                                                                          filename)),
                                       file_path])
                return True
            except subprocess.CalledProcessError:
                if must_exist:
                    raise Exception("Could't get file {0} from {1}:{2}".format(file_path,
                                                                               self.host, self.get_files_path()))
                return False

        if not self.exists_file(filename):
            if must_exist:
                raise Exception('File {0} does not exists'.format(filename))
            return False

        out = self.directory.open(os.path.join(str(self.directory.url), filename))

        out.copy("file://{0}".format(file_path))
        out.close()
        return True

    def exists_file(self, filename):
        """
        Checks if a file exists on this platform

        :param filename: file name
        :type filename: str
        :return: True if it exists, False otherwise
        """
        # noinspection PyBroadException
        if not self.directory:
            try:
                if self.type == 'local':
                    # noinspection PyTypeChecker
                    self.directory = saga.filesystem.Directory("file://{0}".format(os.path.join(self.tmp_path,
                                                                                                'LOG_' + self.expid)))
                else:
                    # noinspection PyTypeChecker
                    self.directory = saga.filesystem.Directory("sftp://{0}{1}".format(self.host, self.get_files_path()),
                                                               session=self.service.session)
            except:
                return False

        # noinspection PyBroadException
        try:
            self.directory.list(filename)
        except:
            return False

        return True

    def delete_file(self, filename):
        """
        Deletes a file from this platform

        :param filename: file name
        :type filename: str
        :return: True if succesful or file does no exists
        :rtype: bool
        """
        if self.type == 'ecaccess':
            try:
                subprocess.check_call(['ecaccess-file-delete',
                                       '{0}:{1}'.format(self.host, os.path.join(self.get_files_path(), filename))])
                return True
            except subprocess.CalledProcessError:
                return True

        if not self.exists_file(filename):
            return True

        try:
            if self.type == 'local':
                # noinspection PyTypeChecker
                out = saga.filesystem.File("file://{0}".format(os.path.join(self.tmp_path, 'LOG_' + self.expid,
                                                                            filename)))
            else:
                # noinspection PyTypeChecker
                out = saga.filesystem.File("sftp://{0}{1}".format(self.host, os.path.join(self.get_files_path(),
                                                                                          filename)),
                                           session=self.service.session)
            out.remove()
            out.close()
            return True
        except saga.DoesNotExist:
            return True

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
        saga_job = self.create_saga_job(job, scriptname)
        saga_job.run()
        return saga_job.id

    def create_saga_job(self, job, script_name):
        """
        Creates a saga job from a given job object.

        :param job: job object
        :type job: autosubmit.job.job.Job
        :param script_name: job script's name
        :type script_name: str
        :return: saga job object for the given job
        :rtype: saga.job.Job
        """
        jd = saga.job.Description()
        if job.type == Type.BASH:
            binary = 'source'
        elif job.type == Type.PYTHON:
            binary = 'python '
        elif job.type == Type.R:
            binary = 'Rscript'

        # jd.executable = '{0} {1}'.format(binary, os.path.join(self.get_files_path(), script_name))
        jd.executable = os.path.join(self.get_files_path(), script_name)
        jd.working_directory = self.get_files_path()

        str_datetime = date2str(datetime.datetime.now(), 'S')
        out_filename = "{0}.{1}.out".format(job.name, str_datetime)
        err_filename = "{0}.{1}.err".format(job.name, str_datetime)
        job.local_logs = (out_filename, err_filename)
        jd.output = out_filename
        jd.error = err_filename

        self.add_attribute(jd, 'Name', job.name)

        wall_clock = job.parameters["WALLCLOCK"]
        if wall_clock == '':
            wall_clock = 0
        else:
            wall_clock = wall_clock.split(':')
            wall_clock = int(wall_clock[0]) * 60 + int(wall_clock[1])
        self.add_attribute(jd, 'WallTimeLimit', wall_clock)

        self.add_attribute(jd, 'Queue', job.parameters["CURRENT_QUEUE"])

        project = job.parameters["CURRENT_BUDG"]
        if job.parameters["CURRENT_RESERVATION"] != '' or job.parameters["CURRENT_EXCLUSIVITY"] == 'true':
            project += ':' + job.parameters["CURRENT_RESERVATION"] + ':'
            if job.parameters["CURRENT_EXCLUSIVITY"] == 'true':
                project += job.parameters["CURRENT_EXCLUSIVITY"]
        self.add_attribute(jd, 'Project', project)

        self.add_attribute(jd, 'TotalCPUCount', job.parameters["NUMPROC"])
        if job.parameters["NUMTASK"] is not None:
            self.add_attribute(jd, 'ProcessesPerHost', job.parameters["NUMTASK"])
        self.add_attribute(jd, 'ThreadsPerProcess', job.parameters["NUMTHREADS"])
        self.add_attribute(jd, 'TotalPhysicalMemory', job.parameters["MEMORY"])
        saga_job = self.service.create_job(jd)
        return saga_job

    def add_attribute(self, jd, name, value):
        """
        Adds an attribute to a given job descriptor, only if it is supported by the adaptor.

        :param jd: job descriptor to use:
        :type jd: saga.job.Descriptor
        :param name: attribute's name
        :type name: str
        :param value: attribute's value
        """
        if self._attributes is None:
            # noinspection PyProtectedMember
            self._attributes = self.service._adaptor._adaptor._info['capabilities']['jdes_attributes']
        if name not in self._attributes or not value:
            return
        jd.set_attribute(name, value)

    def check_job(self, job_id, default_status=Status.COMPLETED, retries=10):
        """
        Checks job running status

        :param retries: retries
        :param job_id: job id
        :type job_id: str
        :param default_status: status to assign if it can be retrieved from the platform
        :type default_status: autosubmit.job.job_common.Status
        :return: current job status
        :rtype: autosubmit.job.job_common.Status
        """
        saga_status = None
        while saga_status is None and retries >= 0:
            try:
                if job_id not in self.service.jobs:
                    return Status.COMPLETED
                saga_status = self.service.get_job(job_id).state
            except Exception as e:
                # If SAGA can not get the job state, we change it to completed
                # It will change to FAILED if not COMPLETED file is present
                Log.debug('Can not get job state: {0}', e)
                retries -= 1
                sleep(5)

        if saga_status is None:
            return default_status
        elif saga_status == saga.job.UNKNOWN:
            return Status.UNKNOWN
        elif saga_status == saga.job.PENDING:
            return Status.QUEUING
        elif saga_status == saga.job.FAILED:
            return Status.FAILED
        elif saga_status == saga.job.CANCELED:
            return Status.FAILED
        elif saga_status == saga.job.DONE:
            return Status.COMPLETED
        elif saga_status == saga.job.RUNNING:
            return Status.RUNNING
        elif saga_status == saga.job.SUSPENDED:
            return Status.SUSPENDED
