import sys
import os
import argparse
from typing import List
from gunicorn.app.wsgiapp import WSGIApplication
from autosubmit_api import __version__ as api_version


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
    bind: List[str] = [],
    workers: int = 1,
    log_level: str = "info",
    log_file: str = "-",
    daemon: bool = False,
    threads: int = 1,
    worker_connections: int = 1000,
    max_requests: int = 0,
    max_requests_jitter: int = 0,
    timeout: int = 600,
    graceful_timeout: int = 30,
    keepalive: int = 2,
    **kwargs,
):
    # API options
    if init_bg_tasks:
        os.environ.setdefault("RUN_BACKGROUND_TASKS_ON_START", str(init_bg_tasks))

    if disable_bg_tasks:
        os.environ.setdefault("DISABLE_BACKGROUND_TASKS", str(disable_bg_tasks))

    # Gunicorn options
    options = {  # Options to always have
        "preload_app": True,
        "capture_output": True,
        "timeout": 600,
    }
    if bind and len(bind) > 0:
        options["bind"] = bind
    if workers and workers > 0:
        options["workers"] = workers
    if log_level:
        options["loglevel"] = log_level
    if log_file:
        options["errorlog"] = log_file
    if daemon:
        options["daemon"] = daemon
    if threads and threads > 0:
        options["threads"] = threads
    if worker_connections and worker_connections > 0:
        options["worker_connections"] = worker_connections
    if max_requests and max_requests > 0:
        options["max_requests"] = max_requests
    if max_requests_jitter and max_requests_jitter > 0:
        options["max_requests_jitter"] = max_requests_jitter
    if timeout and timeout > 0:
        options["timeout"] = timeout
    if graceful_timeout and graceful_timeout > 0:
        options["graceful_timeout"] = graceful_timeout
    if keepalive and keepalive > 0:
        options["keepalive"] = keepalive

    g_app = StandaloneApplication("autosubmit_api.app:create_app()", options)
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
    start_parser.add_argument(
        "-b", "--bind", action="append", help="the socket to bind"
    )
    start_parser.add_argument(
        "-w",
        "--workers",
        type=int,
        help="the number of worker processes for handling requests",
    )
    start_parser.add_argument(
        "--log-level", type=str, help="the granularity of Error log outputs"
    )
    start_parser.add_argument(
        "--log-file", type=str, help="The Error log file to write to"
    )
    start_parser.add_argument(
        "-D", "--daemon", action="store_true", help="Daemonize the Gunicorn process"
    )
    start_parser.add_argument(
        "--threads",
        type=int,
        help="The number of worker threads for handling requests.",
    )
    start_parser.add_argument(
        "--worker-connections",
        type=int,
        help="The maximum number of simultaneous clients.",
    )
    start_parser.add_argument(
        "--max-requests",
        type=int,
        help="The maximum number of requests a worker will process before restarting.",
    )
    start_parser.add_argument(
        "--max-requests-jitter",
        type=int,
        help="The maximum jitter to add to the max_requests setting.",
    )
    start_parser.add_argument(
        "--timeout",
        type=int,
        help="Workers silent for more than this many seconds are killed and restarted.",
    )
    start_parser.add_argument(
        "--graceful-timeout", type=int, help="Timeout for graceful workers restart."
    )
    start_parser.add_argument(
        "--keepalive",
        type=int,
        help="The number of seconds to wait for requests on a Keep-Alive connection.",
    )

    args = parser.parse_args()
    print("Starting autosubmit_api with args: " + str(vars(args)))

    if args.command == "start":
        start_app_gunicorn(**vars(args))
    else:
        parser.print_help()
        parser.exit()


if __name__ == "__main__":
    main()
