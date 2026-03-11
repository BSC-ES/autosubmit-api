.. _runnersGuide:

Runners Guide
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
- **LMod Loader**: Loads dependencies using LMod modules.
- **No Loader**: Does not load any dependencies, useful for commands that do not require any specific environment.


How to enable runners? (Runner profiles)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Runners need to use a valid **Runner profile** to run them. These profiles defines a template with the allowed
configuration of the runner to be used when calling a runner.
This gives more flexibility to the users to define different runner profiles with different configurations and
use them when calling a runner without needing to specify all the configuration options every time.

To define them, you need to update the API configuration file (see more in :ref:`configuration`) to include
the ``RUNNER_CONFIGURATION.PROFILES`` section:

.. code-block:: yaml

    RUNNER_CONFIGURATION:
      PROFILES:
        MY_RUNNER_PROFILE_1: #User defined profile name
          RUNNER_TYPE: SSH # LOCAL or SSH
          MODULE_LOADER_TYPE: LMOD # CONDA, VENV, LMOD, NO_MODULE
          MODULES: autosubmit
          SSH:
            HOST: autosubmit.example.com
            PORT: 22
            USER: autosubmit_user
        MY_RUNNER_PROFILE_2_CUSTOM_USERNAME: #User defined profile name with custom username configuration for the SSH runner
          RUNNER_TYPE: SSH # LOCAL or SSH
          MODULE_LOADER_TYPE: LMOD # CONDA, VENV, LMOD, NO_MODULE
          MODULES: autosubmit
          SSH:
            HOST: autosubmit.example.com
            PORT: 22
      SSH_PUBLIC_KEYS:
      - MY-SSH-PUBLIC-KEY-1
      - MY-SSH-PUBLIC-KEY-2 
      ENDPOINTS: # Enable or disable endpoints for the runner.
        SET_JOB_STATUS:
          ENABLED: True # Default is True.
        CREATE_EXPERIMENT:
          ENABLED: True # Default is True.
        RUNNER_RUN:
          ENABLED: True # Default is True.

If any parameter is missing in the runner profile, it can be specified inside the request body when calling the runner,
giving even more flexibility to the users.



Usage examples
^^^^^^^^^^^^^^^^^^^^

Run an experiment using a runner
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    curl -X POST "http://$AS_API_HOST/v4/runners/command/run-experiment" \
        -H "Content-Type: application/json" \
        --data-raw '{
            "expid": "a001",
            "profile_name": "MY_RUNNER_PROFILE_2_CUSTOM_USERNAME",
            "profile_params": {
                "SSH": {
                    "USER": "custom_user"
                }
            }
        }'


Get the status of the runner of an experiment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    curl -X POST "http://$AS_API_HOST/v4/runners/command/get-runner-run-status" \
        -H "Content-Type: application/json" \
        --data-raw '{
            "expid": "a001"
        }'

**JSON response:**

.. code-block:: json

    {
        "expid": "a001",
        "runner_id": 101,
        "runner": "SSH",
        "module_loader": "LMOD",
        "modules": "autosubmit",
        "status": "ACTIVE",
        "pid": 1234567,
        "created": "2026-02-04T15:59:57+01:00",
        "modified": "2026-03-09T14:55:40+01:00"


Stop the runner of an experiment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    curl -X POST "http://$AS_API_HOST/v4/runners/command/stop-experiment" \
        -H "Content-Type: application/json" \
        --data-raw '{
            "expid": "a001"
        }'


Set job status of an experiment using the runner
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    curl -X POST "http://$AS_API_HOST/v4/runners/command/set-job-status" \
        -H "Content-Type: application/json" \
        --data-raw '{
            "expid": "a001",
            "profile_name": "MY_RUNNER_PROFILE_1",
            "command_params": {
                "job_names_list": ["a001_INI", "a001_POST"],
                "final_status": "COMPLETED"
            }
        }'


Create an experiment using the runner
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: bash

    curl -X POST "http://$AS_API_HOST/v4/runners/command/create-experiment" \
        -H "Content-Type: application/json" \
        --data-raw '{
            "profile_name": "MY_RUNNER_PROFILE_2_CUSTOM_USERNAME",
            "profile_params": {
                "SSH": {
                    "USER": "custom_user"
                }
            },
            "command_params": {
                "description": "Experiment created using the runner",
                "hpc": "MN5"
            }
        }'
