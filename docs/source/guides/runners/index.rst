.. _runnersGuide:

Runners Guide (Alpha)
=======================================

Runners
^^^^^^^^^^^^^^^^^^^^

The Autosubmit API supports running Autosubmit commands through runners.
Runners define the strategy to run Autosubmit commands in a specific environment.

The API currently supports the following runners:

- **Local Runner**: Runs Autosubmit commands on the local machine where the API is running.
- **SSH Runner**: *Coming soon*.


Module Loaders
^^^^^^^^^^^^^^^^^^^^

Module loaders are used to load dependencies and modules required by the Autosubmit commands.

The API supports the following module loaders:

- **Venv Loader**: Loads dependencies from a virtual environment.
- **Conda Loader**: Loads dependencies from a Conda environment.
- **No Loader**: Does not load any dependencies, useful for commands that do not require any specific environment.


How to enable runners?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Runners are disabled by default. To enable them, you need to update the API configuration file (see more in :ref:`configuration`) to include the following section:

.. code-block:: yaml

    RUNNERS:
        LOCAL:
            ENABLED: True # Boolean to enable the local runner. Default is False.
            MODULE_LOADERS:
                CONDA:
                    ENABLED: True # Boolean to enable the Conda loader. Default is False.
                VENV:
                    ENABLED: True # Boolean to enable the venv loader. Default is False.
                    SAFE_ROOT_PATH: / # Optional, specify a safe root path for the venv loader
                NO_MODULE:
                    ENABLED: True # Boolean to enable the no module loader. Default is False.



Usage examples
^^^^^^^^^^^^^^^^^^^^


Get the details of a runner
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    RUNNER = local
    MODULE_LOADER = conda # or venv, no_module
    MODULE = my_conda_env

    curl -X GET "http://$AS_API_HOST/v4alpha/runner-detail?runner=$RUNNER&module_loader=$MODULE_LOADER&modules=$MODULE"

**JSON response:**

.. code-block:: json

    {
        "runner": "local",
        "module_loader": "conda",
        "modules": [
            "my_conda_env"
        ],
        "version": "4.1.13"
    }

Run an experiment using a runner
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    EXPID = a001
    RUNNER = local
    MODULE_LOADER = conda # or venv, no_module
    MODULE = my_conda_env

    curl -X POST "http://$AS_API_HOST/v4alpha/experiments/$EXPID/run-experiment" \
        -H "Content-Type: application/json" \
        --data-raw '{
            "runner": "local",
            "module_loader": "conda",
            "modules": "my_conda_env"
        }'


Get the status of the runner of an experiment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    EXPID = a001

    curl -X GET "http://$AS_API_HOST/v4alpha/experiments/$EXPID/get-runner-status"


**JSON response:**

.. code-block:: json

    {
        "expid": "a001",
        "runner_id": 4,
        "runner": "local",
        "module_loader": "conda",
        "modules": "my_conda_env",
        "status": "ACTIVE",
        "pid": 1816960,
        "created": "2025-06-16T14:03:31+02:00",
        "modified": "2025-06-16T14:03:31+02:00"
    }


Stop the runner of an experiment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    EXPID = a001

    curl -X POST "http://$AS_API_HOST/v4alpha/experiments/$EXPID/stop-experiment"