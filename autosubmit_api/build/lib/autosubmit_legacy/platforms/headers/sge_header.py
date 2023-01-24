#!/usr/bin/env python

# Copyright 2017 Earth Sciences Department, BSC-CNS

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

import textwrap


class SgeHeader(object):
    """Class to handle the Ithaca headers of a job"""

    # noinspection PyMethodMayBeStatic
    def get_queue_directive(self, job):
        """
        Returns queue directive for the specified job

        :param job: job to create queue directive for
        :type job: Job
        :return: queue directive
        :rtype: str
        """
        # There is no queue, so directive is empty
        if job.parameters['CURRENT_QUEUE'] == '':
            return ""
        else:
            return "$ -q {0}".format(job.parameters['CURRENT_QUEUE'])

    # noinspection PyMethodMayBeStatic,PyUnusedLocal
    def get_custom_directives(self, job):
        """
        Returns custom directives for the specified job

        :param job: job to create custom directive for
        :type job: Job
        :return: custom directives
        :rtype: str
        """
        # There is no custom directives, so directive is empty
        if job.parameters['CUSTOM_DIRECTIVES'] != '':
            return '\n'.join(str(s) for s in job.parameters['CUSTOM_DIRECTIVES'])
        return ""

    SERIAL = textwrap.dedent("""\
            ###############################################################################
            #                   %TASKTYPE% %EXPID% EXPERIMENT
            ###############################################################################
            #
            #$ -S /bin/sh
            #$ -N %JOBNAME%
            #$ -e %CURRENT_SCRATCH_DIR%/%CURRENT_PROJ%/%CURRENT_USER%/%EXPID%/LOG_%EXPID%/
            #$ -o %CURRENT_SCRATCH_DIR%/%CURRENT_PROJ%/%CURRENT_USER%/%EXPID%/LOG_%EXPID%/
            #$ -V
            #$ -l h_rt=%WALLCLOCK%:00
            #$ -l s_rt=%WALLCLOCK%:00
            #%QUEUE_DIRECTIVE%
            %CUSTOM_DIRECTIVES%
            #
            ###############################################################################
            """)

    PARALLEL = textwrap.dedent("""\
            ###############################################################################
            #                   %TASKTYPE% %EXPID% EXPERIMENT
            ###############################################################################
            #
            #$ -S /bin/sh
            #$ -N %JOBNAME%
            #$ -e %CURRENT_SCRATCH_DIR%/%CURRENT_PROJ%/%CURRENT_USER%/%EXPID%/LOG_%EXPID%/
            #$ -o %CURRENT_SCRATCH_DIR%/%CURRENT_PROJ%/%CURRENT_USER%/%EXPID%/LOG_%EXPID%/
            #$ -V
            #$ -l h_rt=%WALLCLOCK%:00
            #$ -l s_rt=%WALLCLOCK%:00
            #$ -pe orte %NUMPROC%
            #%QUEUE_DIRECTIVE%
            %CUSTOM_DIRECTIVES%
            #
            ###############################################################################
            """)
