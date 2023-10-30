import pytest
import mock

FAKE_EXP_DIR = "./tests/experiments/"

#### FIXTURES ####
@pytest.fixture
def fixture_mock_basic_config():
    with mock.patch("autosubmitconfigparser.config.basicconfig.BasicConfig.read", return_value=None): 
        with mock.patch("autosubmit_api.config.basicConfig.APIBasicConfig.read", return_value=None): 
            with mock.patch("autosubmit_api.config.basicConfig.APIBasicConfig.__init__", return_value=None): 
                with mock.patch("autosubmit_api.config.basicConfig.APIBasicConfig") as mock_config:
                    mock_config.LOCAL_ROOT_DIR = FAKE_EXP_DIR
                    yield mock_config