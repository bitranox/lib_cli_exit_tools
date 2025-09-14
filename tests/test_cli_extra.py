from __future__ import annotations
import subprocess
import sys

import pytest

import lib_cli_exit_tools.cli as cli_mod
from lib_cli_exit_tools import lib_cli_exit_tools as tools


def test_main_module_help_runs_ok() -> None:
    proc = subprocess.run(
        [sys.executable, "-m", "lib_cli_exit_tools", "--help"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    assert proc.returncode == 0
    assert "Usage" in proc.stdout or "--help" in proc.stdout


def test_signal_handlers_raise() -> None:
    with pytest.raises(cli_mod.SigIntError):
        cli_mod._sigint_handler(2, None)  # pyright: ignore[reportPrivateUsage]
    with pytest.raises(cli_mod.SigTermError):
        cli_mod._sigterm_handler(15, None)  # pyright: ignore[reportPrivateUsage]


def test_install_signal_handlers_windows_fallback() -> None:
    # Force the Windows branch and ensure SIGBREAK registration failure is handled.
    orig = cli_mod.is_posix
    try:
        cli_mod.is_posix = False
        getattr(cli_mod, "_install_signal_handlers")()  # pyright: ignore[reportPrivateUsage]
    finally:
        cli_mod.is_posix = orig


def test_handle_exception_systemexit_string() -> None:
    handle = getattr(cli_mod, "_handle_exception")
    code = handle(SystemExit("oops"))  # pyright: ignore[reportPrivateUsage]
    assert code == 1


def test_handle_exception_traceback_reraises() -> None:
    handle = getattr(cli_mod, "_handle_exception")
    prev = tools.config.traceback
    tools.config.traceback = True
    try:
        with pytest.raises(RuntimeError):
            handle(RuntimeError("boom"))  # pyright: ignore[reportPrivateUsage]
    finally:
        tools.config.traceback = prev
