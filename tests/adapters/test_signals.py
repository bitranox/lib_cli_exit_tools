"""Signal-adapter tests.

Purpose:
    Confirm that platform signal specifications and handler installation
    behave predictably.
Contents:
    * Defaults, extension hooks, and restoration behaviour of signal specs.
    * Handler factory behaviour.
System Integration:
    Protects the adapter layer contracts used by the application runner.
"""

from __future__ import annotations

import signal

import pytest

from lib_cli_exit_tools.adapters.signals import (
    CliSignalError,
    SigIntInterrupt,
    SignalSpec,
    _make_raise_handler,
    default_signal_specs,
    install_signal_handlers,
)


def test_default_signal_specs_include_sigint() -> None:
    """SIGINT is always present in the default signal specification list."""
    specs = default_signal_specs()
    assert any(spec.signum == signal.SIGINT for spec in specs)


def test_default_signal_specs_can_be_extended() -> None:
    """Callers can append additional signal specifications."""
    extra = SignalSpec(signum=999, exception=SigIntInterrupt, message="custom", exit_code=201)
    combined = default_signal_specs([extra])
    assert extra in combined


def test_install_signal_handlers_restores_previous(monkeypatch: pytest.MonkeyPatch) -> None:
    """Installed handlers record prior state and restore it afterwards."""
    registered: list[tuple[int, object]] = []
    restored: list[tuple[int, object]] = []

    def fake_getsignal(signum: int) -> object:  # pragma: no cover - trivial stub
        return f"prev-{signum}"

    def fake_register(signum: int, handler: object) -> object:
        registered.append((signum, handler))
        return handler

    def fake_restore(signum: int, handler: object) -> None:
        restored.append((signum, handler))

    monkeypatch.setattr("lib_cli_exit_tools.adapters.signals.signal.getsignal", fake_getsignal)
    monkeypatch.setattr("lib_cli_exit_tools.adapters.signals.signal.signal", fake_register)

    specs = [SignalSpec(signum=1, exception=SigIntInterrupt, message="", exit_code=1)]
    restore = install_signal_handlers(specs)

    monkeypatch.setattr("lib_cli_exit_tools.adapters.signals.signal.signal", fake_restore)
    restore()

    assert registered
    assert restored and restored[0][0] == 1


# NOTE: exercising private factory to guarantee handler wiring until a public helper exists
def test_make_raise_handler_raises_configured_exception() -> None:
    """Generated handlers raise the configured signal exception type."""
    handler = _make_raise_handler(SigIntInterrupt)
    with pytest.raises(SigIntInterrupt):
        handler(signal.SIGINT, None)
