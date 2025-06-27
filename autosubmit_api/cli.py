import sys
import os
import argparse
from gunicorn.app.wsgiapp import WSGIApplication
from autosubmit_api import __version__ as api_version
from gunicorn.config import KNOWN_SETTINGS, Setting as GunicornSetting

FIXED_GUNICORN_SETTINGS = [
    "preload_app",
    "capture_output",
    "worker_class",
]


class StandaloneApplication(WSGIApplication):
    def __init__(self, app_uri, options=None):
        self.options = options or {}
        self.app_uri = app_uri
        super().__init__()

    def load_config(self):
        config = {
            key: value
            for key, value in self.options.items()
            if key in self.cfg.settings and value is not None
        }
        for key, value in config.items():
            self.cfg.set(key.lower(), value)


def start_app_gunicorn(
    init_bg_tasks: bool = False,
    disable_bg_tasks: bool = False,
    **kwargs,
):
    # API options
    if init_bg_tasks:
        os.environ.setdefault("RUN_BACKGROUND_TASKS_ON_START", str(init_bg_tasks))

    if disable_bg_tasks:
        os.environ.setdefault("DISABLE_BACKGROUND_TASKS", str(disable_bg_tasks))

    # Gunicorn options
    ## Drop None values in kwargs
    kwargs = {k: v for k, v in kwargs.items() if v is not None}

    options = {  # Options to always have
        "preload_app": True,
        "capture_output": True,
        "worker_class": "uvicorn_worker.UvicornWorker",
        "timeout": 600, # Change the default timeout to 10 minutes
        **kwargs,
    }

    g_app = StandaloneApplication("autosubmit_api.app:app", options)
    print("Starting with gunicorn options: " + str(g_app.options))
    g_app.run()


class MyParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write("error: %s\n" % message)
        self.print_help()
        sys.exit(2)


def main():
    parser = MyParser(prog="Autosubmit API", description="Autosubmit API CLI")

    # main parser
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version="%(prog)s v{version}".format(version=api_version),
    )

    subparsers = parser.add_subparsers(dest="command")

    # start parser
    start_parser = subparsers.add_parser("start", description="start the API")

    # Autosubmit API opts
    start_parser.add_argument(
        "--init-bg-tasks", action="store_true", help="run background tasks on start. "
    )

    start_parser.add_argument(
        "--disable-bg-tasks", action="store_true", help="disable background tasks."
    )

    # Gunicorn args
    for setting in KNOWN_SETTINGS:
        setting: GunicornSetting = setting

        # Skip fixed parameters
        if setting.name in FIXED_GUNICORN_SETTINGS:
            continue

        if isinstance(setting.cli, list):
            arg_options = {
                "dest": setting.name,
            }
            if isinstance(setting.desc, str):
                # Get first part of the description
                description = setting.desc.split("\n")[0]
                arg_options["help"] = f"[gunicorn] {description}"
            if setting.type is not None:
                arg_options["type"] = setting.type
            if setting.action is not None:
                arg_options["action"] = setting.action
            if setting.const is not None:
                arg_options["const"] = setting.const

            start_parser.add_argument(*setting.cli, **arg_options)

    args = parser.parse_args()
    print("Starting autosubmit_api with args: " + str(vars(args)))

    if args.command == "start":
        start_app_gunicorn(**vars(args))
    else:
        parser.print_help()
        parser.exit()


if __name__ == "__main__":
    main()
