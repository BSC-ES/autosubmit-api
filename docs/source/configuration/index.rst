.. _configuration:

##############
Configuration
##############

The Autosubmit API have some configuration options that can be modified by setting their specific environment variable before starting the server:


General variables
**************************

* ``SECRET_KEY``: The secret key to encode the JWT tokens from the Authorization Module.
* ``AS_API_ROOT_PATH``: The root path of the API. This is useful if you are serving it with a reverse proxy. Default is an empty string. 
* ``AS_API_CONFIG_FILE``: The path to the API configuration file. Default is ``~/.autosubmit_api.yaml``. See the `API configuration file`_ section for more information.

.. important:: Always set ``SECRET_KEY`` when deploying the API on production.


Authentication variables
**************************

* ``PROTECTION_LEVEL``:  Default ``ALL``. Possible values ``ALL``, ``WRITEONLY``, ``NONE``.
  
  * If set to ``ALL``, all the endpoints will be protected by needing a valid token inside the **Authorization** header of the request.
  * If set to ``WRITEONLY``, only a subset of the endpoints will be protected.
  * If set to ``NONE``, none of the endpoints will be protected.

* ``CAS_SERVER_URL``: CAS Protocol server base URL to request a ticket and verify it. Used for **/v4** endpoints. ``CAS_LOGIN_URL`` and ``CAS_VERIFY_URL`` can be empty if this variable is set (the API will append the protocol URL subpaths).
* ``CAS_LOGIN_URL``: CAS Protocol URL to request a ticket. Used for **/v3** endpoints.
* ``CAS_VERIFY_URL``: CAS Protocol URL to verify a given ticket. Used for **/v3** endpoints.
* ``GITHUB_OAUTH_CLIENT_ID``: Client ID of the Github Oauth app.
* ``GITHUB_OAUTH_CLIENT_SECRET``: Secret key of the Github Oauth app.
* ``GITHUB_OAUTH_WHITELIST_ORGANIZATION``: Used to use authorization based on the membership of a Github organization.
* ``GITHUB_OAUTH_WHITELIST_TEAM``: Used to use authorization based on the membership of a Github team in an organization. ``GITHUB_OAUTH_WHITELIST_ORGANIZATION`` is required
* ``OIDC_TOKEN_URL``: OpenID Connect token URL.
* ``OIDC_CLIENT_ID``: OpenID Connect client ID.
* ``OIDC_CLIENT_SECRET``: OpenID Connect client secret.
* ``OIDC_USERNAME_SOURCE``: Method to use to get the username. Possible values: ``userinfo`` and ``id_token``. Default is ``id_token``.
* ``OIDC_USERNAME_CLAIM``: Claim to use as username. e.g. ``preferred_username``. Default is ``sub``.
* ``OIDC_USERINFO_URL``: OpenID Connect userinfo URL.


API configuration file
**************************

The API configuration file is a YAML file that contains more structured configuration options. It can be used to set the following options:

.. code-block:: yaml

    BACKGROUND_TASKS: # Background tasks configuration
      TASK_STTSUPDTR: # Status update task
        ENABLED: True # Enable or disable the task. Default is True.
        INTERVAL: 5 # in minutes. Default is 5 minutes.
      TASK_POPDET: # Populate details database task
        ENABLED: True # Enable or disable the task. Default is True.
        INTERVAL: 240 # in minutes. Default is 240 minutes.
      TASK_POPGRPH: # Populate graph layout cache task
        ENABLED: True # Enable or disable the task. Default is True.
        INTERVAL: 1440 # in minutes. Default is 1440 minutes.
      