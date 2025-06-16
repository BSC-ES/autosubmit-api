from abc import ABC, abstractmethod
from typing import List, Union
from enum import Enum
import os


# Enum for module types
class ModuleLoaderType(str, Enum):
    CONDA = "conda"
    LMOD = "lmod"
    VENV = "venv"
    NO_MODULE = "no_module"


class ModuleLoader(ABC):
    modules: List[str] = []

    @property
    @abstractmethod
    def module_loader_type(self) -> ModuleLoaderType:
        """
        Returns the type of the module loader.
        """

    @abstractmethod
    def generate_command(self, command: str, *args, **kwargs) -> str:
        """
        Generates a command based on the provided arguments.
        """


class CondaModuleLoader(ModuleLoader):
    module_loader_type = ModuleLoaderType.CONDA

    def __init__(self, env_name: Union[str, List[str], None]):
        if isinstance(env_name, str):
            self.modules = [env_name]
        elif (
            isinstance(env_name, list)
            and len(env_name) == 1
            and isinstance(env_name[0], str)
        ):
            self.modules = env_name
        else:
            raise ValueError(
                "Conda environment name must be a string or a list containing a single string"
            )

        self._validate_modules()

    def _validate_modules(self):
        # Inspect command injection in the env_name
        for module in self.modules:
            if any(char in module for char in [" ", ";", "&", "|", "`", "$", ">", "<"]):
                raise ValueError("Invalid characters in environment name")

    @property
    def base_command(self):
        return f"conda run -n {self.modules[0].strip()} "

    def generate_command(self, command: str, *args, **kwargs):
        """
        Generates a command to run in the specified conda environment.
        """
        full_command = f"{self.base_command}{command} {' '.join(args)}"
        return full_command


class LmodModuleLoader(ModuleLoader):
    module_loader_type = ModuleLoaderType.LMOD

    def __init__(self, modules_list: Union[str, List[str], None]):
        if isinstance(modules_list, str):
            self.modules = [modules_list]
        elif isinstance(modules_list, list) and all(
            isinstance(module, str) for module in modules_list
        ):
            self.modules = modules_list
        else:
            raise ValueError(
                "Modules list must be a string or a list containing strings"
            )

        self._validate_modules()

    def _validate_modules(self):
        # Check if command injection in the modules
        for module in self.modules:
            if any(char in module for char in [" ", ";", "&", "|", "`", "$", ">", "<"]):
                raise ValueError(f"Invalid characters in module name: {module}")

    @property
    def base_command(self):
        return f"module load {' '.join(self.modules)} && "

    def generate_command(self, command: str, *args, **kwargs):
        """
        Generates a command to run with the specified module loaded.
        """
        full_command = f"{self.base_command}{command} {' '.join(args)}"
        return full_command


class VenvModuleLoader(ModuleLoader):
    module_loader_type = ModuleLoaderType.VENV

    def __init__(self, venv_path: Union[str, List[str], None]):
        if isinstance(venv_path, str):
            self.modules = [venv_path]
        elif (
            isinstance(venv_path, list)
            and len(venv_path) == 1
            and isinstance(venv_path[0], str)
        ):
            self.modules = venv_path
        else:
            raise ValueError(
                "Venv path must be a string or a list containing a single string"
            )

        self._validate_modules()

    def _validate_modules(self):
        # Inspect comand injection in the venv_path
        for module in self.modules:
            # Check that it's a valid absolute path
            if not os.path.isabs(self.modules[0]):
                raise ValueError("Venv path must be an absolute path")
            # Check if command injection in the venv_path
            if any(char in module for char in [";", "&", "|", "`", "$", ">", "<"]):
                raise ValueError(f"Invalid characters in venv path: {module}")

    @property
    def base_command(self):
        return f"source {self.modules[0].strip()}/bin/activate && "

    def generate_command(self, command: str, *args, **kwargs):
        """
        Generates a command to run in the specified virtual environment.
        """
        full_command = f"{self.base_command}{command} {' '.join(args)}"
        return full_command


class NoModuleLoader(ModuleLoader):
    module_loader_type = ModuleLoaderType.NO_MODULE

    def __init__(self):
        self.modules = []

    @property
    def base_command(self):
        return ""

    def generate_command(self, command: str, *args, **kwargs):
        """
        Generates a command without any module loading.
        """
        full_command = f"{self.base_command}{command} {' '.join(args)}"
        return full_command


def get_module_loader(
    module_loader: str, modules: Union[str, List[str], None]
) -> ModuleLoader:
    """
    Factory function to get the appropriate module loader based on the module type.
    """
    if module_loader == ModuleLoaderType.CONDA:
        return CondaModuleLoader(modules)
    elif module_loader == ModuleLoaderType.LMOD:
        return LmodModuleLoader(modules)
    elif module_loader == ModuleLoaderType.VENV:
        return VenvModuleLoader(modules)
    elif module_loader == ModuleLoaderType.NO_MODULE:
        return NoModuleLoader()
    else:
        raise ValueError(f"Unknown module type: {module_loader}")
