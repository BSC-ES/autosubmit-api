.. _configuration:

##############
Configuration
##############

The Autosubmit API have some configuration options that can be modified by setting their specific environment variable before starting the server:


General variables
**************************

* ``SECRET_KEY``: The secret key to encode the JWT tokens from the Authorization Module.

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