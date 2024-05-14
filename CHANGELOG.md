# CHANGELOG

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