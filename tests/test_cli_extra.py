from __future__ import annotations

import subprocess
import sys

import pytest

from lib_cli_exit_tools import config, handle_cli_exception
import lib_cli_exit_tools.cli as cli_mod


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


def test_handle_exception_systemexit_string() -> None:
    code = handle_cli_exception(SystemExit("oops"))
    assert code == 1


def test_handle_exception_traceback_reraises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "traceback", True, raising=False)
    with pytest.raises(RuntimeError):
        handle_cli_exception(RuntimeError("boom"))
