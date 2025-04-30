from datetime import timedelta
from typing import Dict
import pytest
from autosubmit_api.bgtasks.scheduler import create_scheduler
from unittest.mock import patch
from apscheduler.util import timedelta_seconds


@pytest.mark.parametrize(
    "bg_tasks_config, expected",
    [
        (
            {},
            {
                "TASK_POPDET": {
                    "ENABLED": True,
                    "INTERVAL": 240,
                },
                "TASK_POPGRPH": {
                    "ENABLED": True,
                    "INTERVAL": 1440,
                },
                "TASK_STTSUPDTR": {
                    "ENABLED": True,
                    "INTERVAL": 5,
                },
            },
        ),
        (
            {
                "TASK_POPDET": {
                    "INTERVAL": 30,
                },
                "TASK_POPGRPH": {
                    "ENABLED": False,
                },
                "TASK_STTSUPDTR": {
                    "ENABLED": True,
                },
            },
            {
                "TASK_POPDET": {
                    "ENABLED": True,
                    "INTERVAL": 30,
                },
                "TASK_POPGRPH": {
                    "ENABLED": False,
                    "INTERVAL": 1440,
                },
                "TASK_STTSUPDTR": {
                    "ENABLED": True,
                    "INTERVAL": 5,
                },
            },
        ),
    ],
)
def test_create_scheduler(bg_tasks_config: Dict, expected: Dict):
    """
    Test the create_scheduler function with different configurations.
    """
    with patch("autosubmit_api.bgtasks.scheduler.read_config_file") as mock_read_config:
        mock_read_config.return_value = {"BACKGROUND_TASKS": bg_tasks_config}

        scheduler = create_scheduler()

        for task_id, task_state in expected.items():
            scheduler_job = scheduler.get_job(task_id)

            if task_state["ENABLED"] is False:
                assert not scheduler_job
            else:
                assert scheduler_job is not None
                assert scheduler_job.id == task_id

                trigger = scheduler.get_job(task_id).trigger

                assert isinstance(trigger.interval, timedelta)
                assert (
                    timedelta_seconds(trigger.interval) == task_state["INTERVAL"] * 60
                )
