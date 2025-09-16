"""Core helpers for clean CLI exits, error printing, and Click integration."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import traceback
from dataclasses import dataclass
from types import FrameType
from typing import Any, Callable, List, Literal, Optional, Protocol, Sequence, TextIO

import click

__all__ = [
    "config",
    "get_system_exit_code",
    "print_exception_message",
    "flush_streams",
    "SignalSpec",
    "CliSignalError",
    "SigIntInterrupt",
    "SigTermInterrupt",
    "SigBreakInterrupt",
    "default_signal_specs",
    "install_signal_handlers",
    "handle_cli_exception",
    "run_cli",
]


@dataclass(slots=True)
class _Config:
    """Runtime configuration for library behavior."""

    traceback: bool = False
    exit_code_style: Literal["errno", "sysexits"] = "errno"
    broken_pipe_exit_code: int = 141


config = _Config()


class CliSignalError(RuntimeError):
    """Base class for signal-triggered errors raised by CLI handlers."""


class SigIntInterrupt(CliSignalError):
    """Raised when SIGINT (Ctrl+C) is received."""


class SigTermInterrupt(CliSignalError):
    """Raised when SIGTERM is received."""


class SigBreakInterrupt(CliSignalError):
    """Raised when SIGBREAK (Ctrl+Break on Windows) is received."""


@dataclass(slots=True)
class SignalSpec:
    """Describe how a signal should be translated into an exception and exit code."""

    signum: int
    exception: type[BaseException]
    message: str
    exit_code: int


class _Echo(Protocol):
    def __call__(self, message: str, *, err: bool = ...) -> None: ...  # pragma: no cover - structural typing


_Handler = Callable[[int, FrameType | None], None]


def _default_echo(message: str, *, err: bool = True) -> None:
    click.echo(message, err=err)


def default_signal_specs() -> List[SignalSpec]:
    """Return SignalSpec instances appropriate for the current platform."""

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

    return specs


def _make_raise_handler(exc_type: type[BaseException]) -> _Handler:
    def _handler(signo: int, frame: FrameType | None) -> None:  # pragma: no cover - just raises
        raise exc_type()

    return _handler


def install_signal_handlers(specs: Sequence[SignalSpec] | None = None) -> Callable[[], None]:
    """Install signal handlers that translate signals into Python exceptions.

    Returns a callable that restores the previous handlers when invoked.
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


def handle_cli_exception(
    exc: BaseException,
    *,
    signal_specs: Sequence[SignalSpec] | None = None,
    echo: _Echo | None = None,
) -> int:
    """Convert an exception raised by a CLI into an exit code and side effects."""

    specs = list(default_signal_specs() if signal_specs is None else signal_specs)
    echo_fn = echo if echo is not None else _default_echo

    for spec in specs:
        if isinstance(exc, spec.exception):
            echo_fn(spec.message, err=True)
            return spec.exit_code

    if isinstance(exc, BrokenPipeError):
        return int(config.broken_pipe_exit_code)

    if isinstance(exc, click.ClickException):
        exc.show()
        return exc.exit_code

    if isinstance(exc, SystemExit):
        try:
            return int(exc.code or 0)
        except Exception:
            return 1

    if config.traceback:
        raise exc

    print_exception_message()
    return get_system_exit_code(exc)


def run_cli(
    cli: "click.BaseCommand",
    argv: Sequence[str] | None = None,
    *,
    prog_name: str | None = None,
    signal_specs: Sequence[SignalSpec] | None = None,
    install_signals: bool = True,
) -> int:
    """Run a Click CLI with lib_cli_exit_tools wiring."""

    specs = list(default_signal_specs() if signal_specs is None else signal_specs)
    restore = install_signal_handlers(specs) if install_signals else None

    try:
        cli.main(args=list(argv) if argv is not None else None, standalone_mode=False, prog_name=prog_name)
        return 0
    except BaseException as exc:  # noqa: BLE001 - single funnel for exit codes
        return handle_cli_exception(exc, signal_specs=specs)
    finally:
        if restore is not None:
            restore()
        flush_streams()


def get_system_exit_code(exc: BaseException) -> int:
    """Return an integer exit code appropriate for the current platform."""

    if isinstance(exc, subprocess.CalledProcessError):
        try:
            return int(exc.returncode)
        except Exception:
            return 1

    if isinstance(exc, KeyboardInterrupt):
        return 130

    if hasattr(exc, "winerror"):
        try:
            return int(getattr(exc, "winerror"))  # type: ignore[arg-type]
        except (AttributeError, TypeError, ValueError):
            pass

    if isinstance(exc, BrokenPipeError):
        return int(config.broken_pipe_exit_code)

    if isinstance(exc, OSError) and getattr(exc, "errno", None) is not None:
        try:
            return int(exc.errno)  # type: ignore[arg-type]
        except Exception:
            pass

    posix_exceptions = {
        FileNotFoundError: 2,
        PermissionError: 13,
        FileExistsError: 17,
        IsADirectoryError: 21,
        NotADirectoryError: 20,
        TimeoutError: 110,
        TypeError: 22,
        ValueError: 22,
        RuntimeError: 1,
    }
    windows_exceptions = {
        FileNotFoundError: 2,
        PermissionError: 5,
        FileExistsError: 80,
        IsADirectoryError: 267,
        NotADirectoryError: 267,
        TimeoutError: 1460,
        TypeError: 87,
        ValueError: 87,
        RuntimeError: 1,
    }

    if isinstance(exc, SystemExit):
        code = getattr(exc, "code", None)
        if isinstance(code, int):
            return code
        if code is None:
            return 0
        try:
            return int(str(code))
        except Exception:
            return 1

    if config.exit_code_style == "sysexits":
        return _sysexits_mapping(exc)

    exceptions = posix_exceptions if os.name == "posix" else windows_exceptions
    for exception, code in exceptions.items():
        if isinstance(exc, exception):
            return code

    return 1


def _sysexits_mapping(exc: BaseException) -> int:
    if isinstance(exc, SystemExit):
        try:
            return int(exc.code)  # type: ignore[attr-defined]
        except Exception:
            return 1
    if isinstance(exc, KeyboardInterrupt):
        return 130
    if isinstance(exc, subprocess.CalledProcessError):
        try:
            return int(exc.returncode)
        except Exception:
            return 1
    if isinstance(exc, BrokenPipeError):
        return int(config.broken_pipe_exit_code)
    if isinstance(exc, (TypeError, ValueError)):
        return 64
    if isinstance(exc, FileNotFoundError):
        return 66
    if isinstance(exc, PermissionError):
        return 77
    if isinstance(exc, (OSError, IOError)):
        return 74
    return 1


def print_exception_message(
    trace_back: bool = config.traceback,
    length_limit: int = 500,
    stream: Optional[TextIO] = None,
) -> None:
    """Print the current exception with optional traceback and truncated output."""

    flush_streams()

    if stream is None:
        stream = sys.stderr

    exc_info = sys.exc_info()[1]
    if exc_info is None:
        return

    if trace_back:
        exc_info_msg = "Traceback Information:\n" + traceback.format_exc()
    else:
        exc_info_msg = f"{type(exc_info).__name__}: {exc_info}"

    if len(exc_info_msg) > length_limit:
        exc_info_msg = f"{exc_info_msg[:length_limit]} ...[TRUNCATED at {length_limit} characters]"

    _print_output(exc_info, "stdout", stream)
    _print_output(exc_info, "stderr", stream)

    print(exc_info_msg, file=stream)
    flush_streams()


def _print_output(exc_info: Any, attr: str, stream: Optional[TextIO] = None) -> None:
    if stream is None:
        stream = sys.stderr

    if not hasattr(exc_info, attr):
        return

    output = getattr(exc_info, attr)
    if output is None:
        return

    text: Optional[str] = None
    if isinstance(output, bytes):
        try:
            text = output.decode("utf-8", errors="replace")
        except Exception:
            text = None
    elif isinstance(output, str):
        text = output

    if text is not None:
        print(f"{attr.upper()}: {text}", file=stream)


def flush_streams() -> None:
    try:
        sys.stdout.flush()
    except Exception:  # pragma: no cover - best effort
        pass
    try:
        sys.stderr.flush()
    except Exception:  # pragma: no cover
        pass
