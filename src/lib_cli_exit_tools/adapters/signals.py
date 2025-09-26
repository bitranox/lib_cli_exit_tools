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
        Ensure every CLI managed by this project responds consistently to Ctrl+C
        and termination signals without duplicating configuration.
    Parameters:
        extra: Optional iterable of additional :class:`SignalSpec` records that
            extend the standard platform-aware set.
    Returns:
        Fresh list of :class:`SignalSpec` entries ready for
        :func:`install_signal_handlers` or :func:`handle_cli_exception`.
    """

    specs: List[SignalSpec] = [
        SignalSpec(
            signum=signal.SIGINT,
            exception=SigIntInterrupt,
            message="Aborted (SIGINT).",
            exit_code=130,
        )
    ]

    if hasattr(signal, "SIGTERM"):
        specs.append(
            SignalSpec(
                signum=getattr(signal, "SIGTERM"),
                exception=SigTermInterrupt,
                message="Terminated (SIGTERM/SIGBREAK).",
                exit_code=143,
            )
        )
    if hasattr(signal, "SIGBREAK"):
        specs.append(
            SignalSpec(
                signum=getattr(signal, "SIGBREAK"),
                exception=SigBreakInterrupt,
                message="Terminated (SIGBREAK).",
                exit_code=149,
            )
        )

    if extra is not None:
        specs.extend(extra)

    return specs


def _make_raise_handler(exc_type: type[BaseException]) -> _Handler:
    """Wrap ``exc_type`` in a signal-compatible callable.

    Why:
        ``signal.signal`` expects handlers with a ``(signum, frame)`` signature.
        The returned closure ignores those arguments and raises ``exc_type``
        immediately so higher layers see a structured exception.
    Parameters:
        exc_type: Exception subclass to raise when the signal fires.
    Returns:
        Callable compatible with ``signal.signal`` registration.
    """

    def _handler(signo: int, frame: FrameType | None) -> None:  # pragma: no cover - just raises
        raise exc_type()

    return _handler


def install_signal_handlers(specs: Sequence[SignalSpec] | None = None) -> Callable[[], None]:
    """Install signal handlers that re-raise as structured exceptions.

    Why:
        Centralise signal wiring so CLI entry points can opt in with a single
        call and reliably restore previous handlers afterwards.
    Parameters:
        specs: Iterable of :class:`SignalSpec` entries. When omitted the
            platform-aware defaults from :func:`default_signal_specs` are used.
    Returns:
        Callable that restores the prior handlers. Invoke it in ``finally`` to
        avoid leaking process-wide state into callers or tests.
    """

    active_specs = list(default_signal_specs() if specs is None else specs)
    previous: List[tuple[int, object]] = []

    for spec in active_specs:
        handler = _make_raise_handler(spec.exception)
        try:
            current = signal.getsignal(spec.signum)
            signal.signal(spec.signum, handler)
            previous.append((spec.signum, current))
        except (AttributeError, OSError, RuntimeError):  # pragma: no cover - platform differences
            continue

    def restore() -> None:
        for signum, prior in previous:
            try:
                signal.signal(signum, prior)  # type: ignore[arg-type]
            except Exception:  # pragma: no cover - restore best-effort
                pass

    return restore
