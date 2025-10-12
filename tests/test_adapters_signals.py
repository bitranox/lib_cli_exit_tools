from __future__ import annotations

import signal

import pytest

from lib_cli_exit_tools.adapters import signals as sig


@pytest.mark.os_agnostic
def test_when_default_signal_specs_is_called_sigint_is_always_present() -> None:
    specs = sig.default_signal_specs()
    assert any(spec.signum == signal.SIGINT and spec.exit_code == 130 for spec in specs)


@pytest.mark.os_agnostic
def test_when_extra_specs_are_supplied_they_are_appended() -> None:
    extra = [sig.SignalSpec(signum=999, exception=RuntimeError, message="extra", exit_code=2)]
    specs = sig.default_signal_specs(extra)
    assert specs[-1].signum == 999


@pytest.mark.os_agnostic
def test_when_choose_specs_receives_none_it_falls_back_to_defaults() -> None:
    resolved = sig._choose_specs(None)  # pyright: ignore[reportPrivateUsage]
    assert resolved


@pytest.mark.os_agnostic
def test_when_choose_specs_receives_values_they_are_returned_as_list() -> None:
    spec = sig.SignalSpec(1, RuntimeError, "msg", 1)
    resolved = sig._choose_specs((spec,))  # pyright: ignore[reportPrivateUsage]
    assert resolved == [spec]


@pytest.mark.posix_only
def test_when_sigterm_exists_it_is_included(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sig.signal, "SIGTERM", signal.SIGTERM, raising=False)
    specs = sig.default_signal_specs()
    assert any(spec.signum == signal.SIGTERM for spec in specs)


@pytest.mark.windows_only
def test_when_sigbreak_exists_it_is_included(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sig.signal, "SIGBREAK", 21, raising=False)
    specs = sig.default_signal_specs()
    assert any(spec.signum == getattr(signal, "SIGBREAK") for spec in specs)


@pytest.mark.os_agnostic
def test_when_install_signal_handlers_is_called_previous_handlers_restore(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[int, object] = {}

    def fake_signal(sig_num: int, handler: object) -> object:
        captured[sig_num] = handler

        def previous(*args: object, **kwargs: object) -> None:
            return None

        return previous

    monkeypatch.setattr(sig.signal, "signal", fake_signal)
    restorer = sig.install_signal_handlers(sig.default_signal_specs())
    assert callable(restorer)
    restorer()
