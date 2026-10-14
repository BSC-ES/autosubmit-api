import sys
import os
import argparse
from gunicorn.app.wsgiapp import WSGIApplication
from gunicorn.config import Config as GunicornConfig
from autosubmit_api import __version__ as api_version

# Gunicorn settings the CLI fixes: they are not exposed as options.
# Always handled to gunicorn with these values.
FIXED_GUNICORN_SETTINGS = {
    "preload_app": True,
    "capture_output": True,
    "worker_class": "uvicorn_worker.UvicornWorker",
}


class StandaloneApplication(WSGIApplication):
    def __init__(self, app_uri, options=None):
        self.options = options or {}
        self.app_uri = app_uri
        super().__init__()

    def load_config(self):
        for key, value in self.options.items():
            if key in self.cfg.settings:
                self.cfg.set(key, value)


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
    # Drop None values in kwargs: an omitted CLI option lets gunicorn use its default
    kwargs = {key: value for key, value in kwargs.items() if value is not None}

    options = {
        # Settings the CLI always fixes, not exposed as options
        **FIXED_GUNICORN_SETTINGS,
        # Raise the default timeout to 10 min
        "timeout": 600,
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

    subparsers = parser.add_subparsers(dest="command", required=True)

    # start parser
    start_parser = subparsers.add_parser("start", description="start the API")

    # Autosubmit API opts. The two flags are mutually exclusive.
    bg_task_group = start_parser.add_mutually_exclusive_group()
    bg_task_group.add_argument(
        "--init-bg-tasks", action="store_true", help="run background tasks on start. "
    )
    bg_task_group.add_argument(
        "--disable-bg-tasks", action="store_true", help="disable background tasks."
    )

    # Gunicorn args. Delegate to gunicorn ``Setting.add_option`` instead of manually rebuilding it.
    for name, setting in GunicornConfig().settings.items():
        # Skip fixed parameters
        if name in FIXED_GUNICORN_SETTINGS:
            continue

        setting.add_option(start_parser)

    args = parser.parse_args()
    cli_args = {key: value for key, value in vars(args).items() if key != "command"}
    print("Starting autosubmit_api with args: " + str(cli_args))

    if args.command == "start":
        start_app_gunicorn(**cli_args)


if __name__ == "__main__":
    main()
