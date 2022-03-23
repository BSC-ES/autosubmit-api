from inspect import trace
import os
import textwrap
import traceback
import autosubmit_api.experiment.common_db_requests as DbRequests
from autosubmit_api.builders.configuration_facade_builder import ConfigurationFacadeDirector, AutosubmitConfigurationFacadeBuilder
from autosubmit_api.config.basicConfig import BasicConfig
from ConfigParser import ParsingError
from collections import namedtuple
from sqlite3 import Connection
from typing import List, Dict, Any, Tuple

ExperimentDetails = namedtuple("ExperimentDetails", ['owner', 'created', 'model', 'branch', 'hpc'])
Experiment = namedtuple("Experiment", ['id', 'name'])

# BasicConfig.read()


class DetailsProcessor:
  def __init__(self, basic_config):
    # type: (BasicConfig) -> None
    self.basic_config = basic_config
    self.main_database_path = os.path.join(self.basic_config.LOCAL_ROOT_DIR, self.basic_config.DB_FILE)
    
  def _get_new_connection(self):
    # type: () -> Connection
    return DbRequests.create_connection(self.main_database_path)

  def process(self):
    details = self._get_all_details()
    self._create_table_if_not_exists()
    self._clean_table()  
    return self._insert_many_into_details_table(details)

  def _get_experiments(self):
    # type: () -> List[Experiment]
    experiments = []      
    conn = self._get_new_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, name from experiment where autosubmit_version IS NOT NULL")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    for row in rows:
        experiments.append(Experiment(int(row[0]), str(row[1])))  
    return experiments
    
  def _get_details_data_from_experiment(self, expid):
    # type: (str) -> ExperimentDetails
    autosubmit_config = ConfigurationFacadeDirector(AutosubmitConfigurationFacadeBuilder(expid)).build_autosubmit_configuration_facade(self.basic_config)
    return ExperimentDetails(autosubmit_config.get_owner_name(), autosubmit_config.get_experiment_created_time_as_datetime(), autosubmit_config.get_model(), autosubmit_config.get_branch(), autosubmit_config.get_main_platform())

  def _get_all_details(self):
    # type: () -> List[Tuple[Any]]
    experiments = self._get_experiments()
    result = []
    exp_ids = set()
    for experiment in experiments:
      try:
        detail = self._get_details_data_from_experiment(experiment.name)
        if experiment.id not in exp_ids:
          result.append((
          experiment.id,
          detail.owner,
          detail.created,
          detail.model,
          detail.branch,
          detail.hpc
          ))
          exp_ids.add(experiment.id)
      except IOError:
        # Ignore file not found errors
        pass
      except ParsingError:
        # Ignore parsing errors
        pass
      except Exception as exp:                
        print("Error on experiment {}: {}".format(experiment.name, str(exp)))
    return result

  def _insert_many_into_details_table(self, values):
    # type: (List[Tuple[Any, Any, Any, Any, Any, Any]]) -> int    
    statement = "INSERT INTO details (exp_id, user, created, model, branch, hpc) values (?, ?, ?, ?, ?, ?)"
    conn  = self._get_new_connection()
    cur = conn.cursor()
    cur.executemany(statement, values)
    conn.commit()
    cur.close()
    conn.close()
    return cur.rowcount

  def _create_table_if_not_exists(self):
    # type: () -> None    
    create_table_query = textwrap.dedent(
      '''CREATE TABLE
      IF NOT EXISTS details (
      exp_id integer PRIMARY KEY,
      user text NOT NULL,
      created text NOT NULL,
      model text NOT NULL,
      branch text NOT NULL,
      hpc text NOT NULL,
      FOREIGN KEY (exp_id) REFERENCES experiment (id)
      );''')
    conn = self._get_new_connection()
    DbRequests.create_table(conn, create_table_query)
  
  def _clean_table(self):
    # type: () -> None    
    statement = "DELETE FROM details"
    conn = self._get_new_connection()
    cur = conn.cursor()
    cur.execute(statement)
    cur.execute("VACUUM")
    cur.close()
    conn.commit()
    conn.close()









