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
from contextlib import ExitStack
from dataclasses import dataclass
from types import FrameType
from typing import Callable, Iterable, Sequence

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


def default_signal_specs(extra: Iterable[SignalSpec] | None = None) -> list[SignalSpec]:
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

    specs: list[SignalSpec] = _standard_signal_specs()
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
    stack = _register_handlers(active_specs)
    return stack.close


def _choose_specs(specs: Sequence[SignalSpec] | None) -> list[SignalSpec]:
    """Return a concrete list of signal specs, defaulting when ``None``."""
    if specs is None:
        return default_signal_specs()
    return list(specs)


def _register_handlers(specs: Sequence[SignalSpec]) -> ExitStack:
    """Register handlers for each ``SignalSpec`` and capture previous handlers."""

    stack = ExitStack()
    for spec in specs:
        handler = _make_raise_handler(spec.exception)
        try:
            previous = signal.getsignal(spec.signum)
            signal.signal(spec.signum, handler)
        except (AttributeError, OSError, RuntimeError):  # pragma: no cover - platform differences
            continue
        stack.callback(signal.signal, spec.signum, previous)
    return stack


def _standard_signal_specs() -> list[SignalSpec]:
    """Return the base set of signal specifications for all platforms."""
    specs: list[SignalSpec] = [_sigint_spec()]
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
