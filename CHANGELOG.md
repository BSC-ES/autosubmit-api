# CHANGELOG

### Release v4.1.1 - Release date: 2025-06-05

* Fixed major bug that didn't allowed using the graph endpoint

### Release v4.1.0 - Release date: 2025-06-04

* Includes all the changes until v4.1.0b1
* Fixed unintended file creation while querying using SQLite
* Minor bug fixes

### Pre-release v4.1.0b1 - Release date: 2025-05-21

* Added OpenID Connect Authentication support
* Added Sustainability and sum of simulated years metrics in `/v3/performance/{expid}`
* Added `workflow_commit` detail in job and experiment level
* Background tasks can be enabled and change their intervals using a configuration file
* Added an endpoint to retrieve log recovery logs
* Populate details background task have been updated to not remove stored fields when they are not reacheable anymore due to `autosubmit archive`
* User-defined metrics related endpoints have been added

### Pre-release v4.0.1b7 - Release date: 2025-03-12

* **Important:** Added support to new job list pkl format introduced in Autosubmit version 4.1.12
* Updated history module DB interactions through SQLAlchemy
* Patched unintended creation of `structure_{expid}.db` file

### Pre-release v4.0.1b6 - Release date: 2025-01-27

* Updated `autosubmit` dependency to handle correctly the pkl file reader
* Updated docker image
* Updated all DB interactions through SQLAlchemy
* Update date strings in responses to follow ISO 8601, if possible
* Update `/v3/expinfo/{expid}` to get all the data it can get without being blocked by an exception
* Updated CLI to have all the `gunicorn` settings that are not fixed by the API

### Pre-release v4.0.1b5 - Release date: 2024-12-10

* Improved search filters
* Fixed `/v3/login` allowed methods which made the legacy GUI doesn't work
* Fixed graph layout DB handler that kept connections open
* Update dependency `autosubmitconfigparser>=1.0.72` to include relevant changes and bugfixes
* Multiple code and security improvements

### Pre-release v4.0.1b4 - Release date: 2024-10-29

* **Major migration: From Flask to FastAPI**
* `/v3` endpoints are now only available with the `/v3` prefix and not at the root
* Now is possible to check the OpenAPI documentation at `/docs` or `/openapi.json`
* Bearer tokens now are returned with its prefix (e.g. `Bearer <token>`) in all the login endpoints
* Now you can define the root path in which you are serving the API by setting `AS_API_ROOT_PATH` environment variable (see more about how it works [here](https://fastapi.tiangolo.com/advanced/behind-a-proxy/))

### Release v4.0.1 - Release date: 2025-05-19

* Last version before Flask to FastAPI migration
* Includes all the changes until v4.0.1b3

### Pre-release v4.0.1b3 - Release date: 2024-10-01

* Added more CLI options related to gunicorn workers
* Fixed inconsistency in performance metrics calculations due to incorrect chunk size
* Added new endpoints: `/v4/experiments/{expid}/filesystem-config`, `/v4/experiments/{expid}/runs`, and `/v4/experiments/{expid}/runs/{run_id}/config`
* Several general code and devops improvements

### Pre-release v4.0.1b2 - Release date: 2024-07-18

* Fix threshold value on outlier detection algorithm.

### Pre-release v4.0.1b1 - Release date: 2024-07-16 (Yanked)

> Yanked reason: Incorrect threshold value on outlier detection algorithm

* Added not considered jobs (outliers) to the `/v3/performance/<expid>` endpoint
* Changed outlier detection method used to calculate the performance metrics from the standard z-score to the modified z-score using the median absolute deviation (MAD).

### Release v4.0.0 - Release date: 2024-07-11

* Included all the changes from v4.0.0b1 to v4.0.0b9

### Pre-release v4.0.0b9 - Release date: 2024-07-03

* Added support to Python 3.12 and dropped support to Python <= 3.8
* Minor bug fixes

### Pre-release v4.0.0b8 - Release date: 2024-05-28

* Fixed major bug: Prevent accidental `job_data_{expid}.db` file creation

### Pre-release v4.0.0b7 - Release date: 2024-05-14

* Reduced writing time in status updater background task
* Improved documentation
* Removed `listexp` view
* Minor fixes

### Pre-release v4.0.0b6 - Release date: 2024-04-19

* Added filter by autosubmit version in `/v4/experiments`
* Fixed bug that affected wrappers information retrieval
* Fixed some connection file handlers
* Added `/v4/experiments/{expid}/wrappers` endpoint

### Pre-release v4.0.0b5 - Release date: 2024-03-18

* Fixed the graph background task to correctly select the active experiments
* Added support to Github Oauth Apps
* Fixed details background task multiple insert
* Included `/v4/experiments/{expid}` and `/v4/experiments/{expid}/jobs` endpoints

### Pre-release v4.0.0b4 - Release date: 2024-02-23

* The background task that updates the experiment status has been refactored. Now, it keeps the records of all the experiments
* **Major change:** Removed `experiment_times` and `job_times` tables and background tasks related to them
* Fixed bug when performance metrics are not calculated when there is only one SIM job
* Multiple tests have been added
* Testing module configuration fixtures have been fixed
* A lot of dead code has been removed
* Fix the decoding issue on graph coordinates generation on the background task

### Pre-release v4.0.0b3 - Release date: 2024-02-09

* Fix HPC value in the running endpoint
* **Major change:** Updated all route names. Versioning path prefix is included:
    * Previous routes have been moved with the prefix `/v3`
    * New routes have been added with prefix `/v4` to better follow the RESTful convention 
* `pydantic` have been added to improve data validation
* `SQLAlchemy` have been added to improve SQL interaction
* *New* RESTful endpoint `GET /v4/experiments` added for experiment info search that handles pagination
* Fix `running` in `/v3/expinfo/<expid>` endpoint to return the right value
* Add the `--disable-bg-tasks` on the CLI 
* Support new Autosubmit >= 4.1 pickle file
    * Affected endpoints: `/v3/quick/<expid>`, `/v3/expcount/<expid>`, `/v3/summary/<expid>`
    * Affected Background task: `PopulateQueueRuntimes`
* Added chunks to the `/v3/performance/<expid>` endpoint
* Added `/v4/auth/cas/v2/login` endpoint to handle CAS version 2 protocol by giving a whitelisted `service` instead of using the `Referer` header in the request. Also, supports wildcard `*` in the `ALLOWED_CLIENTS` list, and by default gives the API base URL as the `service` for direct authentication.
* Added more tests
* Several dead code was removed

### Pre-release v4.0.0b2 - Release date: 2023-11-20

* Fix bug where API allowed clients aren't read from the autosubmitrc.
* Fixed bug that doesn't show the full config of AS4 in the `/cconfig/<expid>` endpoint.
* Added differences calculation in the `/cconfig/<expid>` endpoint.
* Added job status in the `/quick/<expid>` endpoint.
* Improved security by using protection levels.
* Improved logging and code structure.
* Updated the `Parallelization` metric to consider the platform `PROCESSORS` of the job in the `/performance/<expid>` endpoint.
* Added a Processing Elements (PE) estimation that extends the `Parallelization` logic in the `/performance/<expid>` endpoint which improves the CHSY metric accuracy.
* Fixed bug where jobs don't show the correct platform.
* Fixed error while populating the `experiment_times` table which affected the `/running/` endpoint.


### Pre-release v4.0.0b1 - Release date: 2023-11-02

* Introduced `autosubmit_api` CLI
* Majorly solved compatibility with autosubmit >= 4.0.0
