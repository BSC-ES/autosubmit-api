# CHANGELOG

### Pre-release v4.0.0b2 - Release date: TBD

* Fix bug where API allowed clients aren't read from the autosubmitrc.
* Fix bug where `Parallelization` doesn't report the platform `PROCESSORS` in the `/performance/<expid>` endpoint.
* Fixed bug that doesn't show the full config of AS4 in the `/cconfig/<expid>` endpoint.
* Added differences calculation in the `/cconfig/<expid>` endpoint.
* Added job status in the `/quick/<expid>` endpoint.
* Improved security by using protection levels.
* Improved logging and code structure.
* Added Processing Elements (PE) estimation in the `/performance/<expid>` endpoint which improves the CHSY metric accuracy.
* Fixed bug where jobs don't show the correct platform.
* Fixed error while populating the `experiment_times` table which affected the `/running/` endpoint.

### Pre-release v4.0.0b1 - Release date: 2023-11-02

* Introduced `autosubmit_api` CLI
* Majorly solved compatibility with autosubmit >= 4.0.0