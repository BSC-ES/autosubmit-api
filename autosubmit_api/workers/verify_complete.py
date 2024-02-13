#!/usr/bin/env python
from autosubmit_api.bgtasks.tasks.job_times_updater import JobTimesUpdater


def main():
    JobTimesUpdater.run()


if __name__ == "__main__":
    main()
