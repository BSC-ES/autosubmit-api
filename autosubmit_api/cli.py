import sys
import argparse
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


def start_app_gunicorn(port: int, workers: int):
    
    options = {
        "preload_app": True,
        "timeout": 600
    }
    if port:
        options["bind"] = f"127.0.0.1:{port}"
    if workers:
        options["workers"] = workers

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
    
    start_parser.add_argument('-p', '--port', type=int, 
                                   help='the port to serve')
    start_parser.add_argument('-w', '--workers', type=int, 
                                   help='number of workers to use')
    
    args = parser.parse_args()

    if args.command == "start":
        start_app_gunicorn(args.port, args.workers)
    else:
        parser.print_help()
        parser.exit()


if __name__ == "__main__":
    main()