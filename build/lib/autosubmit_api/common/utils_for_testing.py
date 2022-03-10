from mock import Mock

def get_mock_basic_config():
  basic_config = Mock()
  basic_config.DB_DIR = "/esarchive/autosubmit"
  basic_config.DB_FILE = "ecearth.db"
  basic_config.LOCAL_ROOT_DIR = "autosubmit_api/test_cases/"
  basic_config.STRUCTURES_DIR = "autosubmit_api/test_cases/as_metadata/structures"
  basic_config.GRAPHDATA_DIR = "autosubmit_api/test_cases/as_metadata/graph"
  basic_config.JOBDATA_DIR = "autosubmit_api/test_cases/as_metadata/data"
  basic_config.HISTORICAL_LOG_DIR = "autosubmit_api/test_cases/as_metadata/logs"
  basic_config.LOCAL_TMP_DIR = "tmp"
  return basic_config