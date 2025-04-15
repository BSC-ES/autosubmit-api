import pytest
from autosubmit_api.runners.module_loaders import (
    get_module_loader,
    CondaModuleLoader,
    VenvModuleLoader,
    ModuleLoaderType,
    LmodModuleLoader,
    NoModuleLoader,
)


@pytest.mark.parametrize(
    "module_loader_name, modules, expected",
    [
        # Valid cases
        (ModuleLoaderType.CONDA.value, "foo", CondaModuleLoader),
        (ModuleLoaderType.VENV.value, "/foo", VenvModuleLoader),
        (ModuleLoaderType.NO_MODULE.value, None, NoModuleLoader),
        (ModuleLoaderType.LMOD.value, "foo", LmodModuleLoader),
        pytest.param(
            ModuleLoaderType.LMOD.value,
            ["foo", "bar"],
            LmodModuleLoader,
            id="lmod_multiple_modules",
        ),
        # Invalid cases
        ("invalid_loader", "foo", None),
        pytest.param(
            ModuleLoaderType.CONDA.value,
            "foo; rm -rf /",
            None,
            id="conda_command_injection",
        ),
        pytest.param(
            ModuleLoaderType.VENV.value, "~/foo", None, id="venv_not_absolute_path"
        ),
    ],
)
def test_get_module_loader(module_loader_name, modules, expected):
    if expected:
        module_loader = get_module_loader(module_loader_name, modules)
        assert isinstance(module_loader, expected)
    else:
        with pytest.raises(Exception):
            get_module_loader(module_loader_name, modules)


@pytest.mark.parametrize(
    "module_loader_name, modules, expected_cmd",
    [
        (ModuleLoaderType.CONDA.value, "foo", "conda run -n"),
        (ModuleLoaderType.VENV, "/foo", "source /foo/bin/activate"),
        (ModuleLoaderType.LMOD.value, "foo", "module load foo"),
        (ModuleLoaderType.LMOD.value, ["foo", "bar"], "module load foo bar"),
        (ModuleLoaderType.NO_MODULE.value, None, ""),
    ],
)
def test_generate_command(module_loader_name, modules, expected_cmd):
    module_loader = get_module_loader(module_loader_name, modules)

    cmd = module_loader.generate_command("random_cmd")
    assert expected_cmd in cmd
