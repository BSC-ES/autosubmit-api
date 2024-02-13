from typing import List
from flask_apscheduler import APScheduler
from autosubmit_api.bgtasks.bgtask import (
    BackgroundTaskTemplate,
    PopulateDetailsDB,
    PopulateQueueRuntimes,
    PopulateGraph,
)
from autosubmit_api.bgtasks.tasks.job_times_updater import JobTimesUpdater
from autosubmit_api.bgtasks.tasks.status_updater import StatusUpdater
from autosubmit_api.config import (
    DISABLE_BACKGROUND_TASKS,
    RUN_BACKGROUND_TASKS_ON_START,
)

from autosubmit_api.logger import logger, with_log_run_times

REGISTERED_TASKS: List[BackgroundTaskTemplate] = [
    PopulateDetailsDB,
    PopulateQueueRuntimes,
    StatusUpdater,
    JobTimesUpdater,
    PopulateGraph,
]


def create_bind_scheduler(app):
    scheduler = APScheduler()
    scheduler.init_app(app)
    scheduler.start()

    if not DISABLE_BACKGROUND_TASKS:
        for task in REGISTERED_TASKS:
            scheduler.add_job(
                task.id,
                with_log_run_times(logger, task.id, catch_exc=True)(task.run),
                **task.trigger_options
            )

    logger.info(
        "Background tasks: " + str([str(task) for task in scheduler.get_jobs()])
    )

    if RUN_BACKGROUND_TASKS_ON_START:
        logger.info("Starting background tasks on app init before serving...")
        for task in REGISTERED_TASKS:
            scheduler.run_job(task.id)

    return scheduler
