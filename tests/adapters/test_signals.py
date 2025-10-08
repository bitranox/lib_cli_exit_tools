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

    for signum, handler in recorded:
        callable_handler = handler  # mypy/pyright: handler is callable
        with pytest.raises(signals.SigIntInterrupt):
            callable_handler(signum, None)  # type: ignore[misc]


@pytest.mark.skipif(not hasattr(signal, "SIGTERM"), reason="SIGTERM not available on this platform")
def test_default_specs_include_sigterm_when_platform_supports_it() -> None:
    specs = signals.default_signal_specs()
    sigterm = getattr(signal, "SIGTERM")
    assert any(spec.signum == sigterm for spec in specs)


@pytest.mark.skipif(not hasattr(signal, "SIGBREAK"), reason="SIGBREAK only exists on Windows")
def test_default_specs_include_sigbreak_on_windows() -> None:
    specs = signals.default_signal_specs()
    sigbreak = getattr(signal, "SIGBREAK")
    assert any(spec.signum == sigbreak for spec in specs)
