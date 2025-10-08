"""Signal stories told without suspense."""

from __future__ import annotations

import signal

import pytest

import lib_cli_exit_tools.adapters.signals as signals


def test_default_specs_always_include_sigint() -> None:
    specs = signals.default_signal_specs()
    assert any(spec.signum == signal.SIGINT for spec in specs)


def test_default_specs_accept_extra_entries() -> None:
    extra = signals.SignalSpec(signum=999, exception=signals.SigIntInterrupt, message="custom", exit_code=201)
    specs = signals.default_signal_specs([extra])
    assert extra in specs


def test_install_signal_handlers_records_previous_handlers(monkeypatch: pytest.MonkeyPatch) -> None:
    recorded: list[tuple[int, object]] = []

    def fake_getsignal(signum: int) -> object:
        return f"prev-{signum}"

    def fake_register(signum: int, handler: object) -> None:
        recorded.append((signum, handler))

    monkeypatch.setattr("lib_cli_exit_tools.adapters.signals.signal.getsignal", fake_getsignal)
    monkeypatch.setattr("lib_cli_exit_tools.adapters.signals.signal.signal", fake_register)

    restore = signals.install_signal_handlers([signals.SignalSpec(signum=1, exception=signals.SigIntInterrupt, message="", exit_code=1)])

    assert recorded

    restored: list[tuple[int, object]] = []

    def fake_restore(signum: int, handler: object) -> None:
        restored.append((signum, handler))

    monkeypatch.setattr("lib_cli_exit_tools.adapters.signals.signal.signal", fake_restore)
    restore()

    assert restored == [(signum, f"prev-{signum}") for signum, _ in recorded]


def test_make_raise_handler_raises_the_given_exception() -> None:
    handler = signals._make_raise_handler(signals.SigIntInterrupt)  # type: ignore[attr-defined]
    with pytest.raises(signals.SigIntInterrupt):
        handler(signal.SIGINT, None)
