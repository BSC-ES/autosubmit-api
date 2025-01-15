import pytest
from pytest import CaptureFixture
import sys
from unittest.mock import patch
from autosubmit_api.cli import main, start_app_gunicorn


def test_main_no_command(capsys: CaptureFixture):
    test_args = ["autosubmit_api"]
    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit):
            main()
    captured = capsys.readouterr()
    assert "usage: Autosubmit API" in captured.out


def test_version(capsys: CaptureFixture):
    test_args = ["autosubmit_api", "--version"]
    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit):
            main()
    captured = capsys.readouterr()
    assert "Autosubmit API v" in captured.out


def test_main_start_command():
    test_args = [
        "autosubmit_api",
        "start",
        "--init-bg-tasks",
        "--workers",
        "2",
        "--disable-bg-tasks",
    ]
    with patch.object(sys, "argv", test_args):
        with patch("autosubmit_api.cli.start_app_gunicorn") as mock_start_app:
            main()
            # Get the args passed to start_app_gunicorn
            args = mock_start_app.call_args[1]
            assert args["init_bg_tasks"] is True
            assert args["workers"] == 2
            assert args["disable_bg_tasks"] is True


def test_start_app_gunicorn():
    with patch("autosubmit_api.cli.StandaloneApplication") as MockApp:
        with patch("os.environ.setdefault") as mock_setenv:
            mock_setenv.return_value = None
            mock_app_instance = MockApp.return_value
            start_app_gunicorn(init_bg_tasks=True, disable_bg_tasks=True, workers=2)
            mock_app_instance.run.assert_called_once()
