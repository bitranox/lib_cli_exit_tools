"""Tests for signal handling adapters.

Each test verifies exactly one signal handling behavior:
- Default signal specs include SIGINT
- Platform-specific signals are included when available
- Signal handlers can be installed and restored
- Custom specs can be appended
"""

from __future__ import annotations

import signal

import pytest

from lib_cli_exit_tools.adapters import signals as sig


# =============================================================================
# Default Signal Specs
# =============================================================================


@pytest.mark.os_agnostic
def test_default_specs_include_sigint() -> None:
    specs = sig.default_signal_specs()
    sigint_specs = [s for s in specs if s.signum == signal.SIGINT]
    assert len(sigint_specs) == 1


@pytest.mark.os_agnostic
def test_default_sigint_has_exit_code_130() -> None:
    specs = sig.default_signal_specs()
    sigint_spec = next(s for s in specs if s.signum == signal.SIGINT)
    assert sigint_spec.exit_code == 130


@pytest.mark.os_agnostic
def test_default_sigint_raises_sigint_interrupt() -> None:
    specs = sig.default_signal_specs()
    sigint_spec = next(s for s in specs if s.signum == signal.SIGINT)
    assert sigint_spec.exception is sig.SigIntInterrupt


# =============================================================================
# Custom Signal Specs
# =============================================================================


@pytest.mark.os_agnostic
def test_extra_specs_are_appended_to_defaults() -> None:
    extra = sig.SignalSpec(signum=999, exception=RuntimeError, message="extra", exit_code=2)
    specs = sig.default_signal_specs([extra])
    assert specs[-1] is extra


@pytest.mark.os_agnostic
def test_extra_specs_do_not_replace_defaults() -> None:
    extra = sig.SignalSpec(signum=999, exception=RuntimeError, message="extra", exit_code=2)
    specs = sig.default_signal_specs([extra])
    assert any(s.signum == signal.SIGINT for s in specs)


# =============================================================================
# Spec Resolution
# =============================================================================


@pytest.mark.os_agnostic
def test_choose_specs_with_none_returns_defaults() -> None:
    resolved = sig._choose_specs(None)  # pyright: ignore[reportPrivateUsage]
    assert len(resolved) > 0


@pytest.mark.os_agnostic
def test_choose_specs_with_tuple_returns_list() -> None:
    spec = sig.SignalSpec(signum=1, exception=RuntimeError, message="msg", exit_code=1)
    resolved = sig._choose_specs((spec,))  # pyright: ignore[reportPrivateUsage]
    assert resolved == [spec]


@pytest.mark.os_agnostic
def test_choose_specs_preserves_order() -> None:
    spec1 = sig.SignalSpec(signum=1, exception=RuntimeError, message="first", exit_code=1)
    spec2 = sig.SignalSpec(signum=2, exception=ValueError, message="second", exit_code=2)
    resolved = sig._choose_specs([spec1, spec2])  # pyright: ignore[reportPrivateUsage]
    assert resolved[0] is spec1
    assert resolved[1] is spec2


# =============================================================================
# Platform-Specific Signals (POSIX)
# =============================================================================


@pytest.mark.posix_only
def test_posix_default_specs_include_sigterm() -> None:
    specs = sig.default_signal_specs()
    assert any(s.signum == signal.SIGTERM for s in specs)


@pytest.mark.posix_only
def test_posix_sigterm_has_exit_code_143() -> None:
    specs = sig.default_signal_specs()
    sigterm_spec = next(s for s in specs if s.signum == signal.SIGTERM)
    assert sigterm_spec.exit_code == 143


# =============================================================================
# Platform-Specific Signals (Windows)
# =============================================================================


@pytest.mark.windows_only
def test_windows_default_specs_include_sigbreak() -> None:
    specs = sig.default_signal_specs()
    sigbreak = getattr(signal, "SIGBREAK", None)
    if sigbreak is not None:
        assert any(s.signum == sigbreak for s in specs)


@pytest.mark.windows_only
def test_windows_sigbreak_has_exit_code_149() -> None:
    specs = sig.default_signal_specs()
    sigbreak = getattr(signal, "SIGBREAK", None)
    if sigbreak is not None:
        sigbreak_spec = next(s for s in specs if s.signum == sigbreak)
        assert sigbreak_spec.exit_code == 149


# =============================================================================
# Signal Handler Installation (Real Behavior)
# =============================================================================


@pytest.mark.posix_only
def test_install_handlers_returns_callable_restorer() -> None:
    specs = sig.default_signal_specs()
    restorer = sig.install_signal_handlers(specs)
    assert callable(restorer)
    restorer()  # Clean up


@pytest.mark.posix_only
def test_install_handlers_actually_changes_signal_handlers() -> None:
    specs = sig.default_signal_specs()
    original_handler = signal.getsignal(signal.SIGINT)
    restorer = sig.install_signal_handlers(specs)
    new_handler = signal.getsignal(signal.SIGINT)
    assert new_handler != original_handler
    restorer()


@pytest.mark.posix_only
def test_restore_returns_handlers_to_original_state() -> None:
    specs = sig.default_signal_specs()
    original_handler = signal.getsignal(signal.SIGINT)
    restorer = sig.install_signal_handlers(specs)
    restorer()
    restored_handler = signal.getsignal(signal.SIGINT)
    assert restored_handler == original_handler


# =============================================================================
# Signal Handler Installation (Mocked for OS-Agnostic Coverage)
# =============================================================================


@pytest.mark.posix_only
def test_install_handlers_calls_signal_for_each_spec() -> None:
    # Use real SIGINT which is valid on all platforms
    specs = [sig.SignalSpec(signum=signal.SIGINT, exception=RuntimeError, message="a", exit_code=1)]

    original_handler = signal.getsignal(signal.SIGINT)
    restorer = sig.install_signal_handlers(specs)

    # Handler should have changed
    new_handler = signal.getsignal(signal.SIGINT)
    assert new_handler != original_handler

    restorer()

    # Handler should be restored
    restored_handler = signal.getsignal(signal.SIGINT)
    assert restored_handler == original_handler


@pytest.mark.posix_only
def test_restorer_calls_signal_to_restore_previous_handlers() -> None:
    specs = [sig.SignalSpec(signum=signal.SIGINT, exception=RuntimeError, message="test", exit_code=1)]
    original_handler = signal.getsignal(signal.SIGINT)

    restorer = sig.install_signal_handlers(specs)
    restorer()

    # After restoration, handler should be back to original
    restored_handler = signal.getsignal(signal.SIGINT)
    assert restored_handler == original_handler
