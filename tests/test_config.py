import mock
from autosubmit_api.config.confConfigStrategy import confConfigStrategy
from autosubmit_api.config.basicConfig import APIBasicConfig

from autosubmit_api.config.config_common import AutosubmitConfigResolver
from autosubmit_api.config.ymlConfigStrategy import ymlConfigStrategy 

from tests.common_fixtures import fixture_mock_basic_config


class TestConfigResolver:
    
    def test_simple_init(self, fixture_mock_basic_config):
        with mock.patch("os.path.exists", return_value=True):
            with mock.patch("autosubmit_api.config.confConfigStrategy.confConfigStrategy.__init__", return_value=None):
                resolver = AutosubmitConfigResolver("----", fixture_mock_basic_config, None)
                assert isinstance(resolver._configWrapper, confConfigStrategy)
            
        with mock.patch("os.path.exists", return_value=False):
            with mock.patch("autosubmit_api.config.ymlConfigStrategy.ymlConfigStrategy.__init__", return_value=None):
                resolver = AutosubmitConfigResolver("----", fixture_mock_basic_config, None)
                assert isinstance(resolver._configWrapper, ymlConfigStrategy)


    def test_files_init_conf(self, fixture_mock_basic_config):
        with mock.patch("autosubmit_api.config.confConfigStrategy.confConfigStrategy.__init__", return_value=None):
            resolver = AutosubmitConfigResolver("t314", fixture_mock_basic_config, None)
            assert isinstance(resolver._configWrapper, confConfigStrategy)
        
