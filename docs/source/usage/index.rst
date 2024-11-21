.. _usage:

##############
Usage
##############

Once Autosubmit API is installed, the Command Line Interface can be used:

.. code-block:: bash

    autosubmit_api start

``autosubmit_api start`` will have the following options:
    
  ``--init-bg-tasks``
    run background tasks on start.
  ``--disable-bg-tasks``
    disable background tasks.
  ``-b BIND, --``
    bind BIND  the socket to bind
  ``-w WORKERS, --workers WORKERS``
    the number of worker processes for handling requests
  ``--log-level LOG_LEVEL``
    the granularity of Error log outputs
  ``--log-file LOG_FILE``
    The Error log file to write to
  ``-D, --daemon``
    Daemonize the Gunicorn process
  ``--threads THREADS``
    The number of worker threads for handling requests.
  ``--worker-connections WORKER_CONNECTIONS``
    The maximum number of simultaneous clients.
  ``--max-requests MAX_REQUESTS``
    The maximum number of requests a worker will process before restarting.
  ``--max-requests-jitter MAX_REQUESTS_JITTER``
    The maximum jitter to add to the max_requests setting.
  ``--timeout TIMEOUT``
    Workers silent for more than this many seconds are killed and restarted.
  ``--graceful-timeout GRACEFUL_TIMEOUT``
    Timeout for graceful workers restart.
  ``--keepalive KEEPALIVE``
    The number of seconds to wait for requests on a Keep-Alive connection.


You can go to the API reference here: `Reference <../api.html>`_ (Outdated. Go to :ref:`openapiGuide` to see how to generate the latest API specification)