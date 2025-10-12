"""Module-entry stories ensuring ``python -m`` matches console scripts."""

from __future__ import annotations

from collections.abc import Callable
import runpy
import sys
from typing import Any, TextIO

import pytest

import lib_cli_exit_tools
from lib_cli_exit_tools import __init__conf__ as metadata
from lib_cli_exit_tools import cli as cli_mod
from lib_cli_exit_tools.application import runner as runner_mod


@pytest.mark.os_agnostic
def test_when_module_entry_returns_zero_it_matches_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    ledger: dict[str, Any] = {}
    monkeypatch.setattr(sys, "argv", ["lib_cli_exit_tools"], raising=False)

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
            {
                "command": command,
                "argv": argv,
                "prog_name": prog_name,
                "install_signals": install_signals,
            }
        )
        return 0

    monkeypatch.setattr("lib_cli_exit_tools.lib_cli_exit_tools.run_cli", fake_run_cli)
    monkeypatch.setattr(runner_mod, "run_cli", fake_run_cli)

    with pytest.raises(SystemExit) as exc:
        runpy.run_module("lib_cli_exit_tools.__main__", run_name="__main__")

    assert exc.value.code == 0
    assert ledger["command"] is cli_mod.cli
    assert ledger["prog_name"] == metadata.shell_command


@pytest.mark.os_agnostic
def test_when_module_entry_encounters_errors_exit_helpers_translate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    signals: list[str] = []
    monkeypatch.setattr(sys, "argv", ["lib_cli_exit_tools", "fail"], raising=False)
    monkeypatch.setattr(lib_cli_exit_tools.config, "traceback", False, raising=False)
    monkeypatch.setattr(lib_cli_exit_tools.config, "traceback_force_color", False, raising=False)

    def fake_print_exception_message(*, trace_back: bool = False, length_limit: int = 500, stream: TextIO | None = None) -> None:
        signals.append(f"printed:{trace_back}:{length_limit}:{stream is not None}")

    def fake_get_system_exit_code(exc: BaseException) -> int:
        signals.append(f"code:{exc}")
        return 88

    monkeypatch.setattr(
        "lib_cli_exit_tools.lib_cli_exit_tools.print_exception_message",
        fake_print_exception_message,
    )
    monkeypatch.setattr(runner_mod, "print_exception_message", fake_print_exception_message)
    monkeypatch.setattr(
        "lib_cli_exit_tools.lib_cli_exit_tools.get_system_exit_code",
        fake_get_system_exit_code,
    )
    monkeypatch.setattr(runner_mod, "get_system_exit_code", fake_get_system_exit_code)

    with pytest.raises(SystemExit) as exc:
        runpy.run_module("lib_cli_exit_tools.__main__", run_name="__main__")

    assert exc.value.code == 88
    assert signals[0] == "printed:False:500:False"
    assert signals[1].startswith("code:")


@pytest.mark.os_agnostic
def test_when_traceback_flag_is_used_via_module_entry_full_traceback_is_rendered(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    strip_ansi: Callable[[str], str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["lib_cli_exit_tools", "--traceback", "fail"], raising=False)
    monkeypatch.setattr(lib_cli_exit_tools.config, "traceback", False, raising=False)
    monkeypatch.setattr(lib_cli_exit_tools.config, "traceback_force_color", False, raising=False)

    with pytest.raises(SystemExit) as exc:
        runpy.run_module("lib_cli_exit_tools.__main__", run_name="__main__")

    plain_err = strip_ansi(capsys.readouterr().err)

    assert exc.value.code != 0
    assert "Traceback (most recent call last)" in plain_err
    assert "RuntimeError: i should fail" in plain_err
    assert "[TRUNCATED" not in plain_err
    assert lib_cli_exit_tools.config.traceback is True


@pytest.mark.os_agnostic
def test_when_module_entry_imports_cli_the_alias_remains_bound() -> None:
    assert cli_mod.cli.name == cli_mod.cli.name


@pytest.mark.os_agnostic
def test_when_facade_exports_are_missing_import_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib

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
def test_when_main_module_is_imported_normally_it_exposes_main_function() -> None:
    import importlib

    module = importlib.import_module("lib_cli_exit_tools.__main__")
    assert callable(module.main)
