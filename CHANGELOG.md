# CHANGELOG

### Pre-release v4.0.0b3 - Release date: TBD

*

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