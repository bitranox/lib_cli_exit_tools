"""POSIX signal integration described in gentle sentences."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


pytestmark = [
    pytest.mark.posix_only,
    pytest.mark.skipif(sys.platform.startswith("win"), reason="POSIX signal semantics differ on Windows"),
    pytest.mark.usefixtures("reset_config_state"),
]


def test_when_sigint_reaches_the_child_it_announces_readiness(tmp_path: Path) -> None:
    ready, _stdout, _stderr, _code = _run_sigint_child(tmp_path)
    assert ready == "ready"


def test_when_sigint_reaches_the_child_the_exit_code_is_one_hundred_thirty(tmp_path: Path) -> None:
    _ready, _stdout, _stderr, code = _run_sigint_child(tmp_path)
    assert code == 130


def test_when_sigint_reaches_the_child_the_error_mentions_sigint(tmp_path: Path) -> None:
    _ready, _stdout, stderr, _code = _run_sigint_child(tmp_path)
    assert "SIGINT" in stderr


def _run_sigint_child(tmp_path: Path) -> tuple[str, str, str, int]:
    script = tmp_path / "sigint_driver.py"
    script.write_text(
        textwrap.dedent(
            """
            from __future__ import annotations

            import sys
            import time

            import click

            from lib_cli_exit_tools.application.runner import run_cli


            @click.command()
            def block_forever() -> None:
                sys.stdout.write("ready\\n")
                sys.stdout.flush()
                while True:
                    time.sleep(0.1)


            if __name__ == "__main__":
                raise SystemExit(run_cli(block_forever))
            """
        ),
        encoding="utf-8",
    )

    proc = subprocess.Popen(
        [sys.executable, str(script)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert proc.stdout is not None
    try:
        ready_line = proc.stdout.readline().strip()
        os.kill(proc.pid, signal.SIGINT)
        stdout, stderr = proc.communicate(timeout=10)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)

    return ready_line, stdout, stderr, proc.returncode
