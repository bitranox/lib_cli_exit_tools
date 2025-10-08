"""The signal adapter is choreographed in these verses."""

from __future__ import annotations

import signal
from typing import Callable
from collections.abc import Sequence

import pytest

import lib_cli_exit_tools.adapters.signals as signals


pytestmark = [
    pytest.mark.os_agnostic,
]


def test_when_default_specs_are_built_sigint_is_always_present() -> None:
    spec_signums = [spec.signum for spec in signals.default_signal_specs()]
    assert signal.SIGINT in spec_signums


def test_when_extra_specs_are_supplied_they_are_added() -> None:
    extra = signals.SignalSpec(signum=999, exception=signals.SigIntInterrupt, message="custom", exit_code=201)
    assert extra in signals.default_signal_specs([extra])


def test_when_signal_handlers_are_installed_previous_handlers_are_recorded(monkeypatch: pytest.MonkeyPatch) -> None:
    recorded, _restore = _install_single_signal(monkeypatch)
    assert recorded and recorded[0][0] == 1


def test_when_signal_handlers_are_restored_the_original_handlers_return(monkeypatch: pytest.MonkeyPatch) -> None:
    recorded, restore = _install_single_signal(monkeypatch)
    restored: list[tuple[int, object]] = []

    def remember_restored(signum_value: int, handler: object) -> None:
        restored.append((signum_value, handler))

    monkeypatch.setattr("lib_cli_exit_tools.adapters.signals.signal.signal", remember_restored)
    restore()
    expected_previous = [(signum, f"prev-{signum}") for signum, _handler in recorded]
    assert restored == expected_previous


def test_when_signal_handlers_fire_the_configured_exception_is_raised(monkeypatch: pytest.MonkeyPatch) -> None:
    recorded, _restore = _install_single_signal(monkeypatch)
    signum, handler = recorded[0]
    with pytest.raises(signals.SigIntInterrupt):
        handler(signum, None)  # type: ignore[misc]


def test_when_signal_handlers_are_installed_without_arguments_the_default_specs_are_used(monkeypatch: pytest.MonkeyPatch) -> None:
    seen_specs: list[list[signals.SignalSpec]] = []

    def fake_register(specs: Sequence[signals.SignalSpec]) -> list[tuple[int, object]]:
        seen_specs.append(list(specs))
        return []

    monkeypatch.setattr(signals, "_register_handlers", fake_register)
    restore = signals.install_signal_handlers()
    restore()
    assert seen_specs and seen_specs[0][0].signum == signal.SIGINT


@pytest.mark.posix_only
@pytest.mark.skipif(not hasattr(signal, "SIGTERM"), reason="SIGTERM is absent on this interpreter")
def test_on_posix_sigterm_is_present_among_default_specs() -> None:
    spec_signums = [spec.signum for spec in signals.default_signal_specs()]
    assert getattr(signal, "SIGTERM") in spec_signums


@pytest.mark.os_agnostic
def test_when_sigterm_is_missing_no_sigterm_spec_is_added(monkeypatch: pytest.MonkeyPatch) -> None:
    original_sigterm = getattr(signal, "SIGTERM", None)
    monkeypatch.delattr(signal, "SIGTERM", raising=False)
    specs = signals.default_signal_specs()
    assert all(spec.exception is not signals.SigTermInterrupt for spec in specs)
    if original_sigterm is not None:
        monkeypatch.setattr(signal, "SIGTERM", original_sigterm, raising=False)


@pytest.mark.windows_only
@pytest.mark.skipif(not hasattr(signal, "SIGBREAK"), reason="SIGBREAK exists only on certain Windows builds")
def test_on_windows_sigbreak_is_present_among_default_specs() -> None:
    spec_signums = [spec.signum for spec in signals.default_signal_specs()]
    assert getattr(signal, "SIGBREAK") in spec_signums


@pytest.mark.windows_only
@pytest.mark.skipif(not hasattr(signal, "SIGBREAK"), reason="SIGBREAK exists only on certain Windows builds")
def test_on_windows_sigbreak_defaults_to_exit_one_hundred_forty_nine() -> None:
    specs = signals.default_signal_specs()
    sigbreak = getattr(signal, "SIGBREAK")
    spec = next(spec for spec in specs if spec.signum == sigbreak)
    assert spec.exit_code == 149


@pytest.mark.os_agnostic
def test_when_sigbreak_exists_temporarily_it_is_included(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(signal, "SIGBREAK", 999, raising=False)
    specs = signals.default_signal_specs()
    assert any(spec.signum == 999 for spec in specs)


def _install_single_signal(monkeypatch: pytest.MonkeyPatch) -> tuple[list[tuple[int, Callable[[int, object | None], None]]], Callable[[], None]]:
    recorded: list[tuple[int, Callable[[int, object | None], None]]] = []

    def fake_getsignal(signum_value: int) -> object:
        return f"prev-{signum_value}"

    def fake_signal(signum_value: int, handler: Callable[[int, object | None], None]) -> None:
        recorded.append((signum_value, handler))

    monkeypatch.setattr("lib_cli_exit_tools.adapters.signals.signal.getsignal", fake_getsignal)
    monkeypatch.setattr("lib_cli_exit_tools.adapters.signals.signal.signal", fake_signal)
    restore = signals.install_signal_handlers([signals.SignalSpec(signum=1, exception=signals.SigIntInterrupt, message="", exit_code=1)])
    return recorded, restore
