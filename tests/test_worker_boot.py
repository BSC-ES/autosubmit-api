"""Regression test: the gunicorn ASGI worker must be able to boot.

``autosubmit_api start`` serves the API through gunicorn using
``uvicorn_worker.UvicornWorker``. uvicorn and uvicorn_worker are version coupled.

This test boots a real server against an ASGI app and asserts it answers with 200.
"""

from __future__ import annotations

import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

import pytest

APP_SOURCE = """\
async def application(scope, receive, send):
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [(b"content-type", b"text/plain")],
        }
    )
    await send({"type": "http.response.body", "body": b"worker-boot-ok"})
"""

EXPECTED_BODY = "worker-boot-ok"
BOOT_TIMEOUT_SECONDS = 30
SHUTDOWN_TIMEOUT_SECONDS = 10
LOG_TAIL_LINES = 15


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _poll(process: subprocess.Popen, url: str, timeout: float) -> str | None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        # If the worker failed to boot, fail fast instead of waiting till timeout
        if process.poll() is not None:
            return None
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                return response.read().decode()
        except OSError:
            time.sleep(0.2)
    return None


def test_uvicorn_worker_boots(tmp_path):
    (tmp_path / "boot_app.py").write_text(APP_SOURCE)

    port = _free_port()
    log_path = tmp_path / "gunicorn.log"

    with log_path.open("w") as log:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "gunicorn",
                "--worker-class",
                "uvicorn_worker.UvicornWorker",
                "--bind",
                f"127.0.0.1:{port}",
                "--chdir",
                tmp_path,
                "--pythonpath",
                tmp_path,
                "boot_app:application",
            ],
            stdout=log,
            stderr=subprocess.STDOUT,
        )

    try:
        body = _poll(process, f"http://127.0.0.1:{port}/", BOOT_TIMEOUT_SECONDS)
    finally:
        process.terminate()
        try:
            process.wait(timeout=SHUTDOWN_TIMEOUT_SECONDS)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=SHUTDOWN_TIMEOUT_SECONDS)

    if body != EXPECTED_BODY:
        log_tail = "\n".join(log_path.read_text().splitlines()[-LOG_TAIL_LINES:])
        pytest.fail(
            "gunicorn with uvicorn_worker.UvicornWorker did not serve a request.\n"
            "uvicorn and uvicorn-worker are version-coupled.\n\n"
            f"server log:\n{log_tail}"
        )
