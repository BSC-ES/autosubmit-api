import sys
import argparse
from typing import List
from gunicorn.app.wsgiapp import WSGIApplication


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


def start_app_gunicorn(bind: List[str] = [], workers: int = 1, log_level: str = 'info'):
    
    options = {
        "preload_app": True,
        "timeout": 600
    }
    if bind and len(bind) > 0:
        options["bind"] = bind
    if workers and workers > 0:
        options["workers"] = workers
    if log_level:
        options["loglevel"] = log_level

    g_app = StandaloneApplication("autosubmit_api.app:create_app()", options)
    print("gunicorn options: "+str(g_app.options))
    g_app.run()
    

class MyParser(argparse.ArgumentParser):
    def error(self, message):
        sys.stderr.write('error: %s\n' % message)
        self.print_help()
        sys.exit(2)


def main():
    parser = MyParser(prog='Autosubmit API',
                    description='Autosubmit API CLI')
    
    subparsers = parser.add_subparsers(dest='command')

    # start parser
    start_parser = subparsers.add_parser(
        'start', description="start the API")
    
    start_parser.add_argument('-b', '--bind', action='append', 
                                   help='the socket to bind')
    start_parser.add_argument('-w', '--workers', type=int, 
                                   help='the number of worker processes for handling requests')
    start_parser.add_argument('--log-level', type=str, 
                                   help='the granularity of Error log outputs.')
    
    args = parser.parse_args()
    print(args)
    print(args.bind)

    if args.command == "start":
        start_app_gunicorn(args.bind, args.workers, args.log_level)
    else:
        parser.print_help()
        parser.exit()


if __name__ == "__main__":
    main()