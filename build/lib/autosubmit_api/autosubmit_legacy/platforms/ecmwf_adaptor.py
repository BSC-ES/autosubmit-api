""" LSF mn adaptor implementation
"""

import re
import os
import time
import threading
import radical.saga as saga

# noinspection PyPackageRequirements
import radical.utils.threads as sut
import saga.url as surl
import saga.utils.pty_shell
import saga.adaptors.base
import saga.adaptors.cpi.job
import saga.adaptors.loadl.loadljob
import saga.adaptors.pbs.pbsjob
import saga.adaptors.cpi.decorators
from autosubmitAPIwu.config.basicConfig import BasicConfig

SYNC_CALL = saga.adaptors.cpi.decorators.SYNC_CALL
ASYNC_CALL = saga.adaptors.cpi.decorators.ASYNC_CALL

SYNC_WAIT_UPDATE_INTERVAL = 1  # seconds
MONITOR_UPDATE_INTERVAL = 3  # seconds


# --------------------------------------------------------------------
#
# noinspection PyProtectedMember,PyPep8Naming,PyMissingOrEmptyDocstring
class _job_state_monitor(threading.Thread):
    """ thread that periodically monitors job states
    """

    def __init__(self, job_service):

        self.logger = job_service._logger
        self.js = job_service
        self._stop = sut.Event()

        super(_job_state_monitor, self).__init__()
        self.setDaemon(True)

    def stop(self):
        self._stop.set()

    def stopped(self):
        return self._stop.isSet()

    def run(self):
        while self.stopped() is False:
            try:
                # do bulk updates here! we don't want to pull information
                # job by job. that would be too inefficient!
                jobs = self.js.jobs
                job_keys = jobs.keys()

                for job in job_keys:
                    # if the job hasn't been started, we can't update its
                    # state. we can tell if a job has been started if it
                    # has a job id
                    if jobs[job].get('job_id', None) is not None:
                        # we only need to monitor jobs that are not in a
                        # terminal state, so we can skip the ones that are
                        # either done, failed or canceled
                        state = jobs[job]['state']
                        if (state != saga.job.DONE) and (state != saga.job.FAILED) and (state != saga.job.CANCELED):

                            job_info = self.js._job_get_info(job)
                            self.logger.info(
                                "Job monitoring thread updating Job %s (state: %s)" % (job, job_info['state']))

                            if job_info['state'] != jobs[job]['state']:
                                # fire job state callback if 'state' has changed
                                job._api()._attributes_i_set('state', job_info['state'], job._api()._UP, True)

                            # update job info
                            self.js.jobs[job] = job_info

                time.sleep(MONITOR_UPDATE_INTERVAL)
            except Exception as e:
                self.logger.warning("Exception caught in job monitoring thread: %s" % e)


# --------------------------------------------------------------------
#
def log_error_and_raise(message, exception, logger):
    """
    Logs an 'error' message and subsequently throws an exception

    :param message: message to show
    :type message: str
    :param exception: exception to raise
    :param logger: logger to use
    """
    logger.error(message)
    raise exception(message)


# --------------------------------------------------------------------
#
def _ecaccess_to_saga_jobstate(ecaccess_state):
    """ translates a mn one-letter state to saga
    """
    if ecaccess_state in ['EXEC']:
        return saga.job.RUNNING
    elif ecaccess_state in ['INIT', 'RETR', 'STDBY', 'WAIT']:
        return saga.job.PENDING
    elif ecaccess_state in ['DONE']:
        return saga.job.DONE
    elif ecaccess_state in ['STOP']:
        return saga.job.FAILED
    elif ecaccess_state in ['USUSP', 'SSUSP', 'PSUSP']:
        return saga.job.SUSPENDED
    else:
        return saga.job.UNKNOWN

_PTY_TIMEOUT = 2.0

# --------------------------------------------------------------------
# the adaptor name
#
_ADAPTOR_NAME = "autosubmit.platforms.ecmwf_adaptor"
_ADAPTOR_SCHEMAS = ["ecaccess"]
_ADAPTOR_OPTIONS = []


# --------------------------------------------------------------------
# the adaptor capabilities & supported attributes
#
_ADAPTOR_CAPABILITIES = {
    "jdes_attributes": [saga.job.NAME,
                        saga.job.EXECUTABLE,
                        saga.job.ARGUMENTS,
                        saga.job.ENVIRONMENT,
                        saga.job.INPUT,
                        saga.job.OUTPUT,
                        saga.job.ERROR,
                        saga.job.QUEUE,
                        saga.job.PROJECT,
                        saga.job.WALL_TIME_LIMIT,
                        saga.job.WORKING_DIRECTORY,
                        saga.job.SPMD_VARIATION,  # TODO: 'hot'-fix for BigJob
                        saga.job.TOTAL_CPU_COUNT,
                        saga.job.THREADS_PER_PROCESS,
                        saga.job.PROCESSES_PER_HOST],
    "job_attributes": [saga.job.EXIT_CODE,
                       saga.job.EXECUTION_HOSTS,
                       saga.job.CREATED,
                       saga.job.STARTED,
                       saga.job.FINISHED],
    "metrics": [saga.job.STATE],
    "callbacks": [saga.job.STATE],
    "contexts": {"ssh": "SSH public/private keypair",
                 "x509": "GSISSH X509 proxy context",
                 "userpass": "username/password pair (ssh)"}
}

# --------------------------------------------------------------------
# the adaptor documentation
#
_ADAPTOR_DOC = {
    "name": _ADAPTOR_NAME,
    "cfg_options": _ADAPTOR_OPTIONS,
    "capabilities": _ADAPTOR_CAPABILITIES,
    "description": """
The ecaccess adaptor allows to run and manage jobs on ECMWF machines
""",
    "schemas": {"ecaccess": "connect using ecaccess tools"}
}

# --------------------------------------------------------------------
# the adaptor info is used to register the adaptor with SAGA
#
_ADAPTOR_INFO = {
    "name": _ADAPTOR_NAME,
    "version": "v0.1",
    "schemas": _ADAPTOR_SCHEMAS,
    "capabilities": _ADAPTOR_CAPABILITIES,
    "cpis": [
        {
            "type": "saga.job.Service",
            "class": "ECMWFJobService"
        },
        {
            "type": "saga.job.Job",
            "class": "ECMWFJob"
        }
    ]
}


###############################################################################
# The adaptor class
# noinspection PyMissingOrEmptyDocstring
class Adaptor(saga.adaptors.base.Base):
    """ this is the actual adaptor class, which gets loaded by SAGA (i.e. by
        the SAGA engine), and which registers the CPI implementation classes
        which provide the adaptor's functionality.
    """

    # ----------------------------------------------------------------
    #
    def __init__(self):
        # noinspection PyCallByClass,PyTypeChecker
        saga.adaptors.base.Base.__init__(self, _ADAPTOR_INFO, _ADAPTOR_OPTIONS)

        self.id_re = re.compile('^\[(.*)\]-\[(.*?)\]$')

    # ----------------------------------------------------------------
    #
    def sanity_check(self):
        # FIXME: also check for gsissh
        pass

    # ----------------------------------------------------------------
    #
    def parse_id(self, job_id):
        # split the id '[rm]-[pid]' in its parts, and return them.

        match = self.id_re.match(job_id)

        if not match or len(match.groups()) != 2:
            raise saga.BadParameter("Cannot parse job id '%s'" % job_id)

        return match.group(1), match.group(2)


###############################################################################
#
# noinspection PyMethodOverriding,PyMethodOverriding,PyProtectedMember,PyMissingOrEmptyDocstring
class ECMWFJobService(saga.adaptors.cpi.job.Service):
    """ implements saga.adaptors.cpi.job.Service
    """

    # ----------------------------------------------------------------
    #
    # noinspection PyMissingConstructor
    def __init__(self, api, adaptor):

        self._mt = None
        _cpi_base = super(ECMWFJobService, self)
        _cpi_base.__init__(api, adaptor)

        self._adaptor = adaptor
        self.host = None
        self.scheduler = None

    # ----------------------------------------------------------------
    #
    def __del__(self):

        self.close()

    # ----------------------------------------------------------------
    #
    def close(self):

        if self.mt:
            self.mt.stop()
            self.mt.join(10)  # don't block forever on join()

        self._logger.info("Job monitoring thread stopped.")

        self.finalize(True)

    # ----------------------------------------------------------------
    #
    def finalize(self, kill_shell=False):

        if kill_shell:
            if self.shell:
                self.shell.finalize(True)

    # ----------------------------------------------------------------
    #
    @SYNC_CALL
    def init_instance(self, adaptor_state, rm_url, session):
        """ service instance constructor
        :param session:
        :type session: saga.Session
        :param adaptor_state:
        :param rm_url:
        """
        self.rm = rm_url
        self.session = session
        self.ppn = 1
        self.queue = None
        self.shell = None
        self.jobs = dict()

        # the monitoring thread - one per service instance
        # noinspection PyTypeChecker
        self.mt = _job_state_monitor(job_service=self)
        self.mt.start()

        rm_scheme = rm_url.scheme
        pty_url = surl.Url(rm_url)

        # we need to extrac the scheme for PTYShell. That's basically the
        # job.Serivce Url withou the mn+ part. We use the PTYShell to execute
        # mn commands either locally or via gsissh or ssh.
        if rm_scheme == "ecaccess":
            pty_url.scheme = "fork"

        self.shell = saga.utils.pty_shell.PTYShell(pty_url, self.session)

        self.initialize()
        return self.get_api()

    # ----------------------------------------------------------------
    #
    def initialize(self):
        ret, out, _ = self.shell.run_sync("which ecaccess -version")
        if ret == 0:
            self._logger.info("Found ECMWF tools. Version: {0}".format(out))

    def _job_run(self, job_obj):
        """
        runs a job via ecaccess-job-submit
        """
        # get the job description
        jd = job_obj.jd

        # normalize working directory path
        if jd.working_directory:
            jd.working_directory = os.path.normpath(jd.working_directory)

        try:
            # create a loadleveler or PBS job script from SAGA job description
            if self.scheduler == 'loadleveler':
                header = self._generate_ll_header(jd)
            else:
                header = self._generate_pbs_header(jd)
            self._logger.info("Generated ECMWF header: %s" % header)
        except Exception as ex:
            header = ''
            log_error_and_raise(str(ex), saga.BadParameter, self._logger)

        local_file = os.path.join(BasicConfig.LOCAL_ROOT_DIR, jd.name.split('_')[0], BasicConfig.LOCAL_TMP_DIR,
                                  "{0}.cmd".format(str(jd.name)))
        f = open(local_file, 'r+')
        script = f.read()
        script = header + script
        f.seek(0)
        f.write(script)
        f.truncate()
        f.close()

        cmdline = "ecaccess-file-put {0} {1}:{2}".format(local_file, self.host, jd.executable)
        ret, out, _ = self.shell.run_sync(cmdline)
        if ret != 0:
            # something went wrong
            message = "Error sending file job via 'ecaccess-file-put': %s. Commandline was: %s" \
                      % (out, cmdline)
            log_error_and_raise(message, saga.NoSuccess, self._logger)

        cmdline = "ecaccess-job-submit -queueName {0} -jobName {1} -distant {0}:{2}".format(self.host,
                                                                                            jd.name, jd.executable)
        ret, out, _ = self.shell.run_sync(cmdline)
        if ret != 0:
            # something went wrong
            message = "Error submitting job via 'ecaccess-job-submit': %s. Commandline was: %s" \
                      % (out, cmdline)
            log_error_and_raise(message, saga.NoSuccess, self._logger)
        else:
            lines = out.split("\n")
            lines = filter(lambda l: l != '', lines)  # remove empty

            self._logger.info('ecaccess-job-submit: %s' % ''.join(lines))

            mn_job_id = lines[0]

            if not mn_job_id:
                raise Exception("Failed to detect job id after submission.")

            job_id = "[%s]-[%s]" % (self.rm, mn_job_id)

            self._logger.info("Submitted ECMWF job with id: %s" % job_id)

            # update job dictionary
            self.jobs[job_obj]['job_id'] = job_id
            self.jobs[job_obj]['submitted'] = job_id

            # set status to 'pending' and manually trigger callback
            # self.jobs[job_obj]['state'] = saga.job.PENDING
            # job_obj._api()._attributes_i_set('state', self.jobs[job_obj]['state'], job_obj._api()._UP, True)

            # return the job id
            return job_id

    @staticmethod
    def _generate_ll_header(jd):
        """
        generates a IMB LoadLeveler script from a SAGA job description
        :param jd: job descriptor
        :return: the llsubmit script
        """
        loadl_params = ''

        if jd.name is not None:
            loadl_params += "#@ job_name = %s \n" % jd.name

        if jd.environment is not None:
            variable_list = ''
            for key in jd.environment.keys():
                variable_list += "%s=%s;" % (key, jd.environment[key])
            loadl_params += "#@ environment = %s \n" % variable_list

        if jd.working_directory is not None:
            loadl_params += "#@ initialdir = %s\n" % jd.working_directory
        if jd.output is not None:
            loadl_params += "#@ output = %s\n" % os.path.join(jd.working_directory, jd.output)
        if jd.error is not None:
            loadl_params += "#@ error = %s\n" % os.path.join(jd.working_directory, jd.error)
        if jd.wall_time_limit is not None:
            hours = jd.wall_time_limit / 60
            minutes = jd.wall_time_limit % 60
            loadl_params += "#@ wall_clock_limit = {0:02}:{1:02}:00\n".format(hours, minutes)

        if jd.total_cpu_count is None:
            # try to come up with a sensible (?) default value
            jd.total_cpu_count = 1
        else:
            if jd.total_cpu_count > 1:
                loadl_params += "#@ total_tasks = %s\n" % jd.total_cpu_count

        if jd.job_contact is not None:
            if len(jd.job_contact) > 1:
                raise Exception("Only one notify user supported.")
            loadl_params += "#@ notify_user = %s\n" % jd.job_contact[0]
            loadl_params += "#@ notification = always\n"

        # some default (?) parameter that seem to work fine everywhere...
        if jd.queue is not None:
            loadl_params += "#@ class = %s\n" % jd.queue

        # finally, we 'queue' the job
        loadl_params += "#@ queue\n"

        loadlscript = "\n%s" % loadl_params

        return loadlscript.replace('"', '\\"')

    @staticmethod
    def _generate_pbs_header(jd):
        """ generates a PBS script from a SAGA job description
        """
        pbs_params = str()

        if jd.name:
            pbs_params += "#PBS -N %s \n" % jd.name

        # if jd.working_directory:
        #     pbs_params += "#PBS -d %s \n" % jd.working_directory
        #
        if jd.output:
            pbs_params += "#PBS -o %s \n" % os.path.join(jd.working_directory, jd.output)

        if jd.error:
            pbs_params += "#PBS -e %s \n" % os.path.join(jd.working_directory, jd.error)

        if jd.wall_time_limit:
            hours = jd.wall_time_limit / 60
            minutes = jd.wall_time_limit % 60
            pbs_params += "#PBS -l walltime={0:02}:{1:02}:00 \n".format(hours, minutes)

        if jd.queue:
            pbs_params += "#PBS -q %s \n" % jd.queue

        if jd.project:
            pbs_params += "#PBS -l EC_billing_account=%s \n" % str(jd.project)

        if jd.total_cpu_count:
            pbs_params += "#PBS -l EC_total_tasks=%s \n" % str(jd.total_cpu_count)
        if jd.threads_per_process:
            pbs_params += "#PBS -l EC_threads_per_task=%s \n" % str(jd.threads_per_process)
        if jd.processes_per_host:
            pbs_params += "#PBS -l EC_tasks_per_node=%s \n" % str(jd.processes_per_host)

        pbscript = pbs_params

        pbscript = pbscript.replace('"', '\\"')
        return pbscript

    # ----------------------------------------------------------------
    #
    def _retrieve_job(self, job_id):
        """ see if we can get some info about a job that we don't
            know anything about
        """
        rm, pid = self._adaptor.parse_id(job_id)

        ret, out, _ = self.shell.run_sync("ecaccess-job-list {0}".format(pid))

        if ret != 0:
            message = "Couldn't reconnect to job '%s': %s" % (job_id, out)
            log_error_and_raise(message, saga.NoSuccess, self._logger)

        else:
            # the job seems to exist on the backend. let's gather some data. Output will look like
            #      Job-Id: 7100070
            #   Job Name: SAGA-Python-LSFJobScript.j5u51g
            #      Queue: ecgate
            #       Host: ecgb.ecmwf.int
            #   Schedule: Aug 21 09:59
            # Expiration: Aug 28 09:59
            #  Try Count: 1/1
            #     Status: STOP
            #    Comment: Status STOP received from Slurm (exitCode: 127)

            job_info = {
                'state': saga.job.UNKNOWN,
                'exec_hosts': None,
                'returncode': None,
                'create_time': None,
                'start_time': None,
                'end_time': None,
                'gone': False
            }

            results = out.split('\n')
            job_info['state'] = _ecaccess_to_saga_jobstate(results[7].split(":")[1].strip())

            return job_info

    # ----------------------------------------------------------------
    #
    def _job_get_info(self, job_obj):
        """ get job attributes via bjob
        """

        # if we don't have the job in our dictionary, we don't want it
        if job_obj not in self.jobs:
            message = "Unknown job object: %s. Can't update state." % job_obj._id
            log_error_and_raise(message, saga.NoSuccess, self._logger)

        # prev. info contains the info collect when _job_get_info
        # was called the last time
        prev_info = self.jobs[job_obj]

        # if the 'gone' flag is set, there's no need to query the job
        # state again. it's gone forever
        if prev_info['gone'] is True:
            return prev_info

        # curr. info will contain the new job info collect. it starts off
        # as a copy of prev_info (don't use deepcopy because there is an API
        # object in the dict -> recursion)
        curr_info = dict()
        curr_info['job_id'] = prev_info.get('job_id')
        curr_info['state'] = prev_info.get('state')
        curr_info['exec_hosts'] = prev_info.get('exec_hosts')
        curr_info['returncode'] = prev_info.get('returncode')
        curr_info['create_time'] = prev_info.get('create_time')
        curr_info['start_time'] = prev_info.get('start_time')
        curr_info['end_time'] = prev_info.get('end_time')
        curr_info['gone'] = prev_info.get('gone')

        rm, pid = self._adaptor.parse_id(job_obj._id)

        # run the 'ecaccess-job-list' command to get some infos about our job
        # the result of ecaccess-job-list <id> looks like this:
        #
        # JOBID   USER    STAT  QUEUE      FROM_HOST   EXEC_HOST   JOB_NAME   SUBMIT_TIME
        # 901545  oweidne DONE  regular    yslogin5-ib ys3833-ib   *FILENAME  Nov 11 12:06
        #
        ret, out, _ = self.shell.run_sync('ecaccess-job-list {0}'.format(pid))

        if ret != 0:
            if "Illegal job ID" in out:
                # Let's see if the previous job state was running or pending. in
                # that case, the job is gone now, which can either mean DONE,
                # or FAILED. the only thing we can do is set it to 'DONE'
                curr_info['gone'] = True
                # we can also set the end time
                self._logger.warning("Previously running job has disappeared. This probably means that the backend " +
                                     "doesn't store informations about finished jobs. Setting state to 'DONE'.")

                if prev_info['state'] in [saga.job.RUNNING, saga.job.PENDING]:
                    curr_info['state'] = saga.job.DONE
                else:
                    curr_info['state'] = saga.job.FAILED
            else:
                # something went wrong
                message = "Error retrieving job info via 'ecaccess-job-list ': %s" % out
                log_error_and_raise(message, saga.NoSuccess, self._logger)
        else:
            # parse the result
            results = out.split()
            curr_info['state'] = _ecaccess_to_saga_jobstate(results[2])
            curr_info['exec_hosts'] = results[5]

        # return the new job info dict
        return curr_info

    # ----------------------------------------------------------------
    #
    def _job_get_state(self, job_obj):
        """ get the job's state
        """
        return self.jobs[job_obj]['state']

    # ----------------------------------------------------------------
    #
    def _job_get_exit_code(self, job_obj):
        """ get the job's exit code
        """
        ret = self.jobs[job_obj]['returncode']

        # FIXME: 'None' should cause an exception
        if ret is None:
            return None
        else:
            return int(ret)

    # ----------------------------------------------------------------
    #
    def _job_get_execution_hosts(self, job_obj):
        """ get the job's exit code
        """
        return self.jobs[job_obj]['exec_hosts']

    # ----------------------------------------------------------------
    #
    def _job_get_create_time(self, job_obj):
        """ get the job's creation time
        """
        return self.jobs[job_obj]['create_time']

    # ----------------------------------------------------------------
    #
    def _job_get_start_time(self, job_obj):
        """ get the job's start time
        """
        return self.jobs[job_obj]['start_time']

    # ----------------------------------------------------------------
    #
    def _job_get_end_time(self, job_obj):
        """ get the job's end time
        """
        return self.jobs[job_obj]['end_time']

    # ----------------------------------------------------------------
    #
    def _job_cancel(self, job_obj):
        """ cancel the job via 'qdel'
        """
        rm, pid = self._adaptor.parse_id(job_obj._id)

        ret, out, _ = self.shell.run_sync('ecaccess-job-delete {0}'.format(pid))

        if ret != 0:
            message = "Error canceling job via 'ecaccess-job-delete': %s" % out
            log_error_and_raise(message, saga.NoSuccess, self._logger)

        # assume the job was succesfully canceled
        self.jobs[job_obj]['state'] = saga.job.CANCELED

    # ----------------------------------------------------------------
    #
    def _job_wait(self, job_obj, timeout):
        """ wait for the job to finish or fail
        """
        time_start = time.time()
        self._adaptor.parse_id(job_obj._id)

        while True:
            state = self.jobs[job_obj]['state']  # this gets updated in the bg.

            if state == saga.job.DONE or state == saga.job.FAILED or state == saga.job.CANCELED:
                return True

            # avoid busy poll
            time.sleep(SYNC_WAIT_UPDATE_INTERVAL)

            # check if we hit timeout
            if timeout >= 0:
                time_now = time.time()
                if time_now - time_start > timeout:
                    return False

    # ----------------------------------------------------------------
    #
    @SYNC_CALL
    def create_job(self, jd):
        """
        implements saga.adaptors.cpi.job.Service.get_url()

        :param jd: job description
        """
        # this dict is passed on to the job adaptor class -- use it to pass any
        # state information you need there.
        adaptor_state = {"job_service": self,
                         "job_description": jd,
                         "job_schema": self.rm.schema,
                         "reconnect": False
                         }

        # create a new job object
        job_obj = saga.job.Job(_adaptor=self._adaptor,
                               _adaptor_state=adaptor_state)

        # add job to internal list of known jobs.
        self.jobs[job_obj._adaptor] = {
            'state': saga.job.NEW,
            'job_id': None,
            'exec_hosts': None,
            'returncode': None,
            'create_time': None,
            'start_time': None,
            'end_time': None,
            'gone': False,
            'submitted': False
        }

        return job_obj

    # ----------------------------------------------------------------
    #
    @SYNC_CALL
    def get_job(self, jobid):
        """
        Implements saga.adaptors.cpi.job.Service.get_job()

        :param jobid: job identifier
        :type jobid: str
        """

        # try to get some information about this job
        job_info = self._retrieve_job(jobid)

        # this dict is passed on to the job adaptor class -- use it to pass any
        # state information you need there.
        adaptor_state = {"job_service": self,
                         # TODO: fill job description
                         "job_description": saga.job.Description(),
                         "job_schema": self.rm.schema,
                         "reconnect": True,
                         "reconnect_jobid": jobid
                         }

        job = saga.job.Job(_adaptor=self._adaptor,
                           _adaptor_state=adaptor_state)

        # throw it into our job dictionary.
        self.jobs[job._adaptor] = job_info
        return job

    # ----------------------------------------------------------------
    #
    @SYNC_CALL
    def get_url(self):
        """ implements saga.adaptors.cpi.job.Service.get_url()
        """
        return self.rm

    # ----------------------------------------------------------------
    #
    @SYNC_CALL
    def list(self):
        """ implements saga.adaptors.cpi.job.Service.list()
        """
        ids = []

        ret, out, _ = self.shell.run_sync("ecaccess-job-list")

        if ret != 0 and len(out) > 0:
            message = "failed to list jobs via 'ecaccess-job-list   ': %s" % out
            log_error_and_raise(message, saga.NoSuccess, self._logger)
        elif ret != 0 and len(out) == 0:

            pass
        else:
            for line in out.split("\n"):
                # output looks like this:
                # 112059.svc.uc.futuregrid testjob oweidner 0 Q batch
                # 112061.svc.uc.futuregrid testjob oweidner 0 Q batch
                if len(line.split()) > 1:
                    jobid = "[%s]-[%s]" % (self.rm, line.split()[0].split('.')[0])
                    ids.append(str(jobid))

        return ids

        # # ----------------------------------------------------------------
        # #
        # def container_run (self, jobs) :
        #     self._logger.debug ("container run: %s"  %  str(jobs))
        #     # TODO: this is not optimized yet
        #     for job in jobs:
        #         job.run ()
        #
        #
        # # ----------------------------------------------------------------
        # #
        # def container_wait (self, jobs, mode, timeout) :
        #     self._logger.debug ("container wait: %s"  %  str(jobs))
        #     # TODO: this is not optimized yet
        #     for job in jobs:
        #         job.wait ()
        #
        #
        # # ----------------------------------------------------------------
        # #
        # def container_cancel (self, jobs) :
        #     self._logger.debug ("container cancel: %s"  %  str(jobs))
        #     raise saga.NoSuccess ("Not Implemented");


###############################################################################
#
# noinspection PyMethodOverriding,PyProtectedMember,PyMissingOrEmptyDocstring
class ECMWFJob(saga.adaptors.cpi.job.Job):
    """ implements saga.adaptors.cpi.job.Job
    """

    # noinspection PyMissingConstructor
    def __init__(self, api, adaptor):

        # initialize parent class
        _cpi_base = super(ECMWFJob, self)
        _cpi_base.__init__(api, adaptor)

    def _get_impl(self):
        return self

    @SYNC_CALL
    def init_instance(self, job_info):
        """
        implements saga.adaptors.cpi.job.Job.init_instance()

        :param job_info: job descriptiom
        :type job_info: dict
        """
        # init_instance is called for every new saga.job.Job object
        # that is created
        self.jd = job_info["job_description"]
        self.js = job_info["job_service"]

        if job_info['reconnect'] is True:
            self._id = job_info['reconnect_jobid']
            self._started = True
        else:
            self._id = None
            self._started = False

        return self.get_api()

    # ----------------------------------------------------------------
    #
    @SYNC_CALL
    def get_state(self):
        """ implements saga.adaptors.cpi.job.Job.get_state()
        """
        return self.js._job_get_state(job_obj=self)

    # ----------------------------------------------------------------
    #
    @SYNC_CALL
    def wait(self, timeout):
        """
        implements saga.adaptors.cpi.job.Job.wait()

        :param timeout: time to wait
        :type timeout: int
        """
        if self._started is False:
            log_error_and_raise("Can't wait for job that hasn't been started",
                                saga.IncorrectState, self._logger)
        else:
            self.js._job_wait(job_obj=self, timeout=timeout)

    # ----------------------------------------------------------------
    #
    @SYNC_CALL
    def cancel(self, timeout):
        """
        implements saga.adaptors.cpi.job.Job.cancel()

        :param timeout: time to wait
        :type timeout: int
        """
        if self._started is False:
            log_error_and_raise("Can't wait for job that hasn't been started",
                                saga.IncorrectState, self._logger)
        else:
            self.js._job_cancel(self)

    # ----------------------------------------------------------------
    #
    @SYNC_CALL
    def run(self):
        """ implements saga.adaptors.cpi.job.Job.run()
        """
        self._id = self.js._job_run(self)
        self._started = True

    # ----------------------------------------------------------------
    #
    @SYNC_CALL
    def get_service_url(self):
        """ implements saga.adaptors.cpi.job.Job.get_service_url()
        """
        return self.js.rm

    # ----------------------------------------------------------------
    #
    @SYNC_CALL
    def get_id(self):
        """ implements saga.adaptors.cpi.job.Job.get_id()
        """
        return self._id

    # ----------------------------------------------------------------
    #
    @SYNC_CALL
    def get_exit_code(self):
        """ implements saga.adaptors.cpi.job.Job.get_exit_code()
        """
        if self._started is False:
            return None
        else:
            return self.js._job_get_exit_code(self)

    # ----------------------------------------------------------------
    #
    @SYNC_CALL
    def get_created(self):
        """ implements saga.adaptors.cpi.job.Job.get_created()
        """
        if self._started is False:
            return None
        else:
            return self.js._job_get_create_time(self)

    # ----------------------------------------------------------------
    #
    @SYNC_CALL
    def get_started(self):
        """ implements saga.adaptors.cpi.job.Job.get_started()
        """
        if self._started is False:
            return None
        else:
            return self.js._job_get_start_time(self)

    # ----------------------------------------------------------------
    #
    @SYNC_CALL
    def get_finished(self):
        """ implements saga.adaptors.cpi.job.Job.get_finished()
        """
        if self._started is False:
            return None
        else:
            return self.js._job_get_end_time(self)

    # ----------------------------------------------------------------
    #
    @SYNC_CALL
    def get_execution_hosts(self):
        """ implements saga.adaptors.cpi.job.Job.get_execution_hosts()
        """
        if self._started is False:
            return None
        else:
            return self.js._job_get_execution_hosts(self)
