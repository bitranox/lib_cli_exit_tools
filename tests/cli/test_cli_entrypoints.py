"""CLI integration tests.

Purpose:
    Demonstrate that console scripts and `python -m` execution share the same
    output and configuration behaviour.
Contents:
    * Smoke tests for CLI commands and error messaging.
    * Rich-click configuration regression checks.
System Integration:
    Covers the package surface most visible to end users.
"""

from __future__ import annotations

import subprocess
import sys

from _pytest.capture import CaptureFixture

import pytest

from lib_cli_exit_tools import run_cli
from lib_cli_exit_tools.cli import cli as root_cli, main


def test_cli_info_command_outputs_metadata(capsys: CaptureFixture[str]) -> None:
    """The info subcommand surfaces package metadata without stderr output."""
    exit_code = main(["info"])
    out, err = capsys.readouterr()
    assert exit_code == 0
    assert "Info for lib_cli_exit_tools" in out
    assert err == ""


def test_cli_unknown_option_returns_usage_error(capsys: CaptureFixture[str]) -> None:
    """Unknown options trigger Click usage errors with exit code 2."""
    exit_code = main(["--does-not-exist"])
    _out, err = capsys.readouterr()
    assert exit_code == 2
    assert "No such option" in err


def test_module_execution_matches_console_script(capsys: CaptureFixture[str]) -> None:
    """Console script and module execution yield identical results."""
    exit_main = main(["info"])
    out_main, err_main = capsys.readouterr()

    exit_runner = run_cli(root_cli, argv=["info"], install_signals=False)
    out_runner, err_runner = capsys.readouterr()

    assert exit_main == exit_runner == 0
    assert out_main == out_runner
    assert err_main == err_runner


def test_python_m_invocation_provides_help() -> None:
    """Running `python -m lib_cli_exit_tools --help` returns usage text."""
    proc = subprocess.run(
        [sys.executable, "-m", "lib_cli_exit_tools", "--help"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "Usage" in proc.stdout or "--help" in proc.stdout


def test_main_invokes_rich_click_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    """CLI execution lazily configures rich-click output per stream capability."""

    class _FakeStream:
        encoding = "cp1252"

        def isatty(self) -> bool:
            return False

    import lib_cli_exit_tools.cli as cli_mod

    original_force = cli_mod.rich_config.FORCE_TERMINAL
    original_color = cli_mod.rich_config.COLOR_SYSTEM

    monkeypatch.setattr(cli_mod.click, "get_text_stream", lambda _: _FakeStream())
    try:
        cli_mod.rich_config.FORCE_TERMINAL = True
        cli_mod.rich_config.COLOR_SYSTEM = "standard"

        exit_code = cli_mod.main(["info"])
        assert exit_code == 0
        assert cli_mod.rich_config.FORCE_TERMINAL is False
        assert cli_mod.rich_config.COLOR_SYSTEM is None
    finally:
        cli_mod.rich_config.FORCE_TERMINAL = original_force
        cli_mod.rich_config.COLOR_SYSTEM = original_color


def test_python_m_invocation_smoke() -> None:
    """`python -m lib_cli_exit_tools info` completes successfully."""
    import subprocess, sys

    proc = subprocess.run([sys.executable, "-m", "lib_cli_exit_tools", "info"], capture_output=True, text=True, check=False)
    assert proc.returncode == 0
    assert "Info for lib_cli_exit_tools" in proc.stdout
