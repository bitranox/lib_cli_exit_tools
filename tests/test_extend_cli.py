from __future__ import annotations

import signal

import click
import pytest

from lib_cli_exit_tools import (
    SigIntInterrupt,
    SignalSpec,
    config,
    default_signal_specs,
    handle_cli_exception,
    install_signal_handlers,
    run_cli,
)


def test_default_signal_specs_contains_sigint() -> None:
    specs = default_signal_specs()
    assert any(spec.signum == signal.SIGINT for spec in specs)
    sigint_spec = next(spec for spec in specs if spec.exception is SigIntInterrupt)
    assert sigint_spec.exit_code == 130


def test_install_signal_handlers_restores_prior(monkeypatch: pytest.MonkeyPatch) -> None:
    registered: list[tuple[int, object]] = []
    restored: list[tuple[int, object]] = []

    def fake_getsignal(signum: int) -> object:  # pragma: no cover - simple stub
        return f"prev-{signum}"

    def fake_register(signum: int, handler: object) -> object:
        registered.append((signum, handler))
        return handler

    def fake_restore(signum: int, handler: object) -> None:
        restored.append((signum, handler))

        monkeypatch.setattr("lib_cli_exit_tools.lib_cli_exit_tools.signal.getsignal", fake_getsignal)

    monkeypatch.setattr("lib_cli_exit_tools.lib_cli_exit_tools.signal.signal", fake_register)

    specs = [SignalSpec(signum=1, exception=SigIntInterrupt, message="", exit_code=1)]
    restore = install_signal_handlers(specs)

    # Swap signal.signal to observe restoration
    monkeypatch.setattr("lib_cli_exit_tools.lib_cli_exit_tools.signal.signal", fake_restore)
    restore()

    assert registered
    assert restored and restored[0][0] == 1


def test_handle_cli_exception_for_signal(monkeypatch: pytest.MonkeyPatch) -> None:
    messages: list[str] = []

    def echo(msg: str, *, err: bool = False) -> None:
        messages.append(f"{msg}|{err}")

    exit_code = handle_cli_exception(SigIntInterrupt(), echo=echo)
    assert exit_code == 130
    assert messages == ["Aborted (SIGINT).|True"]


def test_handle_cli_exception_generic(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_print() -> None:
        captured["printed"] = True

    def fake_exit(exc: BaseException) -> int:
        captured["exc"] = exc
        return 99

    monkeypatch.setattr("lib_cli_exit_tools.lib_cli_exit_tools.print_exception_message", fake_print)
    monkeypatch.setattr("lib_cli_exit_tools.lib_cli_exit_tools.get_system_exit_code", fake_exit)
    monkeypatch.setattr(config, "traceback", False, raising=False)

    exc = RuntimeError("boom")
    assert handle_cli_exception(exc) == 99
    assert captured == {"printed": True, "exc": exc}


def test_handle_cli_exception_respects_traceback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "traceback", True, raising=False)
    with pytest.raises(RuntimeError):
        handle_cli_exception(RuntimeError("boom"))


def test_run_cli_success(monkeypatch: pytest.MonkeyPatch) -> None:
    @click.command()
    def cli_cmd() -> None:
        click.echo("ok")

    # Prevent actual signal registration during test
    monkeypatch.setattr("lib_cli_exit_tools.lib_cli_exit_tools.install_signal_handlers", lambda specs=None: lambda: None)

    exit_code = run_cli(cli_cmd, argv=["--help"], install_signals=False)
    assert exit_code == 0


def test_run_cli_handles_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    @click.command()
    def cli_cmd() -> None:
        raise click.ClickException("fail")

    monkeypatch.setattr("lib_cli_exit_tools.lib_cli_exit_tools.install_signal_handlers", lambda specs=None: lambda: None)

    exit_code = run_cli(cli_cmd, argv=[], install_signals=False)
    assert exit_code == 1  # ClickException exit_code default 1
