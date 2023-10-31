import pytest
from autosubmitconfigparser.config.basicconfig import BasicConfig
from autosubmit_api.config.basicConfig import APIBasicConfig
from tests.custom_utils import custom_return_value

FAKE_EXP_DIR = "./tests/experiments/"

#### FIXTURES ####
@pytest.fixture
def fixture_mock_basic_config(monkeypatch: pytest.MonkeyPatch):
    # Patch APIBasicConfig parent BasicConfig
    monkeypatch.setattr(BasicConfig, "read", custom_return_value(None))
    monkeypatch.setattr(BasicConfig, "LOCAL_ROOT_DIR", FAKE_EXP_DIR)
    yield APIBasicConfig