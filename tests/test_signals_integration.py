"""Integration tests that exercise real signal delivery against the CLI runner."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import textwrap
import time
from pathlib import Path
from typing import cast

import pytest


_SCRIPT_TEMPLATE = """
from __future__ import annotations

import time

import rich_click as click

from lib_cli_exit_tools import run_cli


@click.command()
def hang() -> None:
    'Spin until a signal arrives so handlers can intercept it.'

    click.echo("ready", err=False)
    while True:  # pragma: no branch - exited via signal handler raising
        time.sleep(0.1)


if __name__ == "__main__":
    raise SystemExit(run_cli(hang))
"""


def _write_harness(tmp_path: Path) -> Path:
    script = tmp_path / "signal_harness.py"
    script.write_text(textwrap.dedent(_SCRIPT_TEMPLATE), encoding="utf-8")
    return script


def _communicate(proc: subprocess.Popen[str]) -> tuple[str, str, int]:
    try:
        stdout, stderr = proc.communicate(timeout=10)
    finally:  # pragma: no cover - defensive cleanup
        if proc.poll() is None:
            proc.kill()
            stdout, stderr = proc.communicate()
    return stdout, stderr, int(proc.returncode or 0)


def _wait_for_ready_marker(proc: subprocess.Popen[str], *, timeout: float = 5.0) -> str:
    deadline = time.monotonic() + timeout
    stdout = proc.stdout
    if stdout is None:
        pytest.fail("signal harness started without stdout pipe")

    while time.monotonic() < deadline:
        if proc.poll() is not None:
            pytest.fail("signal harness exited before readiness marker was emitted")
        line = stdout.readline()
        if "ready" in line:
            return line
    pytest.fail("timed out waiting for readiness marker from signal harness")


ReadyLine = str


@pytest.mark.posix_only
def test_signal_handlers_translate_sigint_exit_code(tmp_path: Path) -> None:
    if os.name != "posix":
        pytest.skip("SIGINT integration test runs only on POSIX platforms")

    script = _write_harness(tmp_path)
    env = os.environ | {"PYTHONUNBUFFERED": "1"}
    proc = subprocess.Popen(
        [sys.executable, str(script)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )

    ready_line = _wait_for_ready_marker(proc)
    proc.send_signal(signal.SIGINT)
    stdout, stderr, returncode = _communicate(proc)

    assert returncode == 130
    assert "ready" in stdout or "ready" in ready_line
    assert "Aborted (SIGINT)." in stderr


@pytest.mark.windows_only
def test_signal_handlers_translate_ctrl_break_exit_code(tmp_path: Path) -> None:
    if not hasattr(signal, "CTRL_BREAK_EVENT"):
        pytest.skip("CTRL_BREAK_EVENT not available on this interpreter")

    script = _write_harness(tmp_path)
    env = os.environ | {"PYTHONUNBUFFERED": "1"}
    proc = subprocess.Popen(
        [sys.executable, str(script)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
    )

    ready_line = _wait_for_ready_marker(proc)
    ctrl_break = cast(int, getattr(signal, "CTRL_BREAK_EVENT"))
    proc.send_signal(ctrl_break)
    stdout, stderr, returncode = _communicate(proc)

    assert returncode == 149
    assert "ready" in stdout or "ready" in ready_line
    assert "SIGBREAK" in stderr
