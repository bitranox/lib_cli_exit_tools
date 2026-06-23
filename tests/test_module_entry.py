"""Tests for module entry point behavior.

Each test verifies exactly one module entry behavior:
- Module invocation via python -m
- Exit code propagation
- Error handling through facade helpers
- Traceback rendering with --traceback flag
- PUBLIC_API export validation
"""

from __future__ import annotations

import importlib
import runpy
import sys
from collections.abc import Callable
from typing import Any, TextIO

import pytest

import lib_cli_exit_tools
from lib_cli_exit_tools import __init__conf__ as metadata
from lib_cli_exit_tools import cli as cli_mod
from lib_cli_exit_tools.application import runner as runner_mod


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def fake_run_cli_recording(monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    """Install a fake run_cli that records its arguments."""
    ledger: dict[str, Any] = {}

    def fake_run_cli(
        command: Any,
        *,
        argv: list[str] | None = None,
        prog_name: str | None = None,
        signal_specs: Any = None,
        install_signals: bool = True,
        exception_handler: Any = None,
        signal_installer: Any = None,
    ) -> int:
        ledger.update(
            command=command,
            argv=argv,
            prog_name=prog_name,
            install_signals=install_signals,
        )
        return 0

    monkeypatch.setattr("lib_cli_exit_tools.lib_cli_exit_tools.run_cli", fake_run_cli)
    monkeypatch.setattr(runner_mod, "run_cli", fake_run_cli)
    return ledger


# =============================================================================
# Module Entry - Successful Execution
# =============================================================================


@pytest.mark.os_agnostic
def test_module_entry_exits_with_zero_on_success(
    monkeypatch: pytest.MonkeyPatch,
    fake_run_cli_recording: dict[str, Any],
) -> None:
    monkeypatch.setattr(sys, "argv", ["lib_cli_exit_tools"], raising=False)

    with pytest.raises(SystemExit) as exc:
        runpy.run_module("lib_cli_exit_tools.__main__", run_name="__main__")

    assert exc.value.code == 0


@pytest.mark.os_agnostic
def test_module_entry_passes_cli_command(
    monkeypatch: pytest.MonkeyPatch,
    fake_run_cli_recording: dict[str, Any],
) -> None:
    monkeypatch.setattr(sys, "argv", ["lib_cli_exit_tools"], raising=False)

    with pytest.raises(SystemExit):
        runpy.run_module("lib_cli_exit_tools.__main__", run_name="__main__")

    assert fake_run_cli_recording["command"] is cli_mod.cli


@pytest.mark.os_agnostic
def test_module_entry_passes_prog_name_from_metadata(
    monkeypatch: pytest.MonkeyPatch,
    fake_run_cli_recording: dict[str, Any],
) -> None:
    monkeypatch.setattr(sys, "argv", ["lib_cli_exit_tools"], raising=False)

    with pytest.raises(SystemExit):
        runpy.run_module("lib_cli_exit_tools.__main__", run_name="__main__")

    assert fake_run_cli_recording["prog_name"] == metadata.shell_command


# =============================================================================
# Module Entry - Error Handling
# =============================================================================


@pytest.mark.os_agnostic
def test_module_entry_uses_exit_code_translator(monkeypatch: pytest.MonkeyPatch) -> None:
    signals: list[str] = []
    monkeypatch.setattr(sys, "argv", ["lib_cli_exit_tools", "fail"], raising=False)
    monkeypatch.setattr(lib_cli_exit_tools.config, "traceback", False, raising=False)
    monkeypatch.setattr(lib_cli_exit_tools.config, "traceback_force_color", False, raising=False)

    def fake_print_exception_message(*, trace_back: bool = False, length_limit: int = 500, stream: TextIO | None = None) -> None:
        signals.append("printed")

    def fake_get_system_exit_code(exc: BaseException) -> int:
        signals.append("translated")
        return 88

    monkeypatch.setattr("lib_cli_exit_tools.lib_cli_exit_tools.print_exception_message", fake_print_exception_message)
    monkeypatch.setattr(runner_mod, "print_exception_message", fake_print_exception_message)
    monkeypatch.setattr("lib_cli_exit_tools.lib_cli_exit_tools.get_system_exit_code", fake_get_system_exit_code)
    monkeypatch.setattr(runner_mod, "get_system_exit_code", fake_get_system_exit_code)

    with pytest.raises(SystemExit) as exc:
        runpy.run_module("lib_cli_exit_tools.__main__", run_name="__main__")

    assert exc.value.code == 88
    assert "translated" in signals


@pytest.mark.os_agnostic
def test_module_entry_prints_exception_message_on_error(monkeypatch: pytest.MonkeyPatch) -> None:
    printed: list[bool] = []
    monkeypatch.setattr(sys, "argv", ["lib_cli_exit_tools", "fail"], raising=False)
    monkeypatch.setattr(lib_cli_exit_tools.config, "traceback", False, raising=False)
    monkeypatch.setattr(lib_cli_exit_tools.config, "traceback_force_color", False, raising=False)

    def fake_print_exception_message(*, trace_back: bool = False, length_limit: int = 500, stream: TextIO | None = None) -> None:
        printed.append(trace_back)

    def fake_get_system_exit_code(exc: BaseException) -> int:
        return 1

    monkeypatch.setattr("lib_cli_exit_tools.lib_cli_exit_tools.print_exception_message", fake_print_exception_message)
    monkeypatch.setattr(runner_mod, "print_exception_message", fake_print_exception_message)
    monkeypatch.setattr("lib_cli_exit_tools.lib_cli_exit_tools.get_system_exit_code", fake_get_system_exit_code)
    monkeypatch.setattr(runner_mod, "get_system_exit_code", fake_get_system_exit_code)

    with pytest.raises(SystemExit):
        runpy.run_module("lib_cli_exit_tools.__main__", run_name="__main__")

    assert printed == [False]


# =============================================================================
# Traceback Flag via Module Entry
# =============================================================================


@pytest.mark.os_agnostic
def test_traceback_flag_via_module_entry_shows_traceback(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    strip_ansi: Callable[[str], str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["lib_cli_exit_tools", "--traceback", "fail"], raising=False)
    monkeypatch.setattr(lib_cli_exit_tools.config, "traceback", False, raising=False)
    monkeypatch.setattr(lib_cli_exit_tools.config, "traceback_force_color", False, raising=False)

    with pytest.raises(SystemExit):
        runpy.run_module("lib_cli_exit_tools.__main__", run_name="__main__")

    plain_err = strip_ansi(capsys.readouterr().err)

    assert "Traceback (most recent call last)" in plain_err


@pytest.mark.os_agnostic
def test_traceback_flag_via_module_entry_shows_exception_details(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    strip_ansi: Callable[[str], str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["lib_cli_exit_tools", "--traceback", "fail"], raising=False)
    monkeypatch.setattr(lib_cli_exit_tools.config, "traceback", False, raising=False)
    monkeypatch.setattr(lib_cli_exit_tools.config, "traceback_force_color", False, raising=False)

    with pytest.raises(SystemExit):
        runpy.run_module("lib_cli_exit_tools.__main__", run_name="__main__")

    plain_err = strip_ansi(capsys.readouterr().err)

    assert "RuntimeError: i should fail" in plain_err


@pytest.mark.os_agnostic
def test_traceback_flag_via_module_entry_exits_nonzero(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["lib_cli_exit_tools", "--traceback", "fail"], raising=False)
    monkeypatch.setattr(lib_cli_exit_tools.config, "traceback", False, raising=False)
    monkeypatch.setattr(lib_cli_exit_tools.config, "traceback_force_color", False, raising=False)

    with pytest.raises(SystemExit) as exc:
        runpy.run_module("lib_cli_exit_tools.__main__", run_name="__main__")

    assert exc.value.code != 0


@pytest.mark.os_agnostic
def test_traceback_flag_enables_config_traceback(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["lib_cli_exit_tools", "--traceback", "fail"], raising=False)
    monkeypatch.setattr(lib_cli_exit_tools.config, "traceback", False, raising=False)
    monkeypatch.setattr(lib_cli_exit_tools.config, "traceback_force_color", False, raising=False)

    with pytest.raises(SystemExit):
        runpy.run_module("lib_cli_exit_tools.__main__", run_name="__main__")

    assert lib_cli_exit_tools.config.traceback is True


# =============================================================================
# CLI Alias Binding
# =============================================================================


@pytest.mark.os_agnostic
def test_cli_alias_remains_bound_after_import() -> None:
    assert cli_mod.cli.name == cli_mod.cli.name


# =============================================================================
# PUBLIC_API Export Validation
# =============================================================================


@pytest.mark.os_agnostic
def test_missing_facade_export_raises_import_error(monkeypatch: pytest.MonkeyPatch) -> None:
    package = importlib.import_module("lib_cli_exit_tools")
    facade = importlib.import_module("lib_cli_exit_tools.lib_cli_exit_tools")
    original = facade.PUBLIC_API
    try:
        monkeypatch.setattr(facade, "PUBLIC_API", original + ("absent",), raising=False)
        with pytest.raises(ImportError, match=r"missing \['absent'\]"):
            importlib.reload(package)
    finally:
        monkeypatch.setattr(facade, "PUBLIC_API", original, raising=False)
        importlib.reload(package)


@pytest.mark.os_agnostic
def test_main_module_exposes_main_function() -> None:
    module = importlib.import_module("lib_cli_exit_tools.__main__")
    assert callable(module.main)
