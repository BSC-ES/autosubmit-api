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

from os import path
import os
from shutil import rmtree
import subprocess
import shutil

from autosubmitAPIwu.config.basicConfig import BasicConfig
from bscearth.utils.log import Log


class AutosubmitGit:
    """
    Class to handle experiment git repository

    :param expid: experiment identifier
    :type expid: str
    """

    def __init__(self, expid):
        self._expid = expid

    @staticmethod
    def clean_git(as_conf):
        """
        Function to clean space on BasicConfig.LOCAL_ROOT_DIR/git directory.

        :param as_conf: experiment configuration
        :type as_conf: autosubmit.config.AutosubmitConfig
        """
        proj_dir = os.path.join(BasicConfig.LOCAL_ROOT_DIR, as_conf.expid, BasicConfig.LOCAL_PROJ_DIR)
        dirname_path = as_conf.get_project_dir()
        Log.debug("Checking git directory status...")
        if path.isdir(dirname_path):
            if path.isdir(os.path.join(dirname_path, '.git')):
                try:
                    output = subprocess.check_output("cd {0}; git diff-index HEAD --".format(dirname_path),
                                                     shell=True)
                except subprocess.CalledProcessError:
                    Log.error("Failed to retrieve git info...")
                    return False
                if output:
                    Log.info("Changes not committed detected... SKIPPING!")
                    Log.user_warning("Commit needed!")
                    return False
                else:
                    output = subprocess.check_output("cd {0}; git log --branches --not --remotes".format(dirname_path),
                                                     shell=True)
                    if output:
                        Log.info("Changes not pushed detected... SKIPPING!")
                        Log.user_warning("Synchronization needed!")
                        return False
                    else:
                        if not as_conf.set_git_project_commit(as_conf):
                            return False
                        Log.debug("Removing directory")
                        rmtree(proj_dir)
            else:
                Log.debug("Not a git repository... SKIPPING!")
        else:
            Log.debug("Not a directory... SKIPPING!")
        return True
    @staticmethod
    def check_commit(as_conf):
        """
        Function to check uncommited changes

        :param as_conf: experiment configuration
        :type as_conf: autosubmit.config.AutosubmitConfig
        """
        proj_dir = os.path.join(BasicConfig.LOCAL_ROOT_DIR, as_conf.expid, BasicConfig.LOCAL_PROJ_DIR)
        dirname_path = as_conf.get_project_dir()
        if path.isdir(dirname_path):
            Log.debug("Checking git directory status...")
            if path.isdir(os.path.join(dirname_path, '.git')):
                try:
                    output = subprocess.check_output("cd {0}; git diff-index HEAD --".format(dirname_path),
                                                     shell=True)
                except subprocess.CalledProcessError:
                    Log.info("This is not a git experiment")
                    return True

                if output:
                    Log.warning( "There are local changes not commited to Git" )
                    return True
                else:
                    output = subprocess.check_output("cd {0}; git log --branches --not --remotes".format(dirname_path),
                                                     shell=True)
                    if output:
                        Log.warning("Last commits are not pushed to Git")
                        return True
                    else:
                        Log.info("Model Git repository is updated")
                        Log.result("Model Git repository is updated")

        return True
    @staticmethod
    def clone_repository(as_conf, force):
        """
        Clones a specified git repository on the project folder

        :param as_conf: experiment configuration
        :type as_conf: autosubmit.config.AutosubmitConfig
        :param force: if True, it will overwrite any existing clone
        :type force: bool
        :return: True if clone was successful, False otherwise
        """
        if not as_conf.is_valid_git_repository():
            Log.error("There isn't a correct Git configuration. Check that there's an origin and a commit or a branch")
        git_project_origin = as_conf.get_git_project_origin()
        git_project_branch = as_conf.get_git_project_branch()
        git_project_commit = as_conf.get_git_project_commit()
        git_project_submodules = as_conf.get_submodules_list()
        project_destination = as_conf.get_project_destination()
        project_path = os.path.join(BasicConfig.LOCAL_ROOT_DIR, as_conf.expid, BasicConfig.LOCAL_PROJ_DIR)
        git_path = as_conf.get_project_dir()

        if os.path.exists(project_path):
            Log.info("Using project folder: {0}", project_path)
            if not force:
                Log.debug("The project folder exists. SKIPPING...")
                return True
            else:
                shutil.rmtree(project_path)
        os.mkdir(project_path)
        Log.debug("The project folder {0} has been created.", project_path)

        if git_project_commit:
            Log.info("Fetching {0} into {1}", git_project_commit + " " + git_project_origin, project_path)
            try:

                command = "cd {0}; git clone {1} {4}; cd {2}; git checkout {3};".format(project_path,
                                                                                        git_project_origin, git_path,
                                                                                        git_project_commit,
                                                                                        project_destination)
                if git_project_submodules.__len__() <= 0:
                    command += " git submodule update --init --recursive"
                else:

                    command += " cd {0}; git submodule init;".format(project_destination)
                    for submodule in git_project_submodules:
                        command += " git submodule update {0};".format(submodule)
                output = subprocess.check_output(command, shell=True)
            except subprocess.CalledProcessError:
                Log.error("Can not checkout commit {0}: {1}", git_project_commit, output)
                shutil.rmtree(project_path)
                return False

        else:
            Log.info("Cloning {0} into {1}", git_project_branch + " " + git_project_origin, project_path)
            try:
                command = "cd {0}; ".format(project_path)
                if git_project_submodules.__len__() <= 0:
                    command += " git clone --recursive -b {0} {1} {2}".format(git_project_branch, git_project_origin,
                                                                              project_destination)
                else:
                    command += " git clone -b {0} {1} {2};".format(git_project_branch, git_project_origin,
                                                                   project_destination)
                    command += " cd {0}; git submodule init;".format(project_destination)
                    for submodule in git_project_submodules:
                        command += " git submodule update {0};".format(submodule)

                output = subprocess.check_output(command, shell=True)
                Log.debug('{0}:{1}', command, output)
            except subprocess.CalledProcessError:
                Log.error("Can not clone {0} into {1}", git_project_branch + " " + git_project_origin, project_path)
                shutil.rmtree(project_path)
                return False

        return True
