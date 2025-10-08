"""Windows signal integration narrated with clarity."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest


pytestmark = [
    pytest.mark.windows_only,
    pytest.mark.skipif(not sys.platform.startswith("win"), reason="These checks require Windows signal semantics"),
    pytest.mark.usefixtures("reset_config_state"),
]


def test_when_sigbreak_arrives_the_child_announces_readiness(tmp_path: Path) -> None:
    ready, _stdout, _stderr, _code = _run_sigbreak_child(tmp_path)
    assert ready == "ready"


def test_when_sigbreak_arrives_the_exit_code_is_one_hundred_forty_nine(tmp_path: Path) -> None:
    _ready, _stdout, _stderr, code = _run_sigbreak_child(tmp_path)
    assert code == 149


def test_when_sigbreak_arrives_the_error_mentions_sigbreak(tmp_path: Path) -> None:
    _ready, _stdout, stderr, _code = _run_sigbreak_child(tmp_path)
    assert "SIGBREAK" in stderr.upper()


def _run_sigbreak_child(tmp_path: Path) -> tuple[str, str, str, int]:
    script = tmp_path / "sigbreak_driver.py"
    script.write_text(
        textwrap.dedent(
            """
            from __future__ import annotations

            import signal
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

    creation_flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    proc = subprocess.Popen(
        [sys.executable, str(script)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        creationflags=creation_flags,
    )

    assert proc.stdout is not None
    try:
        ready_line = proc.stdout.readline().strip()
        ctrl_break = getattr(signal, "CTRL_BREAK_EVENT", None)
        if ctrl_break is None:
            raise pytest.skip("CTRL_BREAK_EVENT unavailable on this platform")
        try:
            proc.send_signal(ctrl_break)
        except ValueError:
            os.kill(proc.pid, ctrl_break)  # type: ignore[arg-type]
        stdout, stderr = proc.communicate(timeout=20)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=5)

    return ready_line, stdout, stderr, proc.returncode
