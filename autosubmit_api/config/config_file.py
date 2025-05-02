import os
from ruamel.yaml import YAML

yaml_loader = YAML(typ="safe")

DEFAULT_CONFIG_PATH = "~/.autosubmit_api.yaml"


def read_config_file_path() -> str:
    """
    Get the path to the configuration file.
    """
    config_file = os.environ.get("AS_API_CONFIG_FILE", DEFAULT_CONFIG_PATH)
    return os.path.expanduser(config_file)


def read_config_file() -> dict:
    """
    Read the configuration file and return the loaded data.
    Returns an empty dictionary if the file is not found or cannot be read.
    """
    config_file = read_config_file_path()

    try:
        with open(config_file, "r") as file:
            config_data = yaml_loader.load(file)
    except Exception:
        # If the file is not found or cannot be read, return an empty dictionary
        config_data = {}

    return config_data
