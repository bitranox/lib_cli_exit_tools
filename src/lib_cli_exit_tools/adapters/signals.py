"""Signal handling adapters for lib_cli_exit_tools.

Purpose:
    Translate operating-system signals into structured Python exceptions and
    provide installation helpers that keep process-wide handlers reversible.
Contents:
    * :class:`CliSignalError` hierarchy capturing supported interrupts.
    * :class:`SignalSpec` dataclass describing signal→exception mappings.
    * :func:`default_signal_specs` building platform-aware defaults.
    * :func:`install_signal_handlers` installing reversible handlers.
System Integration:
    The application runner leverages these helpers to provide consistent exit
    codes across console entry points while allowing tests to inject fakes.
"""

from __future__ import annotations

import signal
from contextlib import suppress
from dataclasses import dataclass
from types import FrameType
from typing import Callable, Iterable, List, Sequence

__all__ = [
    "CliSignalError",
    "SigIntInterrupt",
    "SigTermInterrupt",
    "SigBreakInterrupt",
    "SignalSpec",
    "default_signal_specs",
    "install_signal_handlers",
]


class CliSignalError(RuntimeError):
    """Base class for translating OS signals into structured CLI errors.

    Why:
        Provide a dedicated hierarchy so exit handlers can recognise signal-driven
        interruptions and map them to deterministic exit codes.
    Usage:
        Raised automatically by handlers created via :func:`install_signal_handlers`.
    """


class SigIntInterrupt(CliSignalError):
    """Raised when the process receives ``SIGINT`` (Ctrl+C)."""


class SigTermInterrupt(CliSignalError):
    """Raised when the process receives ``SIGTERM`` (termination request)."""


class SigBreakInterrupt(CliSignalError):
    """Raised when the process receives ``SIGBREAK`` on Windows consoles."""


@dataclass(slots=True)
class SignalSpec:
    """Describe how to translate a low-level signal into CLI-facing behaviour.

    Fields:
        signum: Numeric identifier registered with :mod:`signal`.
        exception: Exception type raised by the generated handler.
        message: User-facing text echoed to stderr when the signal fires.
        exit_code: Numeric code returned to the operating system.
    """

    signum: int
    exception: type[BaseException]
    message: str
    exit_code: int


_Handler = Callable[[int, FrameType | None], None]


def default_signal_specs(extra: Iterable[SignalSpec] | None = None) -> List[SignalSpec]:
    """Build the default list of signal specifications for the host platform.

    Why:
        The application runner needs a predictable baseline of signals to
        install without duplicating platform checks.
    Parameters:
        extra: Optional iterable of additional ``SignalSpec`` instances to
            append for caller-specific behaviour.
    Returns:
        List of signal specifications tailored to the current interpreter.
    """

    specs: List[SignalSpec] = _standard_signal_specs()
    if extra is not None:
        specs.extend(extra)
    return specs


def _make_raise_handler(exc_type: type[BaseException]) -> _Handler:
    """Wrap ``exc_type`` in a signal-compatible callable."""

    def _handler(signo: int, frame: FrameType | None) -> None:  # pragma: no cover - just raises
        raise exc_type()

    return _handler


def install_signal_handlers(specs: Sequence[SignalSpec] | None = None) -> Callable[[], None]:
    """Install signal handlers that re-raise as structured exceptions."""

    active_specs = _choose_specs(specs)
    previous = _register_handlers(active_specs)
    return lambda: _restore_handlers(previous)


def _choose_specs(specs: Sequence[SignalSpec] | None) -> List[SignalSpec]:
    """Return a concrete list of signal specs, defaulting when ``None``."""
    if specs is None:
        return default_signal_specs()
    return list(specs)


def _register_handlers(specs: Sequence[SignalSpec]) -> List[tuple[int, object]]:
    """Register handlers for each ``SignalSpec`` and capture previous handlers."""
    previous: List[tuple[int, object]] = []
    for spec in specs:
        handler = _make_raise_handler(spec.exception)
        _install_handler(spec.signum, handler, previous)
    return previous


def _install_handler(signum_value: int, handler: _Handler, previous: List[tuple[int, object]]) -> None:
    """Install ``handler`` for ``signum_value`` and remember the prior handler."""
    try:
        current = signal.getsignal(signum_value)
        signal.signal(signum_value, handler)
        previous.append((signum_value, current))
    except (AttributeError, OSError, RuntimeError):  # pragma: no cover - platform differences
        return


def _restore_handlers(previous: Sequence[tuple[int, object]]) -> None:
    """Restore previously registered signal handlers."""
    for signum_value, prior in previous:
        with suppress(Exception):  # pragma: no cover - restore best-effort
            signal.signal(signum_value, prior)  # type: ignore[arg-type]


def _standard_signal_specs() -> List[SignalSpec]:
    """Return the base set of signal specifications for all platforms."""
    specs: List[SignalSpec] = [_sigint_spec()]
    specs.extend(_optional_specs())
    return specs


def _sigint_spec() -> SignalSpec:
    """Return the ``SIGINT`` specification shared across all platforms."""
    return SignalSpec(
        signum=signal.SIGINT,
        exception=SigIntInterrupt,
        message="Aborted (SIGINT).",
        exit_code=130,
    )


def _optional_specs() -> Iterable[SignalSpec]:
    """Yield platform-conditional signal specifications."""
    yield from _maybe_sigterm_spec()
    yield from _maybe_sigbreak_spec()


def _maybe_sigterm_spec() -> Iterable[SignalSpec]:
    """Yield the ``SIGTERM`` specification when supported by the host."""
    if hasattr(signal, "SIGTERM"):
        yield SignalSpec(
            signum=getattr(signal, "SIGTERM"),
            exception=SigTermInterrupt,
            message="Terminated (SIGTERM/SIGBREAK).",
            exit_code=143,
        )


def _maybe_sigbreak_spec() -> Iterable[SignalSpec]:
    """Yield the ``SIGBREAK`` specification when running on Windows."""
    if hasattr(signal, "SIGBREAK"):
        yield SignalSpec(
            signum=getattr(signal, "SIGBREAK"),
            exception=SigBreakInterrupt,
            message="Terminated (SIGBREAK).",
            exit_code=149,
        )
