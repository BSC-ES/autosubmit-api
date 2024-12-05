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

"""
Module containing functions to manage autosubmit's database.
"""

from autosubmit_api.builders.experiment_history_builder import (
    ExperimentHistoryDirector,
    ExperimentHistoryBuilder,
)
from autosubmit_api.builders.configuration_facade_builder import (
    ConfigurationFacadeDirector,
    AutosubmitConfigurationFacadeBuilder,
)

from autosubmit_api.repositories.join.experiment_join import (
    create_experiment_join_repository,
)


def search_experiment_by_id(query, exp_type=None, only_active=None, owner=None):
    """
    Search experiments using provided data. Main query searches in the view listexp of ec_earth.db.

    :param searchString: string used to match columns in the table
    :type searchString: str
    :param typeExp: Assumes values "test" (only experiments starting with 't') or "experiment" (not experiment starting with 't') or "all" (indistinct).
    :type typeExp: str
    :param onlyActive: Assumes "active" (only active experiments) or "" (indistinct)
    :type onlyActive: str
    :param owner: return only experiment that match the provided owner of the experiment
    :type owner: str
    :return: list of experiments that match the search
    :rtype: JSON
    """
    experiment_join_repo = create_experiment_join_repository()
    query_result, _ = experiment_join_repo.search(
        query=query, exp_type=exp_type, only_active=only_active, owner=owner
    )

    result = list()
    for row in query_result:
        expid = str(row["name"])
        completed = "NA"
        total = "NA"
        submitted = 0
        queuing = 0
        running = 0
        failed = 0
        suspended = 0
        version = "Unknown"
        wrapper = None
        # last_modified_timestamp = None
        last_modified_pkl_datetime = None
        hpc = row["hpc"]
        try:
            autosubmit_config_facade = ConfigurationFacadeDirector(
                AutosubmitConfigurationFacadeBuilder(expid)
            ).build_autosubmit_configuration_facade()
            version = autosubmit_config_facade.get_autosubmit_version()
            wrapper = autosubmit_config_facade.get_wrapper_type()
            last_modified_pkl_datetime = (
                autosubmit_config_facade.get_pkl_last_modified_time_as_datetime()
            )
            hpc = autosubmit_config_facade.get_main_platform()
        except Exception:
            last_modified_pkl_datetime = None
            pass

        total, completed = ("NA", "NA")

        # Getting run data from historical database
        try:
            current_run = (
                ExperimentHistoryDirector(ExperimentHistoryBuilder(expid))
                .build_reader_experiment_history()
                .manager.get_experiment_run_dc_with_max_id()
            )
            if current_run and current_run.total > 0:
                completed = current_run.completed
                total = current_run.total
                submitted = current_run.submitted
                queuing = current_run.queuing
                running = current_run.running
                failed = current_run.failed
                suspended = current_run.suspended
                # last_modified_timestamp = current_run.modified_timestamp
        except Exception as exp:
            print(("Exception on search_experiment_by_id : {}".format(exp)))
            pass

        result.append(
            {
                "id": row["id"],
                "name": row["name"],
                "user": row["user"],
                "description": row["description"],
                "hpc": hpc,
                "status": row["status"],
                "completed": completed,
                "total": total,
                "version": version,
                "wrapper": wrapper,
                "submitted": submitted,
                "queuing": queuing,
                "running": running,
                "failed": failed,
                "suspended": suspended,
                "modified": last_modified_pkl_datetime,
            }
        )
    return {"experiment": result}


def get_current_running_exp():
    """
    Simple query that gets the list of experiments currently running

    :rtype: list of users
    """
    experiment_join_repo = create_experiment_join_repository()
    query_result, _ = experiment_join_repo.search(only_active=True)

    result = list()
    for row in query_result:
        expid = str(row["name"])
        status = "NOT RUNNING"
        completed = "NA"
        total = "NA"
        submitted = 0
        queuing = 0
        running = 0
        failed = 0
        suspended = 0
        user = str(row["user"])
        version = "Unknown"
        wrapper = None
        # last_modified_timestamp = None
        last_modified_pkl_datetime = None
        status = str(row["status"])
        if status == "RUNNING":
            try:
                autosubmit_config_facade = ConfigurationFacadeDirector(
                    AutosubmitConfigurationFacadeBuilder(expid)
                ).build_autosubmit_configuration_facade()
                version = autosubmit_config_facade.get_autosubmit_version()
                wrapper = autosubmit_config_facade.get_wrapper_type()
                last_modified_pkl_datetime = (
                    autosubmit_config_facade.get_pkl_last_modified_time_as_datetime()
                )
                hpc = autosubmit_config_facade.get_main_platform()
            except Exception:
                # last_modified_pkl_datetime = None
                pass

            # Try to retrieve experiment_run data
            try:
                current_run = (
                    ExperimentHistoryDirector(ExperimentHistoryBuilder(expid))
                    .build_reader_experiment_history()
                    .manager.get_experiment_run_dc_with_max_id()
                )
                if current_run and current_run.total > 0:
                    completed = current_run.completed
                    total = current_run.total
                    submitted = current_run.submitted
                    queuing = current_run.queuing
                    running = current_run.running
                    failed = current_run.failed
                    suspended = current_run.suspended
                    # last_modified_timestamp = current_run.modified_timestamp
            except Exception as exp:
                print(("Exception on get_current_running_exp : {}".format(exp)))

            # Append to result
            result.append(
                {
                    "id": row["id"],
                    "name": row["name"],
                    "user": user,
                    "description": row["description"],
                    "hpc": hpc,
                    "status": status,
                    "completed": completed,
                    "total": total,
                    "version": version,
                    "wrapper": wrapper,
                    "submitted": submitted,
                    "queuing": queuing,
                    "running": running,
                    "failed": failed,
                    "suspended": suspended,
                    "modified": last_modified_pkl_datetime,
                }
            )
    return {"experiment": result}
