import pytest
from pytest import CaptureFixture
import sys
from unittest.mock import patch
from autosubmit_api.cli import StandaloneApplication, main, start_app_gunicorn


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
    ]
    with patch.object(sys, "argv", test_args):
        with patch("autosubmit_api.cli.start_app_gunicorn") as mock_start_app:
            main()
            # Get the args passed to start_app_gunicorn
            args = mock_start_app.call_args[1]
            assert args["init_bg_tasks"] is True
            assert args["disable_bg_tasks"] is False
            assert args["workers"] == 2


def test_main_start_bg_tasks_mutually_exclusive(capsys: CaptureFixture):
    test_args = [
        "autosubmit_api",
        "start",
        "--init-bg-tasks",
        "--disable-bg-tasks",
    ]
    with patch.object(sys, "argv", test_args):
        with pytest.raises(SystemExit) as exec_info:
            main()
    assert exec_info.value.code == 2
    captured = capsys.readouterr()
    assert "not allowed with argument" in captured.err


def test_start_app_gunicorn():
    with patch("autosubmit_api.cli.StandaloneApplication") as MockApp:
        with patch("os.environ.setdefault") as mock_setenv:
            mock_setenv.return_value = None
            mock_app_instance = MockApp.return_value
            start_app_gunicorn(init_bg_tasks=True, disable_bg_tasks=True, workers=2)
            mock_app_instance.run.assert_called_once()


def test_standalone_application_load_config():
    options = {
        "workers": 3,
        "timeout": 42,
        # Not a gunicorn setting: should be ignored
        "unknown_option": "ignored",
    }

    app = StandaloneApplication("tests.unknown:app", options)

    assert app.cfg.workers == 3
    assert app.cfg.timeout == 42
    assert not hasattr(app.cfg, "unknown_option")
