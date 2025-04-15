from abc import ABC, abstractmethod
from typing import List, Union
from enum import Enum


# Enum for module types
class ModuleLoaderType(str, Enum):
    CONDA = "conda"
    LMOD = "lmod"
    VENV = "venv"
    NO_MODULE = "no_module"


class ModuleLoader(ABC):
    @abstractmethod
    def generate_command(self, command: str, *args, **kwargs) -> str:
        """
        Generates a command based on the provided arguments.
        """


class CondaModuleLoader(ModuleLoader):
    module_loader_type = ModuleLoaderType.CONDA

    def __init__(self, env_name: str):
        self.env_name = env_name.strip()

        # Check if command injection in the env_name
        if any(char in env_name for char in [" ", ";", "&", "|", "`", "$", ">", "<"]):
            raise ValueError("Invalid characters in environment name")

        self.base_command = f"conda run -n {self.env_name} "

    def generate_command(self, command: str, *args, **kwargs):
        """
        Generates a command to run in the specified conda environment.
        """
        full_command = f"{self.base_command}{command} {' '.join(args)}"
        return full_command


class LmodModuleLoader(ModuleLoader):
    module_loader_type = ModuleLoaderType.LMOD

    def __init__(self, modules_list: list):
        self.modules_list = modules_list

        # Check if command injection in the modules_list
        for module in modules_list:
            if any(char in module for char in [" ", ";", "&", "|", "`", "$", ">", "<"]):
                raise ValueError(f"Invalid characters in module name: {module}")

        self.base_command = f"module load {' '.join(self.modules_list)} && "

    def generate_command(self, command: str, *args, **kwargs):
        """
        Generates a command to run with the specified module loaded.
        """
        full_command = f"{self.base_command}{command} {' '.join(args)}"
        return full_command


class VenvModuleLoader(ModuleLoader):
    module_loader_type = ModuleLoaderType.VENV

    def __init__(self, venv_path: str):
        self.venv_path = venv_path
        self.base_command = f"source {self.venv_path}/bin/activate && "

        # Check if command injection in the venv_path
        if any(char in venv_path for char in [" ", ";", "&", "|", "`", "$", ">", "<"]):
            raise ValueError("Invalid characters in virtual environment path")

    def generate_command(self, command: str, *args, **kwargs):
        """
        Generates a command to run in the specified virtual environment.
        """
        full_command = f"{self.base_command}{command} {' '.join(args)}"
        return full_command


class NoModuleLoader(ModuleLoader):
    module_loader_type = ModuleLoaderType.NO_MODULE

    def __init__(self):
        self.base_command = ""

    def generate_command(self, command: str, *args, **kwargs):
        """
        Generates a command without any module loading.
        """
        full_command = f"{self.base_command}{command} {' '.join(args)}"
        return full_command


def get_module_loader(
    module_type: str, module_names: Union[str, List[str], None]
) -> ModuleLoader:
    """
    Factory function to get the appropriate module loader based on the module type.
    """
    if module_type == ModuleLoaderType.CONDA:
        if not isinstance(module_names, str):
            raise ValueError("Conda module name must be a string")
        return CondaModuleLoader(module_names)
    elif module_type == ModuleLoaderType.LMOD:
        if isinstance(module_names, str):
            module_names = [module_names]
        elif not isinstance(module_names, list):
            raise ValueError("Lmod module names must be a list")
        return LmodModuleLoader(module_names)
    elif module_type == ModuleLoaderType.VENV:
        if not isinstance(module_names, str):
            raise ValueError("Venv path must be a string")
        return VenvModuleLoader(module_names)
    elif module_type == ModuleLoaderType.NO_MODULE:
        return NoModuleLoader()
    else:
        raise ValueError(f"Unknown module type: {module_type}")
