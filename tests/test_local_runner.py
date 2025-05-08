import pytest
import subprocess
from autosubmit_api.runners.local_runner import LocalRunner
from autosubmit_api.runners.module_loaders import NoModuleLoader


@pytest.mark.asyncio
async def test_get_version(fixture_mock_basic_config):
    module_loader = NoModuleLoader()
    runner = LocalRunner(module_loader)

    version = await runner.version()
    assert version is not None
    assert isinstance(version, str)

    autosubmit_version = subprocess.check_output(
        "autosubmit -v", shell=True, text=True
    ).strip()
    assert autosubmit_version == version

