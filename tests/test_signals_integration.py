"""Integration tests for real signal delivery against the CLI runner.

Each test verifies exactly one signal handling behavior:
- SIGINT results in exit code 130 (POSIX)
- CTRL_BREAK_EVENT results in exit code 149 (Windows)
- Signal messages are displayed to stderr
"""

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


# =============================================================================
# Test Harness
# =============================================================================


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


# =============================================================================
# POSIX Signal Tests
# =============================================================================


@pytest.mark.posix_only
def test_sigint_returns_exit_code_130(tmp_path: Path) -> None:
    script = _write_harness(tmp_path)
    env = os.environ | {"PYTHONUNBUFFERED": "1"}
    proc = subprocess.Popen(
        [sys.executable, str(script)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )

    _wait_for_ready_marker(proc)
    proc.send_signal(signal.SIGINT)
    _, _, returncode = _communicate(proc)

    assert returncode == 130


@pytest.mark.posix_only
def test_sigint_displays_abort_message(tmp_path: Path) -> None:
    script = _write_harness(tmp_path)
    env = os.environ | {"PYTHONUNBUFFERED": "1"}
    proc = subprocess.Popen(
        [sys.executable, str(script)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )

    _wait_for_ready_marker(proc)
    proc.send_signal(signal.SIGINT)
    _, stderr, _ = _communicate(proc)

    assert "Aborted (SIGINT)." in stderr


@pytest.mark.posix_only
def test_sigint_outputs_ready_marker(tmp_path: Path) -> None:
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
    stdout, _, _ = _communicate(proc)

    assert "ready" in stdout or "ready" in ready_line


# =============================================================================
# Windows Signal Tests
# =============================================================================


@pytest.mark.windows_only
def test_ctrl_break_returns_exit_code_149(tmp_path: Path) -> None:
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

    _wait_for_ready_marker(proc)
    ctrl_break = cast(int, getattr(signal, "CTRL_BREAK_EVENT"))
    proc.send_signal(ctrl_break)
    _, _, returncode = _communicate(proc)

    assert returncode == 149


@pytest.mark.windows_only
def test_ctrl_break_displays_sigbreak_message(tmp_path: Path) -> None:
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

    _wait_for_ready_marker(proc)
    ctrl_break = cast(int, getattr(signal, "CTRL_BREAK_EVENT"))
    proc.send_signal(ctrl_break)
    _, stderr, _ = _communicate(proc)

    assert "SIGBREAK" in stderr


@pytest.mark.windows_only
def test_ctrl_break_outputs_ready_marker(tmp_path: Path) -> None:
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
    stdout, _, _ = _communicate(proc)

    assert "ready" in stdout or "ready" in ready_line
