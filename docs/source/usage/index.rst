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


You can go to the API reference here: `Reference <../api.html>`_