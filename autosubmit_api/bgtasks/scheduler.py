from typing import List
from flask_apscheduler import APScheduler
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


def create_bind_scheduler(app):
    scheduler = APScheduler()
    scheduler.init_app(app)
    scheduler.start()

    if not get_disable_background_tasks():
        for task in REGISTERED_TASKS:
            scheduler.add_job(
                task.id,
                with_log_run_times(logger, task.id, catch_exc=True)(task.run),
                **task.trigger_options
            )

    logger.info(
        "Background tasks: " + str([str(task) for task in scheduler.get_jobs()])
    )

    if get_run_background_tasks_on_start():
        logger.info("Starting background tasks on app init before serving...")
        for task in REGISTERED_TASKS:
            scheduler.run_job(task.id)

    return scheduler
