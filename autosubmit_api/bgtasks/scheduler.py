from typing import List
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from autosubmit_api.bgtasks.bgtask import (
    BackgroundTaskTemplate,
    PopulateDetailsDB,
    PopulateGraph,
)
from autosubmit_api.bgtasks.tasks.status_updater import StatusUpdater
from autosubmit_api.config import (
    get_disable_background_tasks,
    get_run_background_tasks_on_start,
)

from autosubmit_api.logger import logger, with_log_run_times

REGISTERED_TASKS: List[BackgroundTaskTemplate] = [
    PopulateDetailsDB,
    StatusUpdater,
    PopulateGraph,
]


def create_scheduler():
    scheduler = BackgroundScheduler()

    if not get_disable_background_tasks():
        for task in REGISTERED_TASKS:
            trigger_options = task.trigger_options.copy()

            job = with_log_run_times(logger, task.id, catch_exc=True)(task.run)
            trigger_type = trigger_options.pop("trigger")
            trigger = None
            if trigger_type == "interval":
                trigger = IntervalTrigger(**trigger_options)
            elif trigger_type == "cron":
                trigger = CronTrigger(**trigger_options)
            else:
                raise ValueError(f"Invalid trigger type {trigger_type}")

            scheduler.add_job(id=task.id, name=task.id, func=job, trigger=trigger)

    logger.info(
        "Background tasks: " + str([str(task) for task in scheduler.get_jobs()])
    )

    if get_run_background_tasks_on_start():
        logger.info("Starting background tasks on app init before serving...")
        for task in REGISTERED_TASKS:
            scheduler.get_job(task.id).func()

    return scheduler
