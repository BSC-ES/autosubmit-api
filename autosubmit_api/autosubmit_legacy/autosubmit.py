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
# pipeline_test

from __future__ import print_function
import traceback
from pyparsing import nestedExpr
from collections import defaultdict
from distutils.util import strtobool
from pkg_resources import require, resource_listdir, resource_exists, resource_string
import portalocker
import datetime
import signal
import random
import re
import shutil
import sys
import pwd
import os
import copy
import time
import tarfile
import json
import subprocess
import argparse
import radical.saga as saga

sys.path.insert(0, os.path.abspath('.'))
from config.basicConfig import BasicConfig
from config.config_common import AutosubmitConfig
from bscearth.utils.config_parser import ConfigParserFactory
from job.job_common import Status
from git.autosubmit_git import AutosubmitGit
from job.job_list import JobList
from job.job_packages import JobPackageThread
from job.job_package_persistence import JobPackagePersistence
from job.job_list_persistence import JobListPersistenceDb
from job.job_list_persistence import JobListPersistencePkl
from job.job_grouping import JobGrouping
from bscearth.utils.log import Log
from database.db_common import create_db
from experiment.experiment_common import new_experiment
from experiment.experiment_common import copy_experiment
from database.db_common import delete_experiment
from database.db_common import get_autosubmit_version
from monitor.monitor import Monitor
from bscearth.utils.date import date2str
from notifications.mail_notifier import MailNotifier
from notifications.notifier import Notifier
from platforms.saga_submitter import SagaSubmitter
from platforms.paramiko_submitter import ParamikoSubmitter
from job.job_exceptions import WrongTemplateException
from job.job_packager import JobPackager
from sets import Set
from platforms.paramiko_platform import ParamikoTimeout
"""
Main module for autosubmit. Only contains an interface class to all functionality implemented on autosubmit
"""

try:
    # noinspection PyCompatibility
    from configparser import SafeConfigParser
except ImportError:
    # noinspection PyCompatibility
    from ConfigParser import SafeConfigParser

# It is Python dialog available? (optional dependency)
try:
    import dialog
except Exception:
    dialog = None


# noinspection PyPackageRequirements
# noinspection PyPackageRequirements
# noinspection PyPackageRequirements

# noinspection PyUnusedLocal


def signal_handler(signal_received, frame):
    """
    Used to handle interrupt signals, allowing autosubmit to clean before exit

    :param signal_received:
    :param frame:
    """
    Log.info('Autosubmit will interrupt at the next safe occasion')
    Autosubmit.exit = True


class Autosubmit:
    """
    Interface class for autosubmit.
    """
    sys.setrecursionlimit(500000)
    # Get the version number from the relevant file. If not, from autosubmit package
    scriptdir = os.path.abspath(os.path.dirname(__file__))

    if not os.path.exists(os.path.join(scriptdir, 'VERSION')):
        scriptdir = os.path.join(scriptdir, os.path.pardir)

    version_path = os.path.join(scriptdir, 'VERSION')
    readme_path = os.path.join(scriptdir, 'README')
    changes_path = os.path.join(scriptdir, 'CHANGELOG')
    if os.path.isfile(version_path):
        with open(version_path) as f:
            autosubmit_version = f.read().strip()
    else:
        autosubmit_version = require("autosubmitAPIwu")[0].version

    exit = False

    @staticmethod
    def parse_args():
        """
        Parse arguments given to an executable and start execution of command given
        """
        try:
            BasicConfig.read()

            parser = argparse.ArgumentParser(
                description='Main executable for autosubmit. ')
            parser.add_argument('-v', '--version', action='version', version=Autosubmit.autosubmit_version,
                                help="returns autosubmit's version number and exit")
            parser.add_argument('-lf', '--logfile', choices=('EVERYTHING', 'DEBUG', 'INFO', 'RESULT', 'USER_WARNING',
                                                             'WARNING', 'ERROR', 'CRITICAL', 'NO_LOG'),
                                default='DEBUG', type=str,
                                help="sets file's log level.")
            parser.add_argument('-lc', '--logconsole', choices=('EVERYTHING', 'DEBUG', 'INFO', 'RESULT', 'USER_WARNING',
                                                                'WARNING', 'ERROR', 'CRITICAL', 'NO_LOG'),
                                default='INFO', type=str,
                                help="sets console's log level")

            subparsers = parser.add_subparsers(dest='command')

            # Run
            subparser = subparsers.add_parser(
                'run', description="runs specified experiment")
            subparser.add_argument('expid', help='experiment identifier')
            subparser.add_argument('-nt', '--notransitive', action='store_true',
                                   default=False, help='Disable transitive reduction')

            # Expid
            subparser = subparsers.add_parser(
                'expid', description="Creates a new experiment")
            group = subparser.add_mutually_exclusive_group()
            group.add_argument(
                '-y', '--copy', help='makes a copy of the specified experiment')
            group.add_argument('-dm', '--dummy', action='store_true',
                               help='creates a new experiment with default values, usually for testing')
            group.add_argument('-op', '--operational', action='store_true',
                               help='creates a new experiment with operational experiment id')
            subparser.add_argument('-H', '--HPC', required=True,
                                   help='specifies the HPC to use for the experiment')
            subparser.add_argument('-d', '--description', type=str, required=True,
                                   help='sets a description for the experiment to store in the database.')

            # Delete
            subparser = subparsers.add_parser(
                'delete', description="delete specified experiment")
            subparser.add_argument('expid', help='experiment identifier')
            subparser.add_argument(
                '-f', '--force', action='store_true', help='deletes experiment without confirmation')

            # Monitor
            subparser = subparsers.add_parser(
                'monitor', description="plots specified experiment")
            subparser.add_argument('expid', help='experiment identifier')
            subparser.add_argument('-o', '--output', choices=('pdf', 'png', 'ps', 'svg'), default='pdf',
                                   help='chooses type of output for generated plot')
            subparser.add_argument('-group_by', choices=('date', 'member', 'chunk', 'split', 'automatic'), default=None,
                                   help='Groups the jobs automatically or by date, member, chunk or split')
            subparser.add_argument('-expand', type=str,
                                   help='Supply the list of dates/members/chunks to filter the list of jobs. Default = "Any". '
                                   'LIST = "[ 19601101 [ fc0 [1 2 3 4] fc1 [1] ] 19651101 [ fc0 [16-30] ] ]"')
            subparser.add_argument(
                '-expand_status', type=str, help='Select the statuses to be expanded')
            subparser.add_argument('--hide_groups', action='store_true',
                                   default=False, help='Hides the groups from the plot')
            subparser.add_argument('-cw', '--check_wrapper', action='store_true',
                                   default=False, help='Generate possible wrapper in the current workflow')

            group2 = subparser.add_mutually_exclusive_group(required=False)

            group.add_argument('-fs', '--filter_status', type=str,
                               choices=('Any', 'READY', 'COMPLETED',
                                        'WAITING', 'SUSPENDED', 'FAILED', 'UNKNOWN'),
                               help='Select the original status to filter the list of jobs')
            group = subparser.add_mutually_exclusive_group(required=False)
            group.add_argument('-fl', '--list', type=str,
                               help='Supply the list of job names to be filtered. Default = "Any". '
                                    'LIST = "b037_20101101_fc3_21_sim b037_20111101_fc4_26_sim"')
            group.add_argument('-fc', '--filter_chunks', type=str,
                               help='Supply the list of chunks to filter the list of jobs. Default = "Any". '
                                    'LIST = "[ 19601101 [ fc0 [1 2 3 4] fc1 [1] ] 19651101 [ fc0 [16-30] ] ]"')
            group.add_argument('-fs', '--filter_status', type=str,
                               choices=('Any', 'READY', 'COMPLETED',
                                        'WAITING', 'SUSPENDED', 'FAILED', 'UNKNOWN'),
                               help='Select the original status to filter the list of jobs')
            group.add_argument('-ft', '--filter_type', type=str,
                               help='Select the job type to filter the list of jobs')
            subparser.add_argument('--hide', action='store_true', default=False,
                                   help='hides plot window')
            group2.add_argument('--txt', action='store_true', default=False,
                                help='Generates only txt status file')

            group2.add_argument('-txtlog', '--txt_logfiles', action='store_true', default=False,
                                help='Generates only txt status file(AS < 3.12b behaviour)')

            subparser.add_argument('-nt', '--notransitive', action='store_true',
                                   default=False, help='Disable transitive reduction')

            # Stats
            subparser = subparsers.add_parser(
                'stats', description="plots statistics for specified experiment")
            subparser.add_argument('expid', help='experiment identifier')
            subparser.add_argument('-ft', '--filter_type', type=str, help='Select the job type to filter '
                                                                          'the list of jobs')
            subparser.add_argument('-fp', '--filter_period', type=int, help='Select the period to filter jobs '
                                                                            'from current time to the past '
                                                                            'in number of hours back')
            subparser.add_argument('-o', '--output', choices=('pdf', 'png', 'ps', 'svg'), default='pdf',
                                   help='type of output for generated plot')
            subparser.add_argument('--hide', action='store_true', default=False,
                                   help='hides plot window')
            subparser.add_argument('-nt', '--notransitive', action='store_true',
                                   default=False, help='Disable transitive reduction')

            # Clean
            subparser = subparsers.add_parser(
                'clean', description="clean specified experiment")
            subparser.add_argument('expid', help='experiment identifier')
            subparser.add_argument(
                '-pr', '--project', action="store_true", help='clean project')
            subparser.add_argument('-p', '--plot', action="store_true",
                                   help='clean plot, only 2 last will remain')
            subparser.add_argument('-s', '--stats', action="store_true",
                                   help='clean stats, only last will remain')

            # Recovery
            subparser = subparsers.add_parser(
                'recovery', description="recover specified experiment")
            subparser.add_argument(
                'expid', type=str, help='experiment identifier')
            subparser.add_argument(
                '-np', '--noplot', action='store_true', default=False, help='omit plot')
            subparser.add_argument('--all', action="store_true", default=False,
                                   help='Get completed files to synchronize pkl')
            subparser.add_argument(
                '-s', '--save', action="store_true", default=False, help='Save changes to disk')
            subparser.add_argument('--hide', action='store_true', default=False,
                                   help='hides plot window')
            subparser.add_argument('-group_by', choices=('date', 'member', 'chunk', 'split', 'automatic'), default=None,
                                   help='Groups the jobs automatically or by date, member, chunk or split')
            subparser.add_argument('-expand', type=str,
                                   help='Supply the list of dates/members/chunks to filter the list of jobs. Default = "Any". '
                                        'LIST = "[ 19601101 [ fc0 [1 2 3 4] fc1 [1] ] 19651101 [ fc0 [16-30] ] ]"')
            subparser.add_argument(
                '-expand_status', type=str, help='Select the statuses to be expanded')
            subparser.add_argument('-nt', '--notransitive', action='store_true',
                                   default=False, help='Disable transitive reduction')
            subparser.add_argument('-nl', '--no_recover_logs', action='store_true', default=False,
                                   help='Disable logs recovery')
            # Migrate
            subparser = subparsers.add_parser(
                'migrate', description="Migrate experiments from current user to another")
            subparser.add_argument('expid', help='experiment identifier')
            group = subparser.add_mutually_exclusive_group(required=True)
            group.add_argument('-o', '--offer', action="store_true",
                               default=False, help='Offer experiment')
            group.add_argument('-p', '--pickup', action="store_true",
                               default=False, help='Pick-up released experiment')

            # Inspect
            subparser = subparsers.add_parser(
                'inspect', description="Generate all .cmd files")
            subparser.add_argument('expid', help='experiment identifier')
            subparser.add_argument('-nt', '--notransitive', action='store_true',
                                   default=False, help='Disable transitive reduction')
            subparser.add_argument(
                '-f', '--force', action="store_true", help='Overwrite all cmd')
            subparser.add_argument('-cw', '--check_wrapper', action='store_true',
                                   default=False, help='Generate possible wrapper in the current workflow')

            group.add_argument('-fs', '--filter_status', type=str,
                               choices=('Any', 'READY', 'COMPLETED',
                                        'WAITING', 'SUSPENDED', 'FAILED', 'UNKNOWN'),
                               help='Select the original status to filter the list of jobs')
            group = subparser.add_mutually_exclusive_group(required=False)
            group.add_argument('-fl', '--list', type=str,
                               help='Supply the list of job names to be filtered. Default = "Any". '
                                    'LIST = "b037_20101101_fc3_21_sim b037_20111101_fc4_26_sim"')
            group.add_argument('-fc', '--filter_chunks', type=str,
                               help='Supply the list of chunks to filter the list of jobs. Default = "Any". '
                                    'LIST = "[ 19601101 [ fc0 [1 2 3 4] fc1 [1] ] 19651101 [ fc0 [16-30] ] ]"')
            group.add_argument('-fs', '--filter_status', type=str,
                               choices=('Any', 'READY', 'COMPLETED',
                                        'WAITING', 'SUSPENDED', 'FAILED', 'UNKNOWN'),
                               help='Select the original status to filter the list of jobs')
            group.add_argument('-ft', '--filter_type', type=str,
                               help='Select the job type to filter the list of jobs')

            # Check
            subparser = subparsers.add_parser(
                'check', description="check configuration for specified experiment")
            subparser.add_argument('expid', help='experiment identifier')
            subparser.add_argument('-nt', '--notransitive', action='store_true',
                                   default=False, help='Disable transitive reduction')
            # Describe
            subparser = subparsers.add_parser(
                'describe', description="Show details for specified experiment")
            subparser.add_argument('expid', help='experiment identifier')

            # Create
            subparser = subparsers.add_parser(
                'create', description="create specified experiment joblist")
            subparser.add_argument('expid', help='experiment identifier')
            subparser.add_argument(
                '-np', '--noplot', action='store_true', default=False, help='omit plot')
            subparser.add_argument('--hide', action='store_true', default=False,
                                   help='hides plot window')
            subparser.add_argument('-o', '--output', choices=('pdf', 'png', 'ps', 'svg'), default='pdf',
                                   help='chooses type of output for generated plot')
            subparser.add_argument('-group_by', choices=('date', 'member', 'chunk', 'split', 'automatic'), default=None,
                                   help='Groups the jobs automatically or by date, member, chunk or split')
            subparser.add_argument('-expand', type=str,
                                   help='Supply the list of dates/members/chunks to filter the list of jobs. Default = "Any". '
                                        'LIST = "[ 19601101 [ fc0 [1 2 3 4] fc1 [1] ] 19651101 [ fc0 [16-30] ] ]"')
            subparser.add_argument(
                '-expand_status', type=str, help='Select the statuses to be expanded')
            subparser.add_argument('-nt', '--notransitive', action='store_true',
                                   default=False, help='Disable transitive reduction')
            subparser.add_argument('-cw', '--check_wrapper', action='store_true',
                                   default=False, help='Generate possible wrapper in the current workflow')

            # Configure
            subparser = subparsers.add_parser('configure', description="configure database and path for autosubmit. It "
                                                                       "can be done at machine, user or local level."
                                                                       "If no arguments specified configure will "
                                                                       "display dialog boxes (if installed)")
            subparser.add_argument(
                '--advanced', action="store_true", help="Open advanced configuration of autosubmit")
            subparser.add_argument('-db', '--databasepath', default=None, help='path to database. If not supplied, '
                                                                               'it will prompt for it')
            subparser.add_argument(
                '-dbf', '--databasefilename', default=None, help='database filename')
            subparser.add_argument('-lr', '--localrootpath', default=None, help='path to store experiments. If not '
                                                                                'supplied, it will prompt for it')
            subparser.add_argument('-pc', '--platformsconfpath', default=None, help='path to platforms.conf file to '
                                                                                    'use by default. Optional')
            subparser.add_argument('-jc', '--jobsconfpath', default=None, help='path to jobs.conf file to use by '
                                                                               'default. Optional')
            subparser.add_argument(
                '-sm', '--smtphostname', default=None, help='STMP server hostname. Optional')
            subparser.add_argument(
                '-mf', '--mailfrom', default=None, help='Notifications sender address. Optional')
            group = subparser.add_mutually_exclusive_group()
            group.add_argument('--all', action="store_true",
                               help='configure for all users')
            group.add_argument('--local', action="store_true", help='configure only for using Autosubmit from this '
                                                                    'path')

            # Install
            subparsers.add_parser(
                'install', description='install database for autosubmit on the configured folder')

            # Set status
            subparser = subparsers.add_parser(
                'setstatus', description="sets job status for an experiment")
            subparser.add_argument('expid', help='experiment identifier')
            subparser.add_argument(
                '-np', '--noplot', action='store_true', default=False, help='omit plot')
            subparser.add_argument(
                '-s', '--save', action="store_true", default=False, help='Save changes to disk')

            subparser.add_argument('-t', '--status_final',
                                   choices=('READY', 'COMPLETED', 'WAITING', 'SUSPENDED', 'FAILED', 'UNKNOWN',
                                            'QUEUING', 'RUNNING'),
                                   required=True,
                                   help='Supply the target status')
            group = subparser.add_mutually_exclusive_group(required=True)
            group.add_argument('-fl', '--list', type=str,
                               help='Supply the list of job names to be changed. Default = "Any". '
                                    'LIST = "b037_20101101_fc3_21_sim b037_20111101_fc4_26_sim"')
            group.add_argument('-fc', '--filter_chunks', type=str,
                               help='Supply the list of chunks to change the status. Default = "Any". '
                                    'LIST = "[ 19601101 [ fc0 [1 2 3 4] fc1 [1] ] 19651101 [ fc0 [16-30] ] ]"')
            group.add_argument('-fs', '--filter_status', type=str,
                               help='Select the status (one or more) to filter the list of jobs.'
                                    "Valid values = ['Any', 'READY', 'COMPLETED', 'WAITING', 'SUSPENDED', 'FAILED', 'UNKNOWN']")
            group.add_argument('-ft', '--filter_type', type=str,
                               help='Select the job type to filter the list of jobs')

            subparser.add_argument('--hide', action='store_true', default=False,
                                   help='hides plot window')
            subparser.add_argument('-group_by', choices=('date', 'member', 'chunk', 'split', 'automatic'), default=None,
                                   help='Groups the jobs automatically or by date, member, chunk or split')
            subparser.add_argument('-expand', type=str,
                                   help='Supply the list of dates/members/chunks to filter the list of jobs. Default = "Any". '
                                        'LIST = "[ 19601101 [ fc0 [1 2 3 4] fc1 [1] ] 19651101 [ fc0 [16-30] ] ]"')
            subparser.add_argument(
                '-expand_status', type=str, help='Select the statuses to be expanded')
            subparser.add_argument('-nt', '--notransitive', action='store_true',
                                   default=False, help='Disable transitive reduction')
            subparser.add_argument('-cw', '--check_wrapper', action='store_true',
                                   default=False, help='Generate possible wrapper in the current workflow')

            # Test Case
            subparser = subparsers.add_parser(
                'testcase', description='create test case experiment')
            subparser.add_argument(
                '-y', '--copy', help='makes a copy of the specified experiment')
            subparser.add_argument(
                '-d', '--description', required=True, help='description of the test case')
            subparser.add_argument('-c', '--chunks', help='chunks to run')
            subparser.add_argument('-m', '--member', help='member to run')
            subparser.add_argument('-s', '--stardate', help='stardate to run')
            subparser.add_argument(
                '-H', '--HPC', required=True, help='HPC to run experiment on it')
            subparser.add_argument(
                '-b', '--branch', help='branch of git to run (or revision from subversion)')

            # Test
            subparser = subparsers.add_parser(
                'test', description='test experiment')
            subparser.add_argument('expid', help='experiment identifier')
            subparser.add_argument(
                '-c', '--chunks', required=True, help='chunks to run')
            subparser.add_argument('-m', '--member', help='member to run')
            subparser.add_argument('-s', '--stardate', help='stardate to run')
            subparser.add_argument(
                '-H', '--HPC', help='HPC to run experiment on it')
            subparser.add_argument(
                '-b', '--branch', help='branch of git to run (or revision from subversion)')

            # Refresh
            subparser = subparsers.add_parser(
                'refresh', description='refresh project directory for an experiment')
            subparser.add_argument('expid', help='experiment identifier')
            subparser.add_argument('-mc', '--model_conf', default=False, action='store_true',
                                   help='overwrite model conf file')
            subparser.add_argument('-jc', '--jobs_conf', default=False, action='store_true',
                                   help='overwrite jobs conf file')

            # Archive
            subparser = subparsers.add_parser(
                'archive', description='archives an experiment')
            subparser.add_argument('expid', help='experiment identifier')

            # Unarchive
            subparser = subparsers.add_parser(
                'unarchive', description='unarchives an experiment')
            subparser.add_argument('expid', help='experiment identifier')

            # Readme
            subparsers.add_parser('readme', description='show readme')

            # Changelog
            subparsers.add_parser('changelog', description='show changelog')

            args = parser.parse_args()

            Log.set_console_level(args.logconsole)
            Log.set_file_level(args.logfile)

            if args.command == 'run':
                return Autosubmit.run_experiment(args.expid, args.notransitive)
            elif args.command == 'expid':
                return Autosubmit.expid(args.HPC, args.description, args.copy, args.dummy, False,
                                        args.operational) != ''
            elif args.command == 'delete':
                return Autosubmit.delete(args.expid, args.force)
            elif args.command == 'monitor':
                return Autosubmit.monitor(args.expid, args.output, args.list, args.filter_chunks, args.filter_status,
                                          args.filter_type, args.hide, args.txt, args.group_by, args.expand,
                                          args.expand_status, args.hide_groups, args.notransitive, args.check_wrapper, args.txt_logfiles)
            elif args.command == 'stats':
                return Autosubmit.statistics(args.expid, args.filter_type, args.filter_period, args.output, args.hide,
                                             args.notransitive)
            elif args.command == 'clean':
                return Autosubmit.clean(args.expid, args.project, args.plot, args.stats)
            elif args.command == 'recovery':
                return Autosubmit.recovery(args.expid, args.noplot, args.save, args.all, args.hide, args.group_by,
                                           args.expand, args.expand_status, args.notransitive, args.no_recover_logs)
            elif args.command == 'check':
                return Autosubmit.check(args.expid, args.notransitive)
            elif args.command == 'inspect':
                return Autosubmit.inspect(args.expid, args.list, args.filter_chunks, args.filter_status,
                                          args.filter_type, args.notransitive, args.force, args.check_wrapper)
            elif args.command == 'describe':
                return Autosubmit.describe(args.expid)
            elif args.command == 'migrate':
                return Autosubmit.migrate(args.expid, args.offer, args.pickup)
            elif args.command == 'create':
                return Autosubmit.create(args.expid, args.noplot, args.hide, args.output, args.group_by, args.expand,
                                         args.expand_status, args.notransitive, args.check_wrapper)
            elif args.command == 'configure':
                if not args.advanced or (args.advanced and dialog is None):
                    return Autosubmit.configure(args.advanced, args.databasepath, args.databasefilename,
                                                args.localrootpath, args.platformsconfpath, args.jobsconfpath,
                                                args.smtphostname, args.mailfrom, args.all, args.local)
                else:
                    return Autosubmit.configure_dialog()
            elif args.command == 'install':
                return Autosubmit.install()
            elif args.command == 'setstatus':
                return Autosubmit.set_status(args.expid, args.noplot, args.save, args.status_final, args.list,
                                             args.filter_chunks, args.filter_status, args.filter_type, args.hide,
                                             args.group_by, args.expand, args.expand_status, args.notransitive, args.check_wrapper)
            elif args.command == 'testcase':
                return Autosubmit.testcase(args.copy, args.description, args.chunks, args.member, args.stardate,
                                           args.HPC, args.branch)
            elif args.command == 'test':
                return Autosubmit.test(args.expid, args.chunks, args.member, args.stardate, args.HPC, args.branch)
            elif args.command == 'refresh':
                return Autosubmit.refresh(args.expid, args.model_conf, args.jobs_conf)
            elif args.command == 'archive':
                return Autosubmit.archive(args.expid)
            elif args.command == 'unarchive':
                return Autosubmit.unarchive(args.expid)

            elif args.command == 'readme':
                if os.path.isfile(Autosubmit.readme_path):
                    with open(Autosubmit.readme_path) as f:
                        print(f.read())
                        return True
                return False
            elif args.command == 'changelog':
                if os.path.isfile(Autosubmit.changes_path):
                    with open(Autosubmit.changes_path) as f:
                        print(f.read())
                        return True
                return False
        except Exception as e:
            from traceback import format_exc
            Log.critical(
                'Unhandled exception on Autosubmit: {0}\n{1}', e, format_exc(10))

            return False

    @staticmethod
    def _delete_expid(expid_delete):
        """
        Removes an experiment from path and database

        :type expid_delete: str
        :param expid_delete: identifier of the experiment to delete
        """
        if expid_delete == '' or expid_delete is None and not os.path.exists(os.path.join(BasicConfig.LOCAL_ROOT_DIR,
                                                                                          expid_delete)):
            Log.info("Experiment directory does not exist.")
        else:
            Log.info("Removing experiment directory...")
            ret = False
            if pwd.getpwuid(os.stat(os.path.join(BasicConfig.LOCAL_ROOT_DIR, expid_delete)).st_uid).pw_name == os.getlogin():
                try:

                    shutil.rmtree(os.path.join(
                        BasicConfig.LOCAL_ROOT_DIR, expid_delete))
                except OSError as e:
                    Log.warning('Can not delete experiment folder: {0}', e)
                    return ret
                Log.info("Deleting experiment from database...")
                ret = delete_experiment(expid_delete)
                if ret:
                    Log.result("Experiment {0} deleted".format(expid_delete))
            else:
                Log.warning(
                    "Current User is not the Owner {0} can not be deleted!", expid_delete)
            return ret

    @staticmethod
    def expid(hpc, description, copy_id='', dummy=False, test=False, operational=False):
        """
        Creates a new experiment for given HPC

        :param operational: if true, creates an operational experiment
        :type operational: bool
        :type hpc: str
        :type description: str
        :type copy_id: str
        :type dummy: bool
        :param hpc: name of the main HPC for the experiment
        :param description: short experiment's description.
        :param copy_id: experiment identifier of experiment to copy
        :param dummy: if true, writes a default dummy configuration for testing
        :param test: if true, creates an experiment for testing
        :return: experiment identifier. If method fails, returns ''.
        :rtype: str
        """
        BasicConfig.read()

        log_path = os.path.join(
            BasicConfig.LOCAL_ROOT_DIR, 'ASlogs', 'expid.log'.format(os.getuid()))
        try:
            Log.set_file(log_path)
        except IOError as e:
            Log.error("Can not create log file in path {0}: {1}".format(
                log_path, e.message))
        exp_id = None
        if description is None:
            Log.error("Missing experiment description.")
            return ''
        if hpc is None:
            Log.error("Missing HPC.")
            return ''
        if not copy_id:
            exp_id = new_experiment(
                description, Autosubmit.autosubmit_version, test, operational)
            if exp_id == '':
                return ''
            try:
                os.mkdir(os.path.join(BasicConfig.LOCAL_ROOT_DIR, exp_id))

                os.mkdir(os.path.join(
                    BasicConfig.LOCAL_ROOT_DIR, exp_id, 'conf'))
                Log.info("Copying config files...")

                # autosubmit config and experiment copied from AS.
                files = resource_listdir('autosubmit.config', 'files')
                for filename in files:
                    if resource_exists('autosubmit.config', 'files/' + filename):
                        index = filename.index('.')
                        new_filename = filename[:index] + \
                            "_" + exp_id + filename[index:]

                        if filename == 'platforms.conf' and BasicConfig.DEFAULT_PLATFORMS_CONF != '':
                            content = open(os.path.join(
                                BasicConfig.DEFAULT_PLATFORMS_CONF, filename)).read()
                        elif filename == 'jobs.conf' and BasicConfig.DEFAULT_JOBS_CONF != '':
                            content = open(os.path.join(
                                BasicConfig.DEFAULT_JOBS_CONF, filename)).read()
                        else:
                            content = resource_string(
                                'autosubmit.config', 'files/' + filename)

                        conf_new_filename = os.path.join(
                            BasicConfig.LOCAL_ROOT_DIR, exp_id, "conf", new_filename)
                        Log.debug(conf_new_filename)
                        open(conf_new_filename, 'w').write(content)
                Autosubmit._prepare_conf_files(
                    exp_id, hpc, Autosubmit.autosubmit_version, dummy)
            except (OSError, IOError) as e:
                Log.error(
                    "Can not create experiment: {0}\nCleaning...".format(e))
                Autosubmit._delete_expid(exp_id)
                return ''
        else:
            try:
                if os.path.exists(os.path.join(BasicConfig.LOCAL_ROOT_DIR, copy_id)):
                    exp_id = copy_experiment(
                        copy_id, description, Autosubmit.autosubmit_version, test, operational)
                    if exp_id == '':
                        return ''
                    dir_exp_id = os.path.join(
                        BasicConfig.LOCAL_ROOT_DIR, exp_id)
                    os.mkdir(dir_exp_id)
                    os.mkdir(dir_exp_id + '/conf')
                    Log.info("Copying previous experiment config directories")
                    conf_copy_id = os.path.join(
                        BasicConfig.LOCAL_ROOT_DIR, copy_id, "conf")
                    files = os.listdir(conf_copy_id)
                    for filename in files:
                        if os.path.isfile(os.path.join(conf_copy_id, filename)):
                            new_filename = filename.replace(copy_id, exp_id)
                            content = open(os.path.join(
                                conf_copy_id, filename), 'r').read()
                            open(os.path.join(dir_exp_id, "conf",
                                              new_filename), 'w').write(content)
                    Autosubmit._prepare_conf_files(
                        exp_id, hpc, Autosubmit.autosubmit_version, dummy)
                    #####
                    autosubmit_config = AutosubmitConfig(
                        copy_id, BasicConfig, ConfigParserFactory())
                    if autosubmit_config.check_conf_files():
                        project_type = autosubmit_config.get_project_type()
                        if project_type == "git":
                            autosubmit_config.check_proj()
                            autosubmit_git = AutosubmitGit(copy_id[0])
                            Log.info("checking model version...")
                            if not autosubmit_git.check_commit(autosubmit_config):
                                return False
                        #####
                else:
                    Log.critical(
                        "The previous experiment directory does not exist")
                    return ''
            except (OSError, IOError) as e:
                Log.error(
                    "Can not create experiment: {0}\nCleaning...".format(e))
                Autosubmit._delete_expid(exp_id)
                return ''

        Log.debug("Creating temporal directory...")
        exp_id_path = os.path.join(BasicConfig.LOCAL_ROOT_DIR, exp_id)
        tmp_path = os.path.join(exp_id_path, "tmp")
        os.mkdir(tmp_path)
        os.chmod(tmp_path, 0o775)
        os.mkdir(os.path.join(tmp_path, BasicConfig.LOCAL_ASLOG_DIR))
        os.chmod(os.path.join(tmp_path, BasicConfig.LOCAL_ASLOG_DIR), 0o775)
        Log.debug("Creating temporal remote directory...")
        remote_tmp_path = os.path.join(tmp_path, "LOG_" + exp_id)
        os.mkdir(remote_tmp_path)
        os.chmod(remote_tmp_path, 0o775)

        Log.debug("Creating pkl directory...")
        os.mkdir(os.path.join(exp_id_path, "pkl"))

        Log.debug("Creating plot directory...")
        os.mkdir(os.path.join(exp_id_path, "plot"))
        os.chmod(os.path.join(exp_id_path, "plot"), 0o775)
        Log.result("Experiment registered successfully")
        Log.user_warning("Remember to MODIFY the config files!")
        return exp_id

    @staticmethod
    def delete(expid, force):
        """
        Deletes and experiment from database and experiment's folder

        :type force: bool
        :type expid: str
        :param expid: identifier of the experiment to delete
        :param force: if True, does not ask for confirmation

        :returns: True if succesful, False if not
        :rtype: bool
        """
        log_path = os.path.join(
            BasicConfig.LOCAL_ROOT_DIR, "ASlogs", 'delete.log'.format(os.getuid()))
        try:
            Log.set_file(log_path)
        except IOError as e:
            Log.error("Can not create log file in path {0}: {1}".format(
                log_path, e.message))

        if os.path.exists(os.path.join(BasicConfig.LOCAL_ROOT_DIR, expid)):
            if force or Autosubmit._user_yes_no_query("Do you want to delete " + expid + " ?"):
                return Autosubmit._delete_expid(expid)
            else:
                Log.info("Quitting...")
                return False
        else:
            Log.error("The experiment does not exist")
            return True

    @staticmethod
    def _load_parameters(as_conf, job_list, platforms):
        # Load parameters
        Log.debug("Loading parameters...")
        parameters = as_conf.load_parameters()
        for platform_name in platforms:
            platform = platforms[platform_name]
            platform.add_parameters(parameters)

        platform = platforms[as_conf.get_platform().lower()]
        platform.add_parameters(parameters, True)

        job_list.parameters = parameters

    @staticmethod
    def inspect(expid, lst, filter_chunks, filter_status, filter_section, notransitive=False, force=False, check_wrapper=False):
        """
         Generates cmd files experiment.

         :type expid: str
         :param expid: identifier of experiment to be run
         :return: True if run to the end, False otherwise
         :rtype: bool
         """

        if expid is None:
            Log.critical("Missing experiment id")

        BasicConfig.read()
        exp_path = os.path.join(BasicConfig.LOCAL_ROOT_DIR, expid)
        tmp_path = os.path.join(exp_path, BasicConfig.LOCAL_TMP_DIR)
        if os.path.exists(os.path.join(tmp_path, 'autosubmit.lock')):
            locked = True
        else:
            locked = False

        if not os.path.exists(exp_path):
            Log.critical(
                "The directory %s is needed and does not exist" % exp_path)
            Log.warning("Does an experiment with the given id exist?")
            return 1
        Log.info("Starting inspect command")
        Log.set_file(os.path.join(
            tmp_path, BasicConfig.LOCAL_ASLOG_DIR, 'generate.log'))
        os.system('clear')
        signal.signal(signal.SIGINT, signal_handler)
        as_conf = AutosubmitConfig(expid, BasicConfig, ConfigParserFactory())
        if not as_conf.check_conf_files():
            Log.critical('Can not generate scripts with invalid configuration')
            return False
        project_type = as_conf.get_project_type()
        if project_type != "none":
            # Check proj configuration
            as_conf.check_proj()
        safetysleeptime = as_conf.get_safetysleeptime()
        Log.debug("The Experiment name is: {0}", expid)
        Log.debug("Sleep: {0}", safetysleeptime)
        packages_persistence = JobPackagePersistence(os.path.join(BasicConfig.LOCAL_ROOT_DIR, expid, "pkl"),
                                                     "job_packages_" + expid)
        os.chmod(os.path.join(BasicConfig.LOCAL_ROOT_DIR, expid,
                              "pkl", "job_packages_" + expid + ".db"), 0664)

        packages_persistence.reset_table(True)
        job_list_original = Autosubmit.load_job_list(
            expid, as_conf, notransitive=notransitive)
        job_list = copy.deepcopy(job_list_original)
        job_list.packages_dict = {}

        Log.debug("Length of the jobs list: {0}", len(job_list))

        # variables to be updated on the fly
        safetysleeptime = as_conf.get_safetysleeptime()
        Log.debug("Sleep: {0}", safetysleeptime)
        # Generate
        Log.info("Starting to generate cmd scripts")

        if not isinstance(job_list, type([])):
            jobs = []
            jobs_cw = []
            if check_wrapper and (not locked or (force and locked)):
                Log.info("Generating all cmd script adapted for wrappers")
                jobs = job_list.get_uncompleted()

                jobs_cw = job_list.get_completed()
            else:
                if (force and not locked) or (force and locked):
                    Log.info("Overwritting all cmd scripts")
                    jobs = job_list.get_job_list()
                elif locked:
                    Log.warning(
                        "There is a .lock file and not -f, generating only all unsubmitted cmd scripts")
                    jobs = job_list.get_unsubmitted()
                else:
                    Log.info("Generating cmd scripts only for selected jobs")
                    if filter_chunks:
                        fc = filter_chunks
                        Log.debug(fc)
                        if fc == 'Any':
                            jobs = job_list.get_job_list()
                        else:
                            # noinspection PyTypeChecker
                            data = json.loads(Autosubmit._create_json(fc))
                            for date_json in data['sds']:
                                date = date_json['sd']
                                jobs_date = filter(lambda j: date2str(
                                    j.date) == date, job_list.get_job_list())

                                for member_json in date_json['ms']:
                                    member = member_json['m']
                                    jobs_member = filter(
                                        lambda j: j.member == member, jobs_date)

                                    for chunk_json in member_json['cs']:
                                        chunk = int(chunk_json)
                                        jobs = jobs + \
                                            [job for job in filter(
                                                lambda j: j.chunk == chunk, jobs_member)]

                    elif filter_status:
                        Log.debug(
                            "Filtering jobs with status {0}", filter_status)
                        if filter_status == 'Any':
                            jobs = job_list.get_job_list()
                        else:
                            fs = Autosubmit._get_status(filter_status)
                            jobs = [job for job in filter(
                                lambda j: j.status == fs, job_list.get_job_list())]

                    elif filter_section:
                        ft = filter_section
                        Log.debug(ft)

                        if ft == 'Any':
                            jobs = job_list.get_job_list()
                        else:
                            for job in job_list.get_job_list():
                                if job.section == ft:
                                    jobs.append(job)
                    elif lst:
                        jobs_lst = lst.split()

                        if jobs == 'Any':
                            jobs = job_list.get_job_list()
                        else:
                            for job in job_list.get_job_list():
                                if job.name in jobs_lst:
                                    jobs.append(job)
                    else:
                        jobs = job_list.get_job_list()
        if isinstance(jobs, type([])):
            referenced_jobs_to_remove = set()
            for job in jobs:
                for child in job.children:
                    if child not in jobs:
                        referenced_jobs_to_remove.add(child)
                for parent in job.parents:
                    if parent not in jobs:
                        referenced_jobs_to_remove.add(parent)

            for job in jobs:
                job.status = Status.WAITING

            Autosubmit.generate_scripts_andor_wrappers(
                as_conf, job_list, jobs, packages_persistence, False)
        if len(jobs_cw) > 0:
            referenced_jobs_to_remove = set()
            for job in jobs_cw:
                for child in job.children:
                    if child not in jobs_cw:
                        referenced_jobs_to_remove.add(child)
                for parent in job.parents:
                    if parent not in jobs_cw:
                        referenced_jobs_to_remove.add(parent)

            for job in jobs_cw:
                job.status = Status.WAITING
            Autosubmit.generate_scripts_andor_wrappers(
                as_conf, job_list, jobs_cw, packages_persistence, False)

        Log.info("no more scripts to generate, now proceed to check them manually")
        time.sleep(safetysleeptime)
        return True

    @staticmethod
    def generate_scripts_andor_wrappers(as_conf, job_list, jobs_filtered, packages_persistence, only_wrappers=False):
        """
        as_conf: AutosubmitConfig object
        job_list: JobList object, contains a list of jobs
        jobs_filtered: list of jobs
        packages_persistence: Database handler
        only_wrappers: True
        """
        job_list._job_list = jobs_filtered
        job_list.update_list(as_conf, False)
        # Identifying the submitter and loading it
        submitter = Autosubmit._get_submitter(as_conf)
        # Function depending on the submitter
        submitter.load_platforms(as_conf)
        # Identifying HPC from config files
        hpcarch = as_conf.get_platform()
        #
        Autosubmit._load_parameters(as_conf, job_list, submitter.platforms)
        platforms_to_test = set()
        for job in job_list.get_job_list():
            if job.platform_name is None:
                job.platform_name = hpcarch
            # noinspection PyTypeChecker
            job.platform = submitter.platforms[job.platform_name.lower()]
            # noinspection PyTypeChecker
            platforms_to_test.add(job.platform)
        # case setstatus
        job_list.check_scripts(as_conf)
        job_list.update_list(as_conf, False)
        Autosubmit._load_parameters(as_conf, job_list, submitter.platforms)
        while job_list.get_active():
            Autosubmit.submit_ready_jobs(
                as_conf, job_list, platforms_to_test, packages_persistence, True, only_wrappers)

            job_list.update_list(as_conf, False)

    @staticmethod
    def run_experiment(expid, notransitive=False):
        """
        Runs and experiment (submitting all the jobs properly and repeating its execution in case of failure).

        :type expid: str
        :param expid: identifier of experiment to be run
        :return: True if run to the end, False otherwise
        :rtype: bool
        """
        if expid is None:
            Log.critical("Missing experiment id")

        BasicConfig.read()
        exp_path = os.path.join(BasicConfig.LOCAL_ROOT_DIR, expid)
        tmp_path = os.path.join(exp_path, BasicConfig.LOCAL_TMP_DIR)
        aslogs_path = os.path.join(tmp_path, BasicConfig.LOCAL_ASLOG_DIR)
        if not os.path.exists(aslogs_path):
            os.mkdir(aslogs_path)
            os.chmod(aslogs_path, 0o775)
        if not os.path.exists(exp_path):
            Log.critical(
                "The directory %s is needed and does not exist" % exp_path)
            Log.warning("Does an experiment with the given id exist?")
            return 1

        # checking host whitelist
        import platform
        host = platform.node()
        print(host)
        if BasicConfig.ALLOWED_HOSTS and host not in BasicConfig.ALLOWED_HOSTS:
            Log.info("\n Autosubmit run command is not allowed on this host")
            return False

        # checking if there is a lock file to avoid multiple running on the same expid
        try:
            with portalocker.Lock(os.path.join(tmp_path, 'autosubmit.lock'), timeout=1):
                Log.info(
                    "Preparing .lock file to avoid multiple instances with same experiment id")

                Log.set_file(os.path.join(aslogs_path, 'run.log'))
                os.system('clear')

                signal.signal(signal.SIGINT, signal_handler)

                as_conf = AutosubmitConfig(
                    expid, BasicConfig, ConfigParserFactory())
                if not as_conf.check_conf_files():
                    Log.critical('Can not run with invalid configuration')
                    return False

                project_type = as_conf.get_project_type()
                if project_type != "none":
                    # Check proj configuration
                    as_conf.check_proj()

                hpcarch = as_conf.get_platform()

                safetysleeptime = as_conf.get_safetysleeptime()
                retrials = as_conf.get_retrials()

                submitter = Autosubmit._get_submitter(as_conf)
                submitter.load_platforms(as_conf)

                Log.debug("The Experiment name is: {0}", expid)
                Log.debug("Sleep: {0}", safetysleeptime)
                Log.debug("Default retrials: {0}", retrials)

                Log.info("Starting job submission...")

                pkl_dir = os.path.join(
                    BasicConfig.LOCAL_ROOT_DIR, expid, 'pkl')
                job_list = Autosubmit.load_job_list(
                    expid, as_conf, notransitive=notransitive)

                Log.debug(
                    "Starting from job list restored from {0} files", pkl_dir)

                Log.debug("Length of the jobs list: {0}", len(job_list))

                Autosubmit._load_parameters(
                    as_conf, job_list, submitter.platforms)

                # check the job list script creation
                Log.debug("Checking experiment templates...")

                platforms_to_test = set()
                for job in job_list.get_job_list():
                    if job.platform_name is None:
                        job.platform_name = hpcarch
                    # noinspection PyTypeChecker
                    job.platform = submitter.platforms[job.platform_name.lower(
                    )]
                    # noinspection PyTypeChecker
                    platforms_to_test.add(job.platform)

                job_list.check_scripts(as_conf)

                packages_persistence = JobPackagePersistence(os.path.join(BasicConfig.LOCAL_ROOT_DIR, expid, "pkl"),
                                                             "job_packages_" + expid)

                if as_conf.get_wrapper_type() != 'none':
                    os.chmod(os.path.join(BasicConfig.LOCAL_ROOT_DIR,
                                          expid, "pkl", "job_packages_" + expid + ".db"), 0664)
                    packages = packages_persistence.load()
                    for (exp_id, package_name, job_name) in packages:
                        if package_name not in job_list.packages_dict:
                            job_list.packages_dict[package_name] = []
                        job_list.packages_dict[package_name].append(
                            job_list.get_job_by_name(job_name))

                    for package_name, jobs in job_list.packages_dict.items():
                        from job.job import WrapperJob
                        wrapper_job = WrapperJob(package_name, jobs[0].id, Status.SUBMITTED, 0, jobs,
                                                 None,
                                                 None, jobs[0].platform, as_conf)
                        job_list.job_package_map[jobs[0].id] = wrapper_job
                job_list.update_list(as_conf)
                job_list.save()
                #########################
                # AUTOSUBMIT - MAIN LOOP
                #########################
                # Main loop. Finishing when all jobs have been submitted
                while job_list.get_active():
                    if Autosubmit.exit:
                        return 2
                    # reload parameters changes
                    Log.debug("Reloading parameters...")
                    as_conf.reload()
                    Autosubmit._load_parameters(
                        as_conf, job_list, submitter.platforms)
                    # variables to be updated on the fly
                    total_jobs = len(job_list.get_job_list())
                    Log.info(
                        "\n\n{0} of {1} jobs remaining ({2})".format(total_jobs - len(job_list.get_completed()),
                                                                     total_jobs,
                                                                     time.strftime("%H:%M")))
                    safetysleeptime = as_conf.get_safetysleeptime()
                    Log.debug("Sleep: {0}", safetysleeptime)
                    default_retrials = as_conf.get_retrials()
                    Log.debug("Number of retrials: {0}", default_retrials)

                    check_wrapper_jobs_sleeptime = as_conf.get_wrapper_check_time()
                    Log.debug('WRAPPER CHECK TIME = {0}'.format(
                        check_wrapper_jobs_sleeptime))

                    save = False

                    slurm = []
                    for platform in platforms_to_test:
                        list_jobid = ""
                        completed_joblist = []
                        list_prevStatus = []
                        queuing_jobs = job_list.get_in_queue_grouped_id(
                            platform)
                        for job_id, job in queuing_jobs.items():
                            if job_list.job_package_map and job_id in job_list.job_package_map:
                                Log.debug(
                                    'Checking wrapper job with id ' + str(job_id))
                                wrapper_job = job_list.job_package_map[job_id]
                                check_wrapper = True
                                if wrapper_job.status == Status.RUNNING:
                                    check_wrapper = True if datetime.timedelta.total_seconds(datetime.datetime.now(
                                    ) - wrapper_job.checked_time) >= check_wrapper_jobs_sleeptime else False
                                if check_wrapper:
                                    wrapper_job.checked_time = datetime.datetime.now()
                                    platform.check_job(wrapper_job)
                                    Log.info(
                                        'Wrapper job ' + wrapper_job.name + ' is ' + str(Status.VALUE_TO_KEY[wrapper_job.new_status]))
                                    wrapper_job.check_status(
                                        wrapper_job.new_status)
                                    save = True
                                else:
                                    Log.info(
                                        "Waiting for wrapper check time: {0}\n", check_wrapper_jobs_sleeptime)
                            else:
                                job = job[0]
                                prev_status = job.status
                                if job.status == Status.FAILED:
                                    continue

                                if platform.type == "slurm":
                                    list_jobid += str(job_id) + ','
                                    list_prevStatus.append(prev_status)
                                    completed_joblist.append(job)
                                else:
                                    platform.check_job(job)
                                    if prev_status != job.update_status(as_conf.get_copy_remote_logs() == 'true'):
                                        if as_conf.get_notifications() == 'true':
                                            if Status.VALUE_TO_KEY[job.status] in job.notify_on:
                                                Notifier.notify_status_change(MailNotifier(BasicConfig), expid, job.name,
                                                                              Status.VALUE_TO_KEY[prev_status],
                                                                              Status.VALUE_TO_KEY[job.status],
                                                                              as_conf.get_mails_to())
                                    save = True

                        if platform.type == "slurm" and list_jobid != "":
                            slurm.append(
                                [platform, list_jobid, list_prevStatus, completed_joblist])
                    # END LOOP
                    for platform_jobs in slurm:
                        platform = platform_jobs[0]
                        jobs_to_check = platform_jobs[1]
                        platform.check_Alljobs(
                            platform_jobs[3], jobs_to_check, as_conf.get_copy_remote_logs())

                        for j_Indx in xrange(0, len(platform_jobs[3])):
                            prev_status = platform_jobs[2][j_Indx]
                            job = platform_jobs[3][j_Indx]

                            if prev_status != job.update_status(as_conf.get_copy_remote_logs() == 'true'):
                                if as_conf.get_notifications() == 'true':
                                    if Status.VALUE_TO_KEY[job.status] in job.notify_on:
                                        Notifier.notify_status_change(MailNotifier(BasicConfig), expid, job.name,
                                                                      Status.VALUE_TO_KEY[prev_status],
                                                                      Status.VALUE_TO_KEY[job.status],
                                                                      as_conf.get_mails_to())
                            save = True

                    if job_list.update_list(as_conf) or save:
                        job_list.save()

                    if Autosubmit.submit_ready_jobs(as_conf, job_list, platforms_to_test, packages_persistence):
                        job_list.save()

                    if Autosubmit.exit:
                        return 2
                    time.sleep(safetysleeptime)

                Log.info("No more jobs to run.")
                if len(job_list.get_failed()) > 0:
                    Log.info("Some jobs have failed and reached maximum retrials")
                    return False
                else:
                    Log.result("Run successful")
                    return True

        except portalocker.AlreadyLocked:
            Autosubmit.show_lock_warning(expid)

        except WrongTemplateException:
            return False

    @staticmethod
    def submit_ready_jobs(as_conf, job_list, platforms_to_test, packages_persistence, inspect=False,
                          only_wrappers=False):
        """
        Gets READY jobs and send them to the platforms if there is available space on the queues

        :param as_conf: autosubmit config object. \n
        :type as_conf: AutosubmitConfig Object. \n
        :param job_list: JobList as a single entity. \n
        :type job_list: JobList() Object. \n
        :param platforms_to_test: List of platforms that will be used in the experiment. \n
        :type platforms_to_test: Set() of Platform() Object. e.g. EcPlatform(), LsfPlatform(), etc. \n
        :return: True if at least one job was submitted, False otherwise
        :rtype: bool
        """
        save = False

        for platform in platforms_to_test:
            Log.debug("\nJobs ready for {1}: {0}", len(
                job_list.get_ready(platform)), platform.name)
            packages_to_submit, remote_dependencies_dict = JobPackager(
                as_conf, platform, job_list).build_packages()
            if not inspect:
                platform.open_submit_script()
            valid_packages_to_submit = []
            for package in packages_to_submit:
                try:
                    if hasattr(package, "name"):
                        if remote_dependencies_dict and package.name in remote_dependencies_dict['dependencies']:
                            remote_dependency = remote_dependencies_dict['dependencies'][package.name]
                            remote_dependency_id = remote_dependencies_dict['name_to_id'][remote_dependency]
                            package.set_job_dependency(remote_dependency_id)
                    if not only_wrappers:
                        try:
                            package.submit(
                                as_conf, job_list.parameters, inspect)
                            valid_packages_to_submit.append(package)
                        except (IOError, OSError):
                            # write error file
                            continue
                    if only_wrappers or inspect:
                        for innerJob in package._jobs:
                            innerJob.status = Status.COMPLETED

                        if hasattr(package, "name"):
                            job_list.packages_dict[package.name] = package.jobs
                            from job.job import WrapperJob
                            wrapper_job = WrapperJob(package.name, package.jobs[0].id, Status.READY, 0,
                                                     package.jobs,
                                                     package._wallclock, package._num_processors,
                                                     package.platform, as_conf)
                            job_list.job_package_map[package.jobs[0].id] = wrapper_job
                            if remote_dependencies_dict and package.name in remote_dependencies_dict['name_to_id']:
                                remote_dependencies_dict['name_to_id'][package.name] = package.jobs[0].id
                        if isinstance(package, JobPackageThread):
                            packages_persistence.save(
                                package.name, package.jobs, package._expid, inspect)
                        save = True
                except WrongTemplateException as e:
                    Log.error(
                        "Invalid parameter substitution in {0} template", e.job_name)
                    raise
                except Exception:
                    Log.error(
                        "{0} submission failed due to Unknown error", platform.name)
                    raise

            if platform.type == "slurm" and not inspect and not only_wrappers:
                try:
                    save = True
                    if len(valid_packages_to_submit) > 0:
                        jobs_id = platform.submit_Script()
                        if jobs_id is None:
                            raise BaseException(
                                "Exiting AS being unable to get jobID")
                        i = 0
                        for package in valid_packages_to_submit:
                            for job in package.jobs:
                                job.id = str(jobs_id[i])
                                Log.info("{0} submitted", job.name)
                                job.status = Status.SUBMITTED
                                job.write_submit_time()
                            if hasattr(package, "name"):
                                job_list.packages_dict[package.name] = package.jobs
                                from job.job import WrapperJob
                                wrapper_job = WrapperJob(package.name, package.jobs[0].id, Status.SUBMITTED, 0,
                                                         package.jobs,
                                                         package._wallclock, package._num_processors,
                                                         package.platform, as_conf)
                                job_list.job_package_map[package.jobs[0].id] = wrapper_job
                                if remote_dependencies_dict and package.name in remote_dependencies_dict[
                                        'name_to_id']:
                                    remote_dependencies_dict['name_to_id'][package.name] = package.jobs[0].id
                                if isinstance(package, JobPackageThread):
                                    packages_persistence.save(
                                        package.name, package.jobs, package._expid, inspect)
                            i += 1

                except WrongTemplateException as e:
                    Log.error(
                        "Invalid parameter substitution in {0} template", e.job_name)
                    raise
                except Exception:
                    Log.error("{0} submission failed", platform.name)
                    raise

        return save

    @staticmethod
    def monitor(expid, file_format, lst, filter_chunks, filter_status, filter_section, hide, txt_only=False,
                group_by=None, expand=list(), expand_status=list(), hide_groups=False, notransitive=False, check_wrapper=False, txt_logfiles=False):
        """
        Plots workflow graph for a given experiment with status of each job coded by node color.
        Plot is created in experiment's plot folder with name <expid>_<date>_<time>.<file_format>

        :type file_format: str
        :type expid: str
        :param expid: identifier of the experiment to plot
        :param file_format: plot's file format. It can be pdf, png, ps or svg
        :param lst: list of jobs to change status
        :type lst: str
        :param filter_chunks: chunks to change status
        :type filter_chunks: str
        :param filter_status: current status of the jobs to change status
        :type filter_status: str
        :param filter_section: sections to change status
        :type filter_section: str
        :param hide: hides plot window
        :type hide: bool
        """
        BasicConfig.read()

        exp_path = os.path.join(BasicConfig.LOCAL_ROOT_DIR, expid)

        if not os.path.exists(exp_path):
            Log.critical(
                "The directory %s is needed and does not exist." % exp_path)
            Log.warning("Does an experiment with the given id exist?")
            return 1

        Log.set_file(os.path.join(BasicConfig.LOCAL_ROOT_DIR, expid,
                                  BasicConfig.LOCAL_TMP_DIR, BasicConfig.LOCAL_ASLOG_DIR, 'monitor.log'))
        Log.info("Getting job list...")

        as_conf = AutosubmitConfig(expid, BasicConfig, ConfigParserFactory())
        if not as_conf.check_conf_files():
            Log.critical('Can not run with invalid configuration')
            return False

        pkl_dir = os.path.join(BasicConfig.LOCAL_ROOT_DIR, expid, 'pkl')

        job_list = Autosubmit.load_job_list(
            expid, as_conf, notransitive=notransitive, monitor=True)
        Log.debug("Job list restored from {0} files", pkl_dir)

        if not isinstance(job_list, type([])):
            jobs = []
            if filter_chunks:
                fc = filter_chunks
                Log.debug(fc)

                if fc == 'Any':
                    jobs = job_list.get_job_list()
                else:
                    # noinspection PyTypeChecker
                    data = json.loads(Autosubmit._create_json(fc))
                    for date_json in data['sds']:
                        date = date_json['sd']
                        jobs_date = filter(lambda j: date2str(
                            j.date) == date, job_list.get_job_list())

                        for member_json in date_json['ms']:
                            member = member_json['m']
                            jobs_member = filter(
                                lambda j: j.member == member, jobs_date)

                            for chunk_json in member_json['cs']:
                                chunk = int(chunk_json)
                                jobs = jobs + \
                                    [job for job in filter(
                                        lambda j: j.chunk == chunk, jobs_member)]

            elif filter_status:
                Log.debug("Filtering jobs with status {0}", filter_status)
                if filter_status == 'Any':
                    jobs = job_list.get_job_list()
                else:
                    fs = Autosubmit._get_status(filter_status)
                    jobs = [job for job in filter(
                        lambda j: j.status == fs, job_list.get_job_list())]

            elif filter_section:
                ft = filter_section
                Log.debug(ft)

                if ft == 'Any':
                    jobs = job_list.get_job_list()
                else:
                    for job in job_list.get_job_list():
                        if job.section == ft:
                            jobs.append(job)

            elif lst:
                jobs_lst = lst.split()

                if jobs == 'Any':
                    jobs = job_list.get_job_list()
                else:
                    for job in job_list.get_job_list():
                        if job.name in jobs_lst:
                            jobs.append(job)
            else:
                jobs = job_list.get_job_list()

        referenced_jobs_to_remove = set()
        for job in jobs:
            for child in job.children:
                if child not in jobs:
                    referenced_jobs_to_remove.add(child)
            for parent in job.parents:
                if parent not in jobs:
                    referenced_jobs_to_remove.add(parent)

        for job in jobs:
            job.children = job.children - referenced_jobs_to_remove
            job.parents = job.parents - referenced_jobs_to_remove
        # WRAPPERS
        if as_conf.get_wrapper_type() != 'none' and check_wrapper:
            packages_persistence = JobPackagePersistence(os.path.join(BasicConfig.LOCAL_ROOT_DIR, expid, "pkl"),
                                                         "job_packages_" + expid)
            os.chmod(os.path.join(BasicConfig.LOCAL_ROOT_DIR, expid,
                                  "pkl", "job_packages_" + expid + ".db"), 0664)
            packages_persistence.reset_table(True)
            referenced_jobs_to_remove = set()
            job_list_wrappers = copy.deepcopy(job_list)
            jobs_wr = copy.deepcopy(jobs)
            [job for job in jobs_wr if (job.status != Status.COMPLETED)]
            for job in jobs_wr:
                for child in job.children:
                    if child not in jobs_wr:
                        referenced_jobs_to_remove.add(child)
                for parent in job.parents:
                    if parent not in jobs_wr:
                        referenced_jobs_to_remove.add(parent)

            for job in jobs_wr:
                job.children = job.children - referenced_jobs_to_remove
                job.parents = job.parents - referenced_jobs_to_remove
            Autosubmit.generate_scripts_andor_wrappers(as_conf, job_list_wrappers, jobs_wr,
                                                       packages_persistence, True)

            packages = packages_persistence.load(True)
        else:
            packages = JobPackagePersistence(os.path.join(BasicConfig.LOCAL_ROOT_DIR, expid, "pkl"),
                                             "job_packages_" + expid).load()

        # print(packages)

        groups_dict = dict()
        if group_by:
            status = list()
            if expand_status:
                for s in expand_status.split():
                    status.append(Autosubmit._get_status(s.upper()))

            job_grouping = JobGrouping(group_by, copy.deepcopy(
                jobs), job_list, expand_list=expand, expanded_status=status)
            groups_dict = job_grouping.group_jobs()

        monitor_exp = Monitor()

        if txt_only or txt_logfiles:
            monitor_exp.generate_output_txt(expid, jobs, os.path.join(
                exp_path, "/tmp/LOG_" + expid), txt_logfiles)
        else:
            monitor_exp.generate_output(expid, jobs, os.path.join(
                exp_path, "/tmp/LOG_", expid), file_format, packages, not hide, groups_dict, hide_groups=hide_groups)

        return True

    @staticmethod
    def statistics(expid, filter_type, filter_period, file_format, hide, notransitive=False):
        """
        Plots statistics graph for a given experiment.
        Plot is created in experiment's plot folder with name <expid>_<date>_<time>.<file_format>

        :type file_format: str
        :type expid: str
        :param expid: identifier of the experiment to plot
        :param filter_type: type of the jobs to plot
        :param filter_period: period to plot
        :param file_format: plot's file format. It can be pdf, png, ps or svg
        :param hide: hides plot window
        :type hide: bool
        """
        BasicConfig.read()
        exp_path = os.path.join(BasicConfig.LOCAL_ROOT_DIR, expid)
        if not os.path.exists(exp_path):
            Log.critical(
                "The directory %s is needed and does not exist." % exp_path)
            Log.warning("Does an experiment with the given id exist?")
            return 1

        Log.set_file(os.path.join(BasicConfig.LOCAL_ROOT_DIR, expid,
                                  BasicConfig.LOCAL_TMP_DIR, BasicConfig.LOCAL_ASLOG_DIR, 'statistics.log'))
        Log.info("Loading jobs...")

        as_conf = AutosubmitConfig(expid, BasicConfig, ConfigParserFactory())
        if not as_conf.check_conf_files():
            Log.critical('Can not run with invalid configuration')
            return False

        pkl_dir = os.path.join(BasicConfig.LOCAL_ROOT_DIR, expid, 'pkl')
        job_list = Autosubmit.load_job_list(
            expid, as_conf, notransitive=notransitive)
        Log.debug("Job list restored from {0} files", pkl_dir)

        if filter_type:
            ft = filter_type
            Log.debug(ft)
            if ft == 'Any':
                job_list = job_list.get_job_list()
            else:
                job_list = [job for job in job_list.get_job_list()
                            if job.section == ft]
        else:
            ft = 'Any'
            job_list = job_list.get_job_list()

        period_fi = datetime.datetime.now().replace(second=0, microsecond=0)
        if filter_period:
            period_ini = period_fi - datetime.timedelta(hours=filter_period)
            # Log.debug(str(period_ini))
            job_list = [job for job in job_list if
                        job.check_started_after(period_ini) or job.check_running_after(period_ini)]
        else:
            period_ini = None

        if len(job_list) > 0:
            # Log.info("Plotting stats...")
            monitor_exp = Monitor()
            # noinspection PyTypeChecker
            monitor_exp.generate_output_stats(
                expid, job_list, file_format, period_ini, period_fi, not hide)
            # Log.result("Stats plot ready")
        else:
            Log.info("There are no {0} jobs in the period from {1} to {2}...".format(
                ft, period_ini, period_fi))
        return True

    @staticmethod
    def clean(expid, project, plot, stats, create_log_file=True):
        """
        Clean experiment's directory to save storage space.
        It removes project directory and outdated plots or stats.

        :param create_log_file: if true, creates log file
        :type create_log_file: bool
        :type plot: bool
        :type project: bool
        :type expid: str
        :type stats: bool
        :param expid: identifier of experiment to clean
        :param project: set True to delete project directory
        :param plot: set True to delete outdated plots
        :param stats: set True to delete outdated stats
        """
        BasicConfig.read()
        exp_path = os.path.join(BasicConfig.LOCAL_ROOT_DIR, expid)
        if not os.path.exists(exp_path):
            Log.critical(
                "The directory %s is needed and does not exist." % exp_path)
            Log.warning("Does an experiment with the given id exist?")
            return 1

        if create_log_file:
            Log.set_file(os.path.join(BasicConfig.LOCAL_ROOT_DIR, expid,
                                      BasicConfig.LOCAL_TMP_DIR, BasicConfig.LOCAL_ASLOG_DIR, 'clean_exp.log'))
        if project:
            autosubmit_config = AutosubmitConfig(
                expid, BasicConfig, ConfigParserFactory())
            if not autosubmit_config.check_conf_files():
                Log.critical(
                    'Can not clean project with invalid configuration')
                return False

            project_type = autosubmit_config.get_project_type()
            if project_type == "git":
                autosubmit_config.check_proj()
                Log.info("Registering commit SHA...")
                autosubmit_config.set_git_project_commit(autosubmit_config)
                autosubmit_git = AutosubmitGit(expid[0])
                Log.info("Cleaning GIT directory...")
                if not autosubmit_git.clean_git(autosubmit_config):
                    return False
            else:
                Log.info("No project to clean...\n")
        if plot:
            Log.info("Cleaning plots...")
            monitor_autosubmit = Monitor()
            monitor_autosubmit.clean_plot(expid)
        if stats:
            Log.info("Cleaning stats directory...")
            monitor_autosubmit = Monitor()
            monitor_autosubmit.clean_stats(expid)
        return True

    @staticmethod
    def recovery(expid, noplot, save, all_jobs, hide, group_by=None, expand=list(), expand_status=list(),
                 notransitive=False, no_recover_logs=False):
        """
        Method to check all active jobs. If COMPLETED file is found, job status will be changed to COMPLETED,
        otherwise it will be set to WAITING. It will also update the jobs list.

        :param expid: identifier of the experiment to recover
        :type expid: str
        :param save: If true, recovery saves changes to the jobs list
        :type save: bool
        :param all_jobs: if True, it tries to get completed files for all jobs, not only active.
        :type all_jobs: bool
        :param hide: hides plot window
        :type hide: bool
        """
        BasicConfig.read()
        exp_path = os.path.join(BasicConfig.LOCAL_ROOT_DIR, expid)
        if not os.path.exists(exp_path):
            Log.critical(
                "The directory %s is needed and does not exist." % exp_path)
            Log.warning("Does an experiment with the given id exist?")
            return 1

        Log.set_file(os.path.join(BasicConfig.LOCAL_ROOT_DIR, expid,
                                  BasicConfig.LOCAL_TMP_DIR, BasicConfig.LOCAL_ASLOG_DIR, 'recovery.log'))

        as_conf = AutosubmitConfig(expid, BasicConfig, ConfigParserFactory())
        if not as_conf.check_conf_files():
            Log.critical('Can not run with invalid configuration')
            return False

        Log.info('Recovering experiment {0}'.format(expid))
        pkl_dir = os.path.join(BasicConfig.LOCAL_ROOT_DIR, expid, 'pkl')
        job_list = Autosubmit.load_job_list(
            expid, as_conf, notransitive=notransitive, monitor=True)
        Log.debug("Job list restored from {0} files", pkl_dir)

        if not as_conf.check_conf_files():
            Log.critical('Can not recover with invalid configuration')
            return False

        hpcarch = as_conf.get_platform()

        submitter = Autosubmit._get_submitter(as_conf)
        submitter.load_platforms(as_conf)
        if submitter.platforms is None:
            return False
        platforms = submitter.platforms

        platforms_to_test = set()
        for job in job_list.get_job_list():
            if job.platform_name is None:
                job.platform_name = hpcarch
            # noinspection PyTypeChecker
            job.platform = platforms[job.platform_name.lower()]
            # noinspection PyTypeChecker
            platforms_to_test.add(platforms[job.platform_name.lower()])

        if all_jobs:
            jobs_to_recover = job_list.get_job_list()
        else:
            jobs_to_recover = job_list.get_active()

        Log.info("Looking for COMPLETED files")
        start = datetime.datetime.now()
        for job in jobs_to_recover:
            if job.platform_name is None:
                job.platform_name = hpcarch
            # noinspection PyTypeChecker
            job.platform = platforms[job.platform_name.lower()]

            if job.platform.get_completed_files(job.name, 0):
                job.status = Status.COMPLETED
                Log.info(
                    "CHANGED job '{0}' status to COMPLETED".format(job.name))
                if not no_recover_logs:
                    try:
                        job.platform.get_logs_files(expid, job.remote_logs)
                    except:
                        pass
                        #Log.warning("Unable to retrieve the log file of {0} in platform {1}",job.name,job.platform.name)
            elif job.status != Status.SUSPENDED:
                job.status = Status.WAITING
                job.fail_count = 0
                Log.info(
                    "CHANGED job '{0}' status to WAITING".format(job.name))

        end = datetime.datetime.now()
        Log.info("Time spent: '{0}'".format(end - start))
        Log.info("Updating the jobs list")
        job_list.update_list(as_conf)

        if save:
            job_list.save()
        else:
            Log.warning(
                'Changes NOT saved to the jobList. Use -s option to save')

        Log.result("Recovery finalized")

        packages = JobPackagePersistence(os.path.join(BasicConfig.LOCAL_ROOT_DIR, expid, "pkl"),
                                         "job_packages_" + expid).load()

        groups_dict = dict()
        if group_by:
            status = list()
            if expand_status:
                for s in expand_status.split():
                    status.append(Autosubmit._get_status(s.upper()))

            job_grouping = JobGrouping(group_by, copy.deepcopy(job_list.get_job_list()), job_list, expand_list=expand,
                                       expanded_status=status)
            groups_dict = job_grouping.group_jobs()

        if not noplot:
            Log.info("\nPlotting the jobs list...")
            monitor_exp = Monitor()
            monitor_exp.generate_output(expid, job_list.get_job_list(), os.path.join(
                exp_path, "/tmp/LOG_", expid), packages=packages, show=not hide, groups=groups_dict)

        return True

    @staticmethod
    def migrate(experiment_id, offer, pickup):
        """
        Migrates experiment files from current to other user.
        It takes mapping information for new user from config files.

        :param experiment_id: experiment identifier:
        :param pickup:
        :param offer:
        """
        log_file = os.path.join(
            BasicConfig.LOCAL_ROOT_DIR, "ASlogs", 'migrate_{0}.log'.format(experiment_id))
        Log.set_file(log_file)

        if offer:
            Log.info('Migrating experiment {0}'.format(experiment_id))
            as_conf = AutosubmitConfig(
                experiment_id, BasicConfig, ConfigParserFactory())
            if not as_conf.check_conf_files():
                Log.critical('Can not proceed with invalid configuration')
                return False

            submitter = Autosubmit._get_submitter(as_conf)

            submitter.load_platforms(as_conf)
            if submitter.platforms is None:
                return False

            Log.info("Checking remote platforms")
            platforms = filter(lambda x: x not in [
                               'local', 'LOCAL'], submitter.platforms)
            already_moved = set()
            backup_files = []
            backup_conf = []

            error = False
            for platform in platforms:
                # Checks
                Log.info(
                    "Checking [{0}] from platforms configuration...", platform)
                if not as_conf.get_migrate_user_to(platform):
                    Log.critical(
                        "Missing directive USER_TO in [{0}]", platform)
                    error = True
                    break

                as_conf.set_new_user(
                    platform, as_conf.get_migrate_user_to(platform))
                if as_conf.get_migrate_project_to(platform):
                    Log.info("Project in platform configuration file successfully updated to {0}",
                             as_conf.get_migrate_user_to(platform))
                    backup_conf.append([platform, as_conf.get_current_user(
                        platform), as_conf.get_current_project(platform)])
                    as_conf.set_new_project(
                        platform, as_conf.get_migrate_project_to(platform))

                else:
                    Log.warning(
                        "optional PROJECT_TO directive not found. The directive PROJECT will remain unchanged")
                    backup_conf.append(
                        [platform, as_conf.get_current_user(platform), None])
                Log.info("Moving local files/dirs")
                p = submitter.platforms[platform]
                if p.temp_dir not in already_moved:
                    if p.root_dir != p.temp_dir or len(p.temp_dir) > 0:
                        already_moved.add(p.temp_dir)
                        Log.info("Converting abs symlink to relative")
                        # find /home/bsc32/bsc32070/dummy3 -type l -lname '/*' -printf ' ln -sf "$(realpath -s --relative-to="%p" $(readlink "%p")")" \n' > script.sh

                        # dummy
                        Log.info(
                            "Converting the absolute symlinks into relatives on platform {0} ", platform)
                        #command = "find " + p.root_dir + " -type l -lname \'/*\' -printf 'var=\"$(realpath -s --relative-to=\"%p\" \"$(readlink \"%p\")\")\" && var=${var:3} && ln -sf $var \"%p\"  \\n'"
                        if p.root_dir.find(experiment_id) < 0:
                            Log.error(
                                "(Aborting) it is not safe to change symlinks in {0} due an invalid expid", p.root_dir)
                            error = True
                            break
                        command = "find " + p.root_dir + \
                            " -type l -lname \'/*\' -printf 'var=\"$(realpath -s --relative-to=\"%p\" \"$(readlink \"%p\")\")\" && var=${var:3} && ln -sf $var \"%p\"  \\n' "
                        try:
                            p.send_command(command, False)
                            if p.get_ssh_output().startswith("var="):
                                p.send_command(p.get_ssh_output(), False)
                        except IOError:
                            Log.debug(
                                "The platform {0} does not contain absolute symlinks", platform)
                        except BaseException:
                            Log.warning(
                                "Absolute symlinks failed to convert, check user in platform.conf")
                            error = True
                            break

                        Log.info("Moving remote files/dirs on {0}", platform)

                        Log.info("Moving from {0} to {1}", p.root_dir, os.path.join(
                            p.temp_dir, experiment_id))
                        try:
                            if not p.move_file(p.root_dir, os.path.join(p.temp_dir, experiment_id), True):
                                Log.critical("The files/dirs on {0} cannot be moved to {1}.", p.root_dir,
                                             os.path.join(p.temp_dir, experiment_id))
                                error = True
                                break
                        except (IOError, BaseException):

                            Log.critical("The files/dirs on {0} cannot be moved to {1}.", p.root_dir,
                                         os.path.join(p.temp_dir, experiment_id))
                            error = True
                            break
                        backup_files.append(platform)

                Log.result(
                    "Files/dirs on {0} have been successfully offered", platform)
                Log.result("[{0}] from platforms configuration OK", platform)

            if error:
                Log.critical(
                    "The experiment cannot be offered, reverting changes")

                for platform in backup_files:
                    p = submitter.platforms[platform]
                    p.move_file(os.path.join(
                        p.temp_dir, experiment_id), p.root_dir, True)
                for platform in backup_conf:
                    as_conf.set_new_user(platform[0], platform[1])
                    if platform[2] is not None:
                        as_conf.set_new_project(platform[0], platform[2])

                return False
            else:
                if not Autosubmit.archive(experiment_id, False):
                    Log.critical(
                        "The experiment cannot be offered,reverting changes.")
                    for platform in backup_files:
                        p = submitter.platforms[platform]
                        p.move_file(os.path.join(
                            p.temp_dir, experiment_id), p.root_dir, True)

                    for platform in backup_conf:
                        as_conf.set_new_user(platform[0], platform[1])
                        if platform[2] is not None:
                            as_conf.set_new_project(platform[0], platform[2])

                    return False
                else:
                    Log.result("The experiment has been successfully offered.")
        elif pickup:
            Log.info('Migrating experiment {0}'.format(experiment_id))
            Log.info("Moving local files/dirs")
            if not Autosubmit.unarchive(experiment_id, True):
                Log.critical("The experiment cannot be picked up")
                return False
            Log.info("Local files/dirs have been successfully picked up")
            as_conf = AutosubmitConfig(
                experiment_id, BasicConfig, ConfigParserFactory())
            if not as_conf.check_conf_files():
                Log.critical('Can not proceed with invalid configuration')
                return False

            Log.info("Checking remote platforms")
            submitter = Autosubmit._get_submitter(as_conf)
            submitter.load_platforms(as_conf)
            if submitter.platforms is None:
                return False

            platforms = filter(lambda x: x not in [
                               'local', 'LOCAL'], submitter.platforms)
            already_moved = set()
            for platform in platforms:
                p = submitter.platforms[platform]
                if p.temp_dir not in already_moved:
                    if p.root_dir != p.temp_dir or len(p.temp_dir) > 0:
                        already_moved.add(p.temp_dir)
                Log.info("Copying remote files/dirs on {0}", platform)

                Log.info("Copying from {0} to {1}", os.path.join(
                    p.temp_dir, experiment_id), p.root_dir)
                try:
                    if not p.send_command("cp -rP " + os.path.join(p.temp_dir, experiment_id) + " " + p.root_dir):
                        Autosubmit.archive(experiment_id)
                        Log.critical(
                            "The experiment cannot be picked,reverting changes.")
                        Log.critical("The files/dirs on {0} cannot be copied to {1}.",
                                     os.path.join(p.temp_dir, experiment_id), p.root_dir)
                        return False

                except (IOError, BaseException):
                    Autosubmit.archive(experiment_id)
                    Log.critical(
                        "The experiment cannot be picked,reverting changes.")

                    Log.critical("The files/dirs on {0} cannot be copied to {1}.",
                                 os.path.join(p.temp_dir, experiment_id), p.root_dir)
                    return False

                Log.result(
                    "Files/dirs on {0} have been successfully picked up", platform)

            Log.result("The experiment has been successfully picked up.")

        return True

    @staticmethod
    def check(experiment_id, notransitive=False):
        """
        Checks experiment configuration and warns about any detected error or inconsistency.

        :param experiment_id: experiment identifier:
        :type experiment_id: str
        """
        BasicConfig.read()
        exp_path = os.path.join(BasicConfig.LOCAL_ROOT_DIR, experiment_id)
        if not os.path.exists(exp_path):
            Log.critical(
                "The directory {0} is needed and does not exist.", exp_path)
            Log.warning("Does an experiment with the given id exist?")
            return False

        log_file = os.path.join(BasicConfig.LOCAL_ROOT_DIR, experiment_id,
                                BasicConfig.LOCAL_TMP_DIR, BasicConfig.LOCAL_ASLOG_DIR, 'check_exp.log')
        Log.set_file(log_file)

        as_conf = AutosubmitConfig(
            experiment_id, BasicConfig, ConfigParserFactory())
        if not as_conf.check_conf_files():
            return False

        project_type = as_conf.get_project_type()
        if project_type != "none":
            if not as_conf.check_proj():
                return False

        submitter = Autosubmit._get_submitter(as_conf)
        submitter.load_platforms(as_conf)
        if len(submitter.platforms) == 0:
            return False

        pkl_dir = os.path.join(
            BasicConfig.LOCAL_ROOT_DIR, experiment_id, 'pkl')
        job_list = Autosubmit.load_job_list(
            experiment_id, as_conf, notransitive=notransitive)
        Log.debug("Job list restored from {0} files", pkl_dir)

        Autosubmit._load_parameters(as_conf, job_list, submitter.platforms)

        hpc_architecture = as_conf.get_platform()
        for job in job_list.get_job_list():
            if job.platform_name is None:
                job.platform_name = hpc_architecture
            job.platform = submitter.platforms[job.platform_name.lower()]
            job.update_parameters(as_conf, job_list.parameters)

        return job_list.check_scripts(as_conf)

    @staticmethod
    def describe(experiment_id):
        """
        Show details for specified experiment

        :param experiment_id: experiment identifier:
        :type experiment_id: str
        :return: user, date created, model, branch, hpc  
        :rtype: str, str, str, str, str
        """
        user = ""
        created = ""
        model = ""
        branch = ""
        hpc = ""
        BasicConfig.read()
        exp_path = os.path.join(BasicConfig.LOCAL_ROOT_DIR, experiment_id)
        if not os.path.exists(exp_path):
            return user, created, model, branch, hpc

        experiment_file = os.path.join(
            exp_path, "conf", "expdef_{}.conf".format(experiment_id))

        user = os.stat(experiment_file).st_uid
        try:
            user = pwd.getpwuid(user).pw_name
        except:
            pass

        created = datetime.datetime.fromtimestamp(
            os.path.getmtime(experiment_file))

        try:
            as_conf = AutosubmitConfig(
                experiment_id, BasicConfig, ConfigParserFactory())
            as_conf.reload()

            project_type = as_conf.get_project_type()
            if project_type != "none":
                if not as_conf.check_proj():
                    return False
            if (as_conf.get_svn_project_url()):
                model = as_conf.get_svn_project_url()
                branch = as_conf.get_svn_project_url()
            else:
                model = as_conf.get_git_project_origin()
                branch = as_conf.get_git_project_branch()
            if model is "":
                model = "Not Found"
            if branch is "":
                branch = "Not Found"
            hpc = as_conf.get_platform()
        except:
            pass
        return user, created, model, branch, hpc

    @staticmethod
    def configure(advanced, database_path, database_filename, local_root_path, platforms_conf_path, jobs_conf_path,
                  smtp_hostname, mail_from, machine, local):
        """
        Configure several paths for autosubmit: database, local root and others. Can be configured at system,
        user or local levels. Local level configuration precedes user level and user level precedes system
        configuration.

        :param database_path: path to autosubmit database
        :type database_path: str
        :param database_filename: database filename
        :type database_filename: str
        :param local_root_path: path to autosubmit's experiments' directory
        :type local_root_path: str
        :param platforms_conf_path: path to platforms conf file to be used as model for new experiments
        :type platforms_conf_path: str
        :param jobs_conf_path: path to jobs conf file to be used as model for new experiments
        :type jobs_conf_path: str
        :param machine: True if this configuration has to be stored for all the machine users
        :type machine: bool
        :param local: True if this configuration has to be stored in the local path
        :type local: bool
        :param mail_from:
        :type mail_from: str
        :param smtp_hostname:
        :type smtp_hostname: str
        """
        home_path = os.path.expanduser('~')
        # Setting default values
        if not advanced and database_path is None and local_root_path is None:
            database_path = home_path
            local_root_path = home_path + '/autosubmit'
            database_filename = 'autosubmit.db'

        while database_path is None:
            database_path = raw_input("Introduce Database path: ")
        database_path = database_path.replace('~', home_path)
        if not os.path.exists(database_path):
            Log.error("Database path does not exist.")
            return False

        while local_root_path is None:
            local_root_path = raw_input("Introduce path to experiments: ")
        local_root_path = local_root_path.replace('~', home_path)
        if not os.path.exists(local_root_path):
            Log.error("Local Root path does not exist.")
            return False

        if platforms_conf_path is not None:
            platforms_conf_path = platforms_conf_path.replace('~', home_path)
            if not os.path.exists(platforms_conf_path):
                Log.error("platforms.conf path does not exist.")
                return False
        if jobs_conf_path is not None:
            jobs_conf_path = jobs_conf_path.replace('~', home_path)
            if not os.path.exists(jobs_conf_path):
                Log.error("jobs.conf path does not exist.")
                return False

        if machine:
            path = '/etc'
        elif local:
            path = '.'
        else:
            path = home_path
        path = os.path.join(path, '.autosubmitrc')

        config_file = open(path, 'w')
        Log.info("Writing configuration file...")
        try:
            parser = SafeConfigParser()
            parser.add_section('database')
            parser.set('database', 'path', database_path)
            if database_filename is not None:
                parser.set('database', 'filename', database_filename)
            parser.add_section('local')
            parser.set('local', 'path', local_root_path)
            if jobs_conf_path is not None or platforms_conf_path is not None:
                parser.add_section('conf')
                if jobs_conf_path is not None:
                    parser.set('conf', 'jobs', jobs_conf_path)
                if platforms_conf_path is not None:
                    parser.set('conf', 'platforms', platforms_conf_path)
            if smtp_hostname is not None or mail_from is not None:
                parser.add_section('mail')
                parser.set('mail', 'smtp_server', smtp_hostname)
                parser.set('mail', 'mail_from', mail_from)
            parser.write(config_file)
            config_file.close()
            Log.result("Configuration file written successfully")
        except (IOError, OSError) as e:
            Log.critical("Can not write config file: {0}".format(e.message))
            return False
        return True

    @staticmethod
    def configure_dialog():
        """
        Configure several paths for autosubmit interactively: database, local root and others.
        Can be configured at system, user or local levels. Local level configuration precedes user level and user level
        precedes system configuration.
        """

        not_enough_screen_size_msg = 'The size of your terminal is not enough to draw the configuration wizard,\n' \
                                     'so we\'ve closed it to prevent errors. Resize it and then try it again.'

        home_path = os.path.expanduser('~')

        try:
            d = dialog.Dialog(
                dialog="dialog", autowidgetsize=True, screen_color='GREEN')
        except dialog.DialogError:
            Log.critical(not_enough_screen_size_msg)
            return False
        except Exception:
            Log.critical("Missing package 'dialog', please install it with: 'apt-get install dialog'"
                         "or provide configure arguments")
            return False

        d.set_background_title("Autosubmit configure utility")
        if os.geteuid() == 0:
            text = ''
            choice = [
                ("All", "All users on this machine (may require root privileges)")]
        else:
            text = "If you want to configure Autosubmit for all users, you will need to provide root privileges"
            choice = []

        choice.append(("User", "Current user"))
        choice.append(
            ("Local", "Only when launching Autosubmit from this path"))

        try:
            code, level = d.menu(text, choices=choice, width=60,
                                 title="Choose when to apply the configuration")
            if code != dialog.Dialog.OK:
                os.system('clear')
                return False
        except dialog.DialogError:
            Log.critical(not_enough_screen_size_msg)
            return False

        filename = '.autosubmitrc'
        if level == 'All':
            path = '/etc'
            filename = 'autosubmitrc'
        elif level == 'User':
            path = home_path
        else:
            path = '.'
        path = os.path.join(path, filename)

        # Setting default values
        database_path = home_path
        local_root_path = home_path
        database_filename = 'autosubmit.db'
        jobs_conf_path = ''
        platforms_conf_path = ''

        d.infobox("Reading configuration file...", width=50, height=5)
        try:
            if os.path.isfile(path):
                parser = SafeConfigParser()
                parser.optionxform = str
                parser.read(path)
                if parser.has_option('database', 'path'):
                    database_path = parser.get('database', 'path')
                if parser.has_option('database', 'filename'):
                    database_filename = parser.get('database', 'filename')
                if parser.has_option('local', 'path'):
                    local_root_path = parser.get('local', 'path')
                if parser.has_option('conf', 'platforms'):
                    platforms_conf_path = parser.get('conf', 'platforms')
                if parser.has_option('conf', 'jobs'):
                    jobs_conf_path = parser.get('conf', 'jobs')

        except (IOError, OSError) as e:
            Log.critical("Can not read config file: {0}".format(e.message))
            return False

        while True:
            try:
                code, database_path = d.dselect(database_path, width=80, height=20,
                                                title='\Zb\Z1Select path to database\Zn', colors='enable')
            except dialog.DialogError:
                Log.critical(not_enough_screen_size_msg)
                return False

            if Autosubmit._requested_exit(code, d):
                return False
            elif code == dialog.Dialog.OK:
                database_path = database_path.replace('~', home_path)
                if not os.path.exists(database_path):
                    d.msgbox(
                        "Database path does not exist.\nPlease, insert the right path", width=50, height=6)
                else:
                    break

        while True:
            try:
                code, local_root_path = d.dselect(local_root_path, width=80, height=20,
                                                  title='\Zb\Z1Select path to experiments repository\Zn',
                                                  colors='enable')
            except dialog.DialogError:
                Log.critical(not_enough_screen_size_msg)
                return False

            if Autosubmit._requested_exit(code, d):
                return False
            elif code == dialog.Dialog.OK:
                database_path = database_path.replace('~', home_path)
                if not os.path.exists(database_path):
                    d.msgbox(
                        "Local root path does not exist.\nPlease, insert the right path", width=50, height=6)
                else:
                    break
        while True:
            try:
                (code, tag) = d.form(text="",
                                     elements=[("Database filename", 1, 1, database_filename, 1, 40, 20, 20),
                                               (
                                                   "Default platform.conf path", 2, 1, platforms_conf_path, 2, 40, 40,
                                                   200),
                                               ("Default jobs.conf path", 3, 1, jobs_conf_path, 3, 40, 40, 200)],
                                     height=20,
                                     width=80,
                                     form_height=10,
                                     title='\Zb\Z1Just a few more options:\Zn', colors='enable')
            except dialog.DialogError:
                Log.critical(not_enough_screen_size_msg)
                return False

            if Autosubmit._requested_exit(code, d):
                return False
            elif code == dialog.Dialog.OK:
                database_filename = tag[0]
                platforms_conf_path = tag[1]
                jobs_conf_path = tag[2]

                platforms_conf_path = platforms_conf_path.replace(
                    '~', home_path).strip()
                jobs_conf_path = jobs_conf_path.replace('~', home_path).strip()

                if platforms_conf_path and not os.path.exists(platforms_conf_path):
                    d.msgbox(
                        "Platforms conf path does not exist.\nPlease, insert the right path", width=50, height=6)
                elif jobs_conf_path and not os.path.exists(jobs_conf_path):
                    d.msgbox(
                        "Jobs conf path does not exist.\nPlease, insert the right path", width=50, height=6)
                else:
                    break

        smtp_hostname = "mail.bsc.es"
        mail_from = "automail@bsc.es"
        while True:
            try:
                (code, tag) = d.form(text="",
                                     elements=[("STMP server hostname", 1, 1, smtp_hostname, 1, 40, 20, 20),
                                               ("Notifications sender address", 2, 1, mail_from, 2, 40, 40, 200)],
                                     height=20,
                                     width=80,
                                     form_height=10,
                                     title='\Zb\Z1Mail notifications configuration:\Zn', colors='enable')
            except dialog.DialogError:
                Log.critical(not_enough_screen_size_msg)
                return False

            if Autosubmit._requested_exit(code, d):
                return False
            elif code == dialog.Dialog.OK:
                smtp_hostname = tag[0]
                mail_from = tag[1]
                break
                # TODO: Check that is a valid config?

        config_file = open(path, 'w')
        d.infobox("Writing configuration file...", width=50, height=5)
        try:
            parser = SafeConfigParser()
            parser.add_section('database')
            parser.set('database', 'path', database_path)
            if database_filename:
                parser.set('database', 'filename', database_filename)
            parser.add_section('local')
            parser.set('local', 'path', local_root_path)
            if jobs_conf_path or platforms_conf_path:
                parser.add_section('conf')
                if jobs_conf_path:
                    parser.set('conf', 'jobs', jobs_conf_path)
                if platforms_conf_path:
                    parser.set('conf', 'platforms', platforms_conf_path)
            parser.add_section('mail')
            parser.set('mail', 'smtp_server', smtp_hostname)
            parser.set('mail', 'mail_from', mail_from)
            parser.write(config_file)
            config_file.close()
            d.msgbox("Configuration file written successfully",
                     width=50, height=5)
            os.system('clear')
        except (IOError, OSError) as e:
            Log.critical("Can not write config file: {0}".format(e.message))
            os.system('clear')
            return False
        return True

    @staticmethod
    def _requested_exit(code, d):
        if code != dialog.Dialog.OK:
            code = d.yesno(
                'Exit configure utility without saving?', width=50, height=5)
            if code == dialog.Dialog.OK:
                os.system('clear')
                return True
        return False

    @staticmethod
    def install():
        """
        Creates a new database instance for autosubmit at the configured path

        """
        BasicConfig.read()
        Log.set_file(os.path.join(
            BasicConfig.LOCAL_ROOT_DIR, "ASlogs", 'install.log'))
        if not os.path.exists(BasicConfig.DB_PATH):
            Log.info("Creating autosubmit database...")
            qry = resource_string('autosubmit.database', 'data/autosubmit.sql')
            if not create_db(qry):
                Log.critical("Can not write database file")
                return False
            Log.result("Autosubmit database created successfully")
        else:
            Log.error("Database already exists.")
            return False
        return True

    @staticmethod
    def refresh(expid, model_conf, jobs_conf):
        """
        Refresh project folder for given experiment

        :param model_conf:
        :type model_conf: bool
        :param jobs_conf:
        :type jobs_conf: bool
        :param expid: experiment identifier
        :type expid: str
        """
        BasicConfig.read()
        Log.set_file(os.path.join(BasicConfig.LOCAL_ROOT_DIR, expid,
                                  BasicConfig.LOCAL_TMP_DIR, BasicConfig.LOCAL_ASLOG_DIR, 'refresh.log'))
        as_conf = AutosubmitConfig(expid, BasicConfig, ConfigParserFactory())
        as_conf.reload()
        if not as_conf.check_expdef_conf():
            Log.critical('Can not copy with invalid configuration')
            return False
        project_type = as_conf.get_project_type()
        if Autosubmit._copy_code(as_conf, expid, project_type, True):
            Log.result("Project folder updated")
        Autosubmit._create_project_associated_conf(
            as_conf, model_conf, jobs_conf)
        return True

    @staticmethod
    def archive(expid, clean=True):
        """
        Archives an experiment: call clean (if experiment is of version 3 or later), compress folder
        to tar.gz and moves to year's folder

        :param clean:
        :return:
        :param expid: experiment identifier
        :type expid: str
        """
        BasicConfig.read()
        exp_path = os.path.join(BasicConfig.LOCAL_ROOT_DIR, expid)
        if not os.path.exists(exp_path):
            Log.critical(
                "The directory %s is needed and does not exist." % exp_path)
            Log.warning("Does an experiment with the given id exist?")
            return 1

        Log.set_file(os.path.join(BasicConfig.LOCAL_ROOT_DIR,
                                  "ASlogs", 'archive_{0}.log'.format(expid)))
        exp_folder = os.path.join(BasicConfig.LOCAL_ROOT_DIR, expid)

        if clean:
            # Cleaning to reduce file size.
            version = get_autosubmit_version(expid)
            if version is not None and version.startswith('3') and not Autosubmit.clean(expid, True, True, True, False):
                Log.critical("Can not archive project. Clean not successful")
                return False

        # Getting year of last completed. If not, year of expid folder
        year = None
        tmp_folder = os.path.join(exp_folder, BasicConfig.LOCAL_TMP_DIR)
        if os.path.isdir(tmp_folder):
            for filename in os.listdir(tmp_folder):
                if filename.endswith("COMPLETED"):
                    file_year = time.localtime(os.path.getmtime(
                        os.path.join(tmp_folder, filename))).tm_year
                    if year is None or year < file_year:
                        year = file_year

        if year is None:
            year = time.localtime(os.path.getmtime(exp_folder)).tm_year
        Log.info("Archiving in year {0}", year)

        # Creating tar file
        Log.info("Creating tar file ... ")
        try:
            year_path = os.path.join(BasicConfig.LOCAL_ROOT_DIR, str(year))
            if not os.path.exists(year_path):
                os.mkdir(year_path)
            with tarfile.open(os.path.join(year_path, '{0}.tar.gz'.format(expid)), "w:gz") as tar:
                tar.add(exp_folder, arcname='')
                tar.close()
                os.chmod(os.path.join(
                    year_path, '{0}.tar.gz'.format(expid)), 0o775)
        except Exception as e:
            Log.critical("Can not write tar file: {0}".format(e))
            return False

        Log.info("Tar file created!")

        try:
            shutil.rmtree(exp_folder)
        except Exception as e:
            Log.critical("Can not remove experiments folder: {0}".format(e))
            Autosubmit.unarchive(expid)
            return False

        Log.result("Experiment archived successfully")
        return True

    @staticmethod
    def unarchive(experiment_id, migrate=False):
        """
        Unarchives an experiment: uncompress folder from tar.gz and moves to experiments root folder

        :param experiment_id: experiment identifier
        :type experiment_id: str
        """
        BasicConfig.read()
        Log.set_file(os.path.join(BasicConfig.LOCAL_ROOT_DIR,
                                  "ASlogs", 'unarchive_{0}.log'.format(experiment_id)))
        exp_folder = os.path.join(BasicConfig.LOCAL_ROOT_DIR, experiment_id)

        if os.path.exists(exp_folder):
            Log.error("Experiment {0} is not archived", experiment_id)
            return False

        # Searching by year. We will store it on database
        year = datetime.datetime.today().year
        archive_path = None
        while year > 2000:
            archive_path = os.path.join(BasicConfig.LOCAL_ROOT_DIR, str(
                year), '{0}.tar.gz'.format(experiment_id))
            if os.path.exists(archive_path):
                break
            year -= 1

        if year == 2000:
            Log.critical("Experiment can not be located on archive")
            return False
        Log.info("Experiment located in {0} archive", year)

        # Creating tar file
        Log.info("Unpacking tar file ... ")
        try:
            os.mkdir(exp_folder)
            with tarfile.open(os.path.join(archive_path), "r:gz") as tar:
                tar.extractall(exp_folder)
                tar.close()
        except Exception as e:
            os.rmdir(exp_folder)
            Log.critical("Can not extract tar file: {0}".format(e))
            return False

        Log.info("Unpacking finished")
        if not migrate:
            try:
                os.remove(archive_path)
            except Exception as e:
                Log.error("Can not remove archived file folder: {0}".format(e))
                return False

        Log.result("Experiment {0} unarchived successfully", experiment_id)
        return True

    @staticmethod
    def _create_project_associated_conf(as_conf, force_model_conf, force_jobs_conf):
        project_destiny = as_conf.project_file
        jobs_destiny = as_conf.jobs_file

        if as_conf.get_project_type() != 'none':
            if as_conf.get_file_project_conf():
                copy = True
                if os.path.exists(project_destiny):
                    if force_model_conf:
                        os.remove(project_destiny)
                    else:
                        copy = False
                if copy:
                    shutil.copyfile(os.path.join(as_conf.get_project_dir(), as_conf.get_file_project_conf()),
                                    project_destiny)

            if as_conf.get_file_jobs_conf():
                copy = True
                if os.path.exists(jobs_destiny):
                    if force_jobs_conf:
                        os.remove(jobs_destiny)
                    else:
                        copy = False
                if copy:
                    shutil.copyfile(os.path.join(as_conf.get_project_dir(), as_conf.get_file_jobs_conf()),
                                    jobs_destiny)

    @staticmethod
    def create(expid, noplot, hide, output='pdf', group_by=None, expand=list(), expand_status=list(), notransitive=False, check_wrappers=False):
        """
        Creates job list for given experiment. Configuration files must be valid before realizing this process.

        :param expid: experiment identifier
        :type expid: str
        :param noplot: if True, method omits final plotting of the jobs list. Only needed on large experiments when
        plotting time can be much larger than creation time.
        :type noplot: bool
        :return: True if successful, False if not
        :rtype: bool
        :param hide: hides plot window
        :type hide: bool
        :param hide: hides plot window
        :type hide: bool
        :param output: plot's file format. It can be pdf, png, ps or svg
        :type output: str

        """
        BasicConfig.read()

        exp_path = os.path.join(BasicConfig.LOCAL_ROOT_DIR, expid)
        tmp_path = os.path.join(exp_path, BasicConfig.LOCAL_TMP_DIR)
        aslogs_path = os.path.join(tmp_path, BasicConfig.LOCAL_ASLOG_DIR)
        if not os.path.exists(aslogs_path):
            os.mkdir(aslogs_path)
            os.chmod(aslogs_path, 0o775)
        if not os.path.exists(exp_path):
            Log.critical(
                "The directory %s is needed and does not exist." % exp_path)
            Log.warning("Does an experiment with the given id exist?")
            return 1

        # checking if there is a lock file to avoid multiple running on the same expid
        try:
            with portalocker.Lock(os.path.join(tmp_path, 'autosubmit.lock'), timeout=1):
                Log.info(
                    "Preparing .lock file to avoid multiple instances with same expid.")
                Log.set_file(os.path.join(
                    tmp_path, BasicConfig.LOCAL_ASLOG_DIR, 'create_exp.log'))

                as_conf = AutosubmitConfig(
                    expid, BasicConfig, ConfigParserFactory())
                if not as_conf.check_conf_files():
                    Log.critical('Can not create with invalid configuration')
                    return False

                project_type = as_conf.get_project_type()

                if not Autosubmit._copy_code(as_conf, expid, project_type, False):
                    return False
                update_job = not os.path.exists(os.path.join(BasicConfig.LOCAL_ROOT_DIR, expid, "pkl",
                                                             "job_list_" + expid + ".pkl"))
                Autosubmit._create_project_associated_conf(
                    as_conf, False, update_job)

                if project_type != "none":
                    # Check project configuration
                    as_conf.check_proj()

                # Load parameters
                Log.info("Loading parameters...")
                parameters = as_conf.load_parameters()

                date_list = as_conf.get_date_list()
                if len(date_list) != len(set(date_list)):
                    Log.error('There are repeated start dates!')
                    return False
                num_chunks = as_conf.get_num_chunks()
                chunk_ini = as_conf.get_chunk_ini()
                member_list = as_conf.get_member_list()
                if len(member_list) != len(set(member_list)):
                    Log.error('There are repeated member names!')
                    return False
                rerun = as_conf.get_rerun()

                Log.info("\nCreating the jobs list...")
                job_list = JobList(expid, BasicConfig, ConfigParserFactory(),
                                   Autosubmit._get_job_list_persistence(expid, as_conf))

                date_format = ''
                if as_conf.get_chunk_size_unit() is 'hour':
                    date_format = 'H'
                for date in date_list:
                    if date.hour > 1:
                        date_format = 'H'
                    if date.minute > 1:
                        date_format = 'M'
                job_list.generate(date_list, member_list, num_chunks, chunk_ini, parameters, date_format,
                                  as_conf.get_retrials(),
                                  as_conf.get_default_job_type(),
                                  as_conf.get_wrapper_type(), as_conf.get_wrapper_jobs(), notransitive=notransitive)

                if rerun == "true":
                    chunk_list = Autosubmit._create_json(
                        as_conf.get_chunk_list())
                    job_list.rerun(chunk_list, notransitive)
                else:
                    job_list.remove_rerun_only_jobs(notransitive)
                Log.info("\nSaving the jobs list...")
                job_list.save()
                JobPackagePersistence(os.path.join(BasicConfig.LOCAL_ROOT_DIR, expid, "pkl"),
                                      "job_packages_" + expid).reset_table()

                groups_dict = dict()

                if not noplot:
                    if group_by:
                        status = list()
                        if expand_status:
                            for s in expand_status.split():
                                status.append(
                                    Autosubmit._get_status(s.upper()))

                        job_grouping = JobGrouping(group_by, copy.deepcopy(job_list.get_job_list()), job_list,
                                                   expand_list=expand, expanded_status=status)
                        groups_dict = job_grouping.group_jobs()
                    # WRAPPERS
                    if as_conf.get_wrapper_type() != 'none' and check_wrappers:
                        packages_persistence = JobPackagePersistence(
                            os.path.join(BasicConfig.LOCAL_ROOT_DIR, expid, "pkl"), "job_packages_" + expid)
                        packages_persistence.reset_table(True)
                        referenced_jobs_to_remove = set()
                        job_list_wrappers = copy.deepcopy(job_list)
                        jobs_wr = job_list_wrappers.get_job_list()
                        for job in jobs_wr:
                            for child in job.children:
                                if child not in jobs_wr:
                                    referenced_jobs_to_remove.add(child)
                            for parent in job.parents:
                                if parent not in jobs_wr:
                                    referenced_jobs_to_remove.add(parent)

                        for job in jobs_wr:
                            job.children = job.children - referenced_jobs_to_remove
                            job.parents = job.parents - referenced_jobs_to_remove
                        Autosubmit.generate_scripts_andor_wrappers(as_conf, job_list_wrappers, jobs_wr,
                                                                   packages_persistence, True)

                        packages = packages_persistence.load(True)
                    else:
                        packages = None

                    Log.info("\nPlotting the jobs list...")
                    monitor_exp = Monitor()
                    monitor_exp.generate_output(expid, job_list.get_job_list(),
                                                os.path.join(
                                                    exp_path, "/tmp/LOG_", expid), output, packages, not hide,
                                                groups=groups_dict)

                Log.result("\nJob list created successfully")
                Log.user_warning("Remember to MODIFY the MODEL config files!")

                return True

        except portalocker.AlreadyLocked:
            Autosubmit.show_lock_warning(expid)

    @staticmethod
    def _copy_code(as_conf, expid, project_type, force):
        """
        Method to copy code from experiment repository to project directory.

        :param as_conf: experiment configuration class
        :type as_conf: AutosubmitConfig
        :param expid: experiment identifier
        :type expid: str
        :param project_type: project type (git, svn, local)
        :type project_type: str
        :param force: if True, overwrites current data
        :return: True if succesful, False if not
        :rtype: bool
        """
        project_destination = as_conf.get_project_destination()
        if project_type == "git":
            return AutosubmitGit.clone_repository(as_conf, force)
        elif project_type == "svn":
            svn_project_url = as_conf.get_svn_project_url()
            svn_project_revision = as_conf.get_svn_project_revision()
            project_path = os.path.join(
                BasicConfig.LOCAL_ROOT_DIR, expid, BasicConfig.LOCAL_PROJ_DIR)
            if os.path.exists(project_path):
                Log.info("Using project folder: {0}", project_path)
                if not force:
                    Log.debug("The project folder exists. SKIPPING...")
                    return True
                else:
                    shutil.rmtree(project_path, ignore_errors=True)
            os.mkdir(project_path)
            Log.debug("The project folder {0} has been created.", project_path)
            Log.info("Checking out revision {0} into {1}",
                     svn_project_revision + " " + svn_project_url, project_path)
            try:
                output = subprocess.check_output("cd " + project_path + "; svn --force-interactive checkout -r " +
                                                 svn_project_revision + " " + svn_project_url + " " +
                                                 project_destination, shell=True)
            except subprocess.CalledProcessError:
                Log.error("Can not check out revision {0} into {1}", svn_project_revision + " " + svn_project_url,
                          project_path)
                shutil.rmtree(project_path, ignore_errors=True)
                return False
            Log.debug("{0}", output)

        elif project_type == "local":
            local_project_path = as_conf.get_local_project_path()
            project_path = os.path.join(
                BasicConfig.LOCAL_ROOT_DIR, expid, BasicConfig.LOCAL_PROJ_DIR)
            local_destination = os.path.join(project_path, project_destination)

            if os.path.exists(project_path):

                Log.info("Using project folder: {0}", project_path)
                if os.path.exists(local_destination):
                    try:
                        cmd = ["rsync -ach --info=progress2 " +
                               local_project_path + "/* " + local_destination]
                        subprocess.call(cmd, shell=True)
                    except subprocess.CalledProcessError:
                        Log.error(
                            "Can not synchronize {0} into {1}. Exiting...", local_project_path, project_path)
                        # shutil.rmtree(project_path)
                        return False
                else:
                    os.mkdir(local_destination)
                    try:
                        output = subprocess.check_output(
                            "cp -R " + local_project_path + "/* " + local_destination, shell=True)
                    except subprocess.CalledProcessError:
                        Log.error(
                            "Can not copy {0} into {1}. Exiting...", local_project_path, project_path)
                        shutil.rmtree(project_path)
                        return False
            else:
                os.mkdir(project_path)
                os.mkdir(local_destination)
                Log.debug(
                    "The project folder {0} has been created.", project_path)
                Log.info("Copying {0} into {1}",
                         local_project_path, project_path)

                try:
                    output = subprocess.check_output(
                        "cp -R " + local_project_path + "/* " + local_destination, shell=True)
                except subprocess.CalledProcessError:
                    Log.error(
                        "Can not copy {0} into {1}. Exiting...", local_project_path, project_path)
                    shutil.rmtree(project_path)
                    return False
                Log.debug("{0}", output)
        return True

    @staticmethod
    def change_status(final, final_status, job):
        """
        Set job status to final

        :param final:
        :param final_status:
        :param job:
        """
        job.status = final_status
        Log.info("CHANGED: job: " + job.name + " status to: " + final)

    @staticmethod
    def set_status(expid, noplot, save, final, lst, filter_chunks, filter_status, filter_section, hide, group_by=None,
                   expand=list(), expand_status=list(), notransitive=False, check_wrapper=False):
        """
        Set status

        :param expid: experiment identifier
        :type expid: str
        :param save: if true, saves the new jobs list
        :type save: bool
        :param final: status to set on jobs
        :type final: str
        :param lst: list of jobs to change status
        :type lst: str
        :param filter_chunks: chunks to change status
        :type filter_chunks: str
        :param filter_status: current status of the jobs to change status
        :type filter_status: str
        :param filter_section: sections to change status
        :type filter_section: str
        :param hide: hides plot window
        :type hide: bool
        """
        BasicConfig.read()
        exp_path = os.path.join(BasicConfig.LOCAL_ROOT_DIR, expid)
        tmp_path = os.path.join(exp_path, BasicConfig.LOCAL_TMP_DIR)
        if not os.path.exists(exp_path):
            Log.critical(
                "The directory %s is needed and does not exist." % exp_path)
            Log.warning("Does an experiment with the given id exist?")
            return 1

        # checking if there is a lock file to avoid multiple running on the same expid
        try:
            with portalocker.Lock(os.path.join(tmp_path, 'autosubmit.lock'), timeout=1):
                Log.info(
                    "Preparing .lock file to avoid multiple instances with same expid.")

                Log.set_file(os.path.join(
                    tmp_path, BasicConfig.LOCAL_ASLOG_DIR, 'set_status.log'))
                Log.debug('Exp ID: {0}', expid)
                Log.debug('Save: {0}', save)
                Log.debug('Final status: {0}', final)
                Log.debug('List of jobs to change: {0}', lst)
                Log.debug('Chunks to change: {0}', filter_chunks)
                Log.debug('Status of jobs to change: {0}', filter_status)
                Log.debug('Sections to change: {0}', filter_section)
                wrongExpid = 0
                as_conf = AutosubmitConfig(
                    expid, BasicConfig, ConfigParserFactory())
                if not as_conf.check_conf_files():
                    Log.critical('Can not run with invalid configuration')
                    return False

                job_list = Autosubmit.load_job_list(
                    expid, as_conf, notransitive=notransitive)
                jobs_filtered = []
                final_status = Autosubmit._get_status(final)
                if filter_section or filter_chunks:
                    if filter_section:
                        ft = filter_section.split()
                    else:
                        ft = filter_chunks.split(",")[1:]
                    if ft == 'Any':
                        for job in job_list.get_job_list():
                            Autosubmit.change_status(final, final_status, job)
                    else:
                        for section in ft:
                            for job in job_list.get_job_list():
                                if job.section == section:
                                    if filter_chunks:
                                        jobs_filtered.append(job)
                                    else:
                                        Autosubmit.change_status(
                                            final, final_status, job)

                if filter_chunks:
                    if len(jobs_filtered) == 0:
                        jobs_filtered = job_list.get_job_list()

                    fc = filter_chunks
                    Log.debug(fc)

                    if fc == 'Any':
                        for job in jobs_filtered:
                            Autosubmit.change_status(final, final_status, job)
                    else:
                        # noinspection PyTypeChecker
                        data = json.loads(Autosubmit._create_json(fc))
                        for date_json in data['sds']:
                            date = date_json['sd']
                            jobs_date = filter(lambda j: date2str(
                                j.date) == date, jobs_filtered)

                            for member_json in date_json['ms']:
                                member = member_json['m']
                                jobs_member = filter(
                                    lambda j: j.member == member, jobs_date)

                                # for job in filter(lambda j: j.chunk is None, jobs_member):
                                #    Autosubmit.change_status(final, final_status, job)

                                for chunk_json in member_json['cs']:
                                    chunk = int(chunk_json)
                                    for job in filter(lambda j: j.chunk == chunk and j.synchronize is not None, jobs_date):
                                        Autosubmit.change_status(
                                            final, final_status, job)

                                    for job in filter(lambda j: j.chunk == chunk, jobs_member):
                                        Autosubmit.change_status(
                                            final, final_status, job)

                if filter_status:
                    status_list = filter_status.split()

                    Log.debug("Filtering jobs with status {0}", filter_status)
                    if status_list == 'Any':
                        for job in job_list.get_job_list():
                            Autosubmit.change_status(final, final_status, job)
                    else:
                        for status in status_list:
                            fs = Autosubmit._get_status(status)
                            for job in filter(lambda j: j.status == fs, job_list.get_job_list()):
                                Autosubmit.change_status(
                                    final, final_status, job)

                if lst:
                    jobs = lst.split()
                    expidJoblist = defaultdict(int)
                    for x in lst.split():
                        expidJoblist[str(x[0:4])] += 1

                    if str(expid) in expidJoblist:
                        wrongExpid = jobs.__len__() - expidJoblist[expid]
                    if wrongExpid > 0:
                        Log.warning(
                            "There are {0} job.name with an invalid Expid", wrongExpid)

                    if jobs == 'Any':
                        for job in job_list.get_job_list():
                            Autosubmit.change_status(final, final_status, job)
                    else:
                        for job in job_list.get_job_list():
                            if job.name in jobs:
                                Autosubmit.change_status(
                                    final, final_status, job)

                job_list.update_list(as_conf, False, True)

                if save and wrongExpid == 0:
                    job_list.save()
                else:
                    Log.warning(
                        "Changes NOT saved to the JobList!!!!:  use -s option to save")
                    if wrongExpid > 0:

                        Log.error(
                            "Save disabled due invalid  expid, please check <expid> or/and jobs expid name")

                if as_conf.get_wrapper_type() != 'none' and check_wrapper:
                    packages_persistence = JobPackagePersistence(os.path.join(BasicConfig.LOCAL_ROOT_DIR, expid, "pkl"),
                                                                 "job_packages_" + expid)
                    os.chmod(os.path.join(BasicConfig.LOCAL_ROOT_DIR,
                                          expid, "pkl", "job_packages_" + expid + ".db"), 0664)
                    packages_persistence.reset_table(True)
                    referenced_jobs_to_remove = set()
                    job_list_wrappers = copy.deepcopy(job_list)
                    jobs_wr = copy.deepcopy(job_list.get_job_list())
                    [job for job in jobs_wr if (
                        job.status != Status.COMPLETED)]
                    for job in jobs_wr:
                        for child in job.children:
                            if child not in jobs_wr:
                                referenced_jobs_to_remove.add(child)
                        for parent in job.parents:
                            if parent not in jobs_wr:
                                referenced_jobs_to_remove.add(parent)

                    for job in jobs_wr:
                        job.children = job.children - referenced_jobs_to_remove
                        job.parents = job.parents - referenced_jobs_to_remove
                    Autosubmit.generate_scripts_andor_wrappers(as_conf, job_list_wrappers, jobs_wr,
                                                               packages_persistence, True)

                    packages = packages_persistence.load(True)
                else:
                    packages = JobPackagePersistence(os.path.join(BasicConfig.LOCAL_ROOT_DIR, expid, "pkl"),
                                                     "job_packages_" + expid).load()
                if not noplot:
                    groups_dict = dict()
                    if group_by:
                        status = list()
                        if expand_status:
                            for s in expand_status.split():
                                status.append(
                                    Autosubmit._get_status(s.upper()))

                        job_grouping = JobGrouping(group_by, copy.deepcopy(job_list.get_job_list()), job_list, expand_list=expand,
                                                   expanded_status=status)
                        groups_dict = job_grouping.group_jobs()
                    Log.info("\nPloting joblist...")
                    monitor_exp = Monitor()
                    monitor_exp.generate_output(expid, job_list.get_job_list(), os.path.join(
                        exp_path, "/tmp/LOG_", expid), packages=packages, show=not hide, groups=groups_dict)

                return True

        except portalocker.AlreadyLocked:
            Autosubmit.show_lock_warning(expid)

    @staticmethod
    def _user_yes_no_query(question):
        """
        Utility function to ask user a yes/no question

        :param question: question to ask
        :type question: str
        :return: True if answer is yes, False if it is no
        :rtype: bool
        """
        sys.stdout.write('{0} [y/n]\n'.format(question))
        while True:
            try:
                if sys.version_info[0] == 3:
                    answer = raw_input()
                else:
                    # noinspection PyCompatibility
                    answer = raw_input()
                return strtobool(answer.lower())
            except ValueError:
                sys.stdout.write('Please respond with \'y\' or \'n\'.\n')

    @staticmethod
    def _prepare_conf_files(exp_id, hpc, autosubmit_version, dummy):
        """
        Changes default configuration files to match new experiment values

        :param exp_id: experiment identifier
        :type exp_id: str
        :param hpc: hpc to use
        :type hpc: str
        :param autosubmit_version: current autosubmit's version
        :type autosubmit_version: str
        :param dummy: if True, creates a dummy experiment adding some default values
        :type dummy: bool
        """
        as_conf = AutosubmitConfig(exp_id, BasicConfig, ConfigParserFactory())
        as_conf.set_version(autosubmit_version)
        as_conf.set_expid(exp_id)
        as_conf.set_platform(hpc)
        as_conf.set_safetysleeptime(10)

        if dummy:
            content = open(as_conf.experiment_file).read()

            # Experiment
            content = content.replace(re.search('^DATELIST =.*', content, re.MULTILINE).group(0),
                                      "DATELIST = 20000101")
            content = content.replace(re.search('^MEMBERS =.*', content, re.MULTILINE).group(0),
                                      "MEMBERS = fc0")
            content = content.replace(re.search('^CHUNKSIZE =.*', content, re.MULTILINE).group(0),
                                      "CHUNKSIZE = 4")
            content = content.replace(re.search('^NUMCHUNKS =.*', content, re.MULTILINE).group(0),
                                      "NUMCHUNKS = 1")
            content = content.replace(re.search('^PROJECT_TYPE =.*', content, re.MULTILINE).group(0),
                                      "PROJECT_TYPE = none")

            open(as_conf.experiment_file, 'w').write(content)

    @staticmethod
    def _get_status(s):
        """
        Convert job status from str to Status

        :param s: status string
        :type s: str
        :return: status instance
        :rtype: Status
        """
        if s == 'READY':
            return Status.READY
        elif s == 'COMPLETED':
            return Status.COMPLETED
        elif s == 'WAITING':
            return Status.WAITING
        elif s == 'SUSPENDED':
            return Status.SUSPENDED
        elif s == 'FAILED':
            return Status.FAILED
        elif s == 'RUNNING':
            return Status.RUNNING
        elif s == 'QUEUING':
            return Status.QUEUING
        elif s == 'UNKNOWN':
            return Status.UNKNOWN

    @staticmethod
    def _get_members(out):
        """
        Function to get a list of members from json

        :param out: json member definition
        :type out: str
        :return: list of members
        :rtype: list
        """
        count = 0
        data = []
        # noinspection PyUnusedLocal
        for element in out:
            if count % 2 == 0:
                ms = {'m': out[count],
                      'cs': Autosubmit._get_chunks(out[count + 1])}
                data.append(ms)
                count += 1
            else:
                count += 1

        return data

    @staticmethod
    def _get_chunks(out):
        """
        Function to get a list of chunks from json

        :param out: json member definition
        :type out: str
        :return: list of chunks
        :rtype: list
        """
        data = []
        for element in out:
            if element.find("-") != -1:
                numbers = element.split("-")
                for count in range(int(numbers[0]), int(numbers[1]) + 1):
                    data.append(str(count))
            else:
                data.append(element)

        return data

    @staticmethod
    def _get_submitter(as_conf):
        """
        Returns the submitter corresponding to the communication defined on autosubmit's config file

        :return: submitter
        :rtype: Submitter
        """
        communications_library = as_conf.get_communications_library()
        if communications_library == 'saga':
            return SagaSubmitter()
        elif communications_library == 'paramiko':
            return ParamikoSubmitter()

        # communications library not known
        Log.error(
            'You have defined a not valid communications library on the configuration file')
        raise Exception('Communications library not known')

    @staticmethod
    def _get_job_list_persistence(expid, as_conf):
        """
        Returns the JobListPersistence corresponding to the storage type defined on autosubmit's config file

        :return: job_list_persistence
        :rtype: JobListPersistence
        """
        storage_type = as_conf.get_storage_type()
        if storage_type == 'pkl':
            return JobListPersistencePkl()
        elif storage_type == 'db':
            return JobListPersistenceDb(os.path.join(BasicConfig.LOCAL_ROOT_DIR, expid, "pkl"),
                                        "job_list_" + expid)

        # communications library not known
        Log.error(
            'You have defined a not valid storage type on the configuration file')
        raise Exception('Storage type not known')

    @staticmethod
    def _create_json(text):
        """
        Function to parse rerun specification from json format

        :param text: text to parse
        :type text: list
        :return: parsed output
        """
        count = 0
        data = []
        # text = "[ 19601101 [ fc0 [1 2 3 4] fc1 [1] ] 16651101 [ fc0 [1-30 31 32] ] ]"

        out = nestedExpr('[', ']').parseString(text).asList()

        # noinspection PyUnusedLocal
        for element in out[0]:
            if count % 2 == 0:
                sd = {'sd': out[0][count], 'ms': Autosubmit._get_members(
                    out[0][count + 1])}
                data.append(sd)
                count += 1
            else:
                count += 1

        sds = {'sds': data}
        result = json.dumps(sds)
        return result

    @staticmethod
    def testcase(copy_id, description, chunks=None, member=None, start_date=None, hpc=None, branch=None):
        """
        Method to create a test case. It creates a new experiment whose id starts by 't'.


        :param copy_id: experiment identifier
        :type copy_id: str
        :param description: test case experiment description
        :type description: str
        :param chunks: number of chunks to be run by the experiment. If None, it uses configured chunk(s).
        :type chunks: int
        :param member: member to be used by the test. If None, it uses configured member(s).
        :type member: str
        :param start_date: start date to be used by the test. If None, it uses configured start date(s).
        :type start_date: str
        :param hpc: HPC to be used by the test. If None, it uses configured HPC.
        :type hpc: str
        :param branch: branch or revision to be used by the test. If None, it uses configured branch.
        :type branch: str
        :return: test case id
        :rtype: str
        """

        testcaseid = Autosubmit.expid(hpc, description, copy_id, False, True)
        if testcaseid == '':
            return False

        Autosubmit._change_conf(
            testcaseid, hpc, start_date, member, chunks, branch, False)

        return testcaseid

    @staticmethod
    def test(expid, chunks, member=None, start_date=None, hpc=None, branch=None):
        """
        Method to conduct a test for a given experiment. It creates a new experiment for a given experiment with a
        given number of chunks with a random start date and a random member to be run on a random HPC.


        :param expid: experiment identifier
        :type expid: str
        :param chunks: number of chunks to be run by the experiment
        :type chunks: int
        :param member: member to be used by the test. If None, it uses a random one from which are defined on
                       the experiment.
        :type member: str
        :param start_date: start date to be used by the test. If None, it uses a random one from which are defined on
                         the experiment.
        :type start_date: str
        :param hpc: HPC to be used by the test. If None, it uses a random one from which are defined on
                    the experiment.
        :type hpc: str
        :param branch: branch or revision to be used by the test. If None, it uses configured branch.
        :type branch: str
        :return: True if test was succesful, False otherwise
        :rtype: bool
        """
        testid = Autosubmit.expid(
            'test', 'test experiment for {0}'.format(expid), expid, False, True)
        if testid == '':
            return False

        Autosubmit._change_conf(testid, hpc, start_date,
                                member, chunks, branch, True)

        Autosubmit.create(testid, False, True)
        if not Autosubmit.run_experiment(testid):
            return False
        return True

    @staticmethod
    def _change_conf(testid, hpc, start_date, member, chunks, branch, random_select=False):
        as_conf = AutosubmitConfig(testid, BasicConfig, ConfigParserFactory())
        exp_parser = as_conf.get_parser(
            ConfigParserFactory(), as_conf.experiment_file)
        if exp_parser.get_bool_option('rerun', "RERUN", True):
            Log.error('Can not test a RERUN experiment')
            return False

        content = open(as_conf.experiment_file).read()
        if random_select:
            if hpc is None:
                platforms_parser = as_conf.get_parser(
                    ConfigParserFactory(), as_conf.platforms_file)
                test_platforms = list()
                for section in platforms_parser.sections():
                    if platforms_parser.get_option(section, 'TEST_SUITE', 'false').lower() == 'true':
                        test_platforms.append(section)
                if len(test_platforms) == 0:
                    Log.critical('No test HPC defined')
                    return False
                hpc = random.choice(test_platforms)
            if member is None:
                member = random.choice(exp_parser.get(
                    'experiment', 'MEMBERS').split(' '))
            if start_date is None:
                start_date = random.choice(exp_parser.get(
                    'experiment', 'DATELIST').split(' '))
            if chunks is None:
                chunks = 1

        # Experiment
        content = content.replace(re.search('^EXPID =.*', content, re.MULTILINE).group(0),
                                  "EXPID = " + testid)
        if start_date is not None:
            content = content.replace(re.search('^DATELIST =.*', content, re.MULTILINE).group(0),
                                      "DATELIST = " + start_date)
        if member is not None:
            content = content.replace(re.search('^MEMBERS =.*', content, re.MULTILINE).group(0),
                                      "MEMBERS = " + member)
        if chunks is not None:
            # noinspection PyTypeChecker
            content = content.replace(re.search('^NUMCHUNKS =.*', content, re.MULTILINE).group(0),
                                      "NUMCHUNKS = " + chunks)
        if hpc is not None:
            content = content.replace(re.search('^HPCARCH =.*', content, re.MULTILINE).group(0),
                                      "HPCARCH = " + hpc)
        if branch is not None:
            content = content.replace(re.search('^PROJECT_BRANCH =.*', content, re.MULTILINE).group(0),
                                      "PROJECT_BRANCH = " + branch)
            content = content.replace(re.search('^PROJECT_REVISION =.*', content, re.MULTILINE).group(0),
                                      "PROJECT_REVISION = " + branch)

        open(as_conf.experiment_file, 'w').write(content)

    @staticmethod
    def load_job_list(expid, as_conf, notransitive=False, monitor=False):
        """
        Process that builds the job list.  
        """
        # print("Load Job List Start")
        try:
            BasicConfig.read()
            rerun = as_conf.get_rerun()
            job_list = JobList(expid, BasicConfig, ConfigParserFactory(),
                               Autosubmit._get_job_list_persistence(expid, as_conf))
            date_list = as_conf.get_date_list()
            date_format = ''
            if as_conf.get_chunk_size_unit() is 'hour':
                date_format = 'H'
            for date in date_list:
                if date.hour > 1:
                    date_format = 'H'
                if date.minute > 1:
                    date_format = 'M'
            run_only_members = as_conf.get_member_list(run_only=True)
            job_list.generate(date_list, as_conf.get_member_list(), as_conf.get_num_chunks(), as_conf.get_chunk_ini(),
                              as_conf.load_parameters(), date_format, as_conf.get_retrials(),
                              as_conf.get_default_job_type(), as_conf.get_wrapper_type(), as_conf.get_wrapper_jobs(),
                              new=False, notransitive=notransitive, run_only_members=run_only_members)
            if rerun == "true":

                chunk_list = Autosubmit._create_json(as_conf.get_chunk_list())
                if not monitor:
                    job_list.rerun(chunk_list, notransitive)
                else:
                    rerun_list = JobList(expid, BasicConfig, ConfigParserFactory(),
                                         Autosubmit._get_job_list_persistence(expid, as_conf))
                    rerun_list.generate(date_list, as_conf.get_member_list(), as_conf.get_num_chunks(),
                                        as_conf.get_chunk_ini(),
                                        as_conf.load_parameters(), date_format, as_conf.get_retrials(),
                                        as_conf.get_default_job_type(), as_conf.get_wrapper_type(),
                                        as_conf.get_wrapper_jobs(),
                                        new=False, notransitive=notransitive)
                    rerun_list.rerun(chunk_list, notransitive)
                    job_list = Autosubmit.rerun_recovery(
                        expid, job_list, rerun_list, as_conf)
            else:
                job_list.remove_rerun_only_jobs(notransitive)
        except AssertionError as e:
            raise Exception(str(e))
            return None
        except Exception as e:
            print(traceback.format_exc())
            print('Exception: ' + str(e))
            return None
        # print("Load Job List End")
        return job_list

    @staticmethod
    def rerun_recovery(expid, job_list, rerun_list, as_conf):
        """
        Method to check all active jobs. If COMPLETED file is found, job status will be changed to COMPLETED,
        otherwise it will be set to WAITING. It will also update the jobs list.

        :param expid: identifier of the experiment to recover
        :type expid: str
        :param save: If true, recovery saves changes to the jobs list
        :type save: bool
        :param all_jobs: if True, it tries to get completed files for all jobs, not only active.
        :type all_jobs: bool
        :param hide: hides plot window
        :type hide: bool
        """

        hpcarch = as_conf.get_platform()
        submitter = Autosubmit._get_submitter(as_conf)
        submitter.load_platforms(as_conf)
        if submitter.platforms is None:
            return False
        platforms = submitter.platforms

        platforms_to_test = set()
        for job in job_list.get_job_list():
            if job.platform_name is None:
                job.platform_name = hpcarch
            # noinspection PyTypeChecker
            job.platform = platforms[job.platform_name.lower()]
            # noinspection PyTypeChecker
            platforms_to_test.add(platforms[job.platform_name.lower()])

        rerun_names = []

        [rerun_names.append(job.name) for job in rerun_list.get_job_list()]
        jobs_to_recover = [
            i for i in job_list.get_job_list() if i.name not in rerun_names]

        Log.info("Looking for COMPLETED files")
        start = datetime.datetime.now()
        for job in jobs_to_recover:
            if job.platform_name is None:
                job.platform_name = hpcarch
            # noinspection PyTypeChecker
            job.platform = platforms[job.platform_name.lower()]

            if job.platform.get_completed_files(job.name, 0):
                job.status = Status.COMPLETED
            #    Log.info("CHANGED job '{0}' status to COMPLETED".format(job.name))
            # elif job.status != Status.SUSPENDED:
            #    job.status = Status.WAITING
            #    job.fail_count = 0
            #    Log.info("CHANGED job '{0}' status to WAITING".format(job.name))

            job.platform.get_logs_files(expid, job.remote_logs)

        #end = datetime.datetime.now()
        #Log.info("Time spent: '{0}'".format(end - start))
        #Log.info("Updating the jobs list")
        return job_list

    @staticmethod
    def show_lock_warning(expid):
        Log.warning(
            "We have detected that there is another Autosubmit instance using the experiment {0}.", expid)
        Log.warning(
            "We have stopped this execution in order to prevent incoherency errors.")
        Log.warning(
            "Stop other Autosubmit instances that are using the experiment {0} and try it again.", expid)
