import pytest

from autosubmit_api.runners.module_loaders import CondaModuleLoader, VenvModuleLoader
from autosubmit_api.runners.ssh_runner import SSHRunner

@pytest.mark.asyncio
@pytest.mark.ssh_runner
@pytest.mark.parametrize("module_loader", [
    CondaModuleLoader(env_name="autosubmit_env"),
    VenvModuleLoader(venv_path="/opt/autosubmit_venv"),
])
async def test_ssh_runner(fixture_mock_basic_config, module_loader):
    runner = SSHRunner(
        module_loader=module_loader,
        ssh_host="localhost",
        ssh_user="root",
        ssh_port=2222,
    )

    version = await runner.version()

    assert version == "4.1.14"