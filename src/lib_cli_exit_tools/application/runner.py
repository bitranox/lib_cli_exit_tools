"""Application orchestration for lib_cli_exit_tools CLIs.

Purpose:
    Provide reusable helpers that execute Click commands with shared signal
    handling, traceback rendering, and exit-code translation across entry
    points.
Contents:
    * :func:`handle_cli_exception` – maps exceptions to exit codes and renders
      diagnostics.
    * :func:`run_cli` – orchestrates signal installation, command execution, and
      cleanup.
    * Supporting utilities for Rich-based output and stream management.
System Integration:
    Imported by the package root and CLI adapters to keep behaviour consistent
    between console scripts and ``python -m`` execution while remaining
    testable via dependency injection.
"""

from __future__ import annotations

import contextlib
import sys
from typing import Callable, Optional, Protocol, Sequence, TextIO

import rich_click as click
from rich_click import rich_click as rich_config
from rich.console import Console
from rich.text import Text
from rich.traceback import Traceback

from ..adapters.signals import (
    CliSignalError,
    SigBreakInterrupt,
    SigIntInterrupt,
    SigTermInterrupt,
    SignalSpec,
    default_signal_specs,
    install_signal_handlers,
)
from ..core.configuration import config
from ..core.exit_codes import get_system_exit_code

__all__ = [
    "handle_cli_exception",
    "print_exception_message",
    "flush_streams",
    "run_cli",
]


class _Echo(Protocol):
    """Protocol describing the echo interface expected by error handlers."""

    def __call__(self, message: str, *, err: bool = ...) -> None: ...  # pragma: no cover - structural typing


def _default_echo(message: str, *, err: bool = True) -> None:
    """Proxy to :func:`click.echo` used when callers do not supply one.

    Why:
        Keep :func:`handle_cli_exception` testable without importing Click in the
        call site while still providing a sensible default stderr writer.
    Parameters:
        message: Text to emit.
        err: When ``True`` (default) the message targets stderr; Click routes to
            stdout otherwise.
    Side Effects:
        Writes a newline-terminated string via Click's IO abstraction.
    """

    click.echo(message, err=err)


def flush_streams() -> None:
    """Best-effort flush of ``stdout`` and ``stderr`` to avoid buffered loss.

    Why:
        When Click raises an exception it can leave output buffered. Flushing
        ensures diagnostics reach the terminal before the process exits.
    Side Effects:
        Invokes ``flush`` on standard streams and suppresses unexpected errors
        from non-standard stream objects.
    """

    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        flush = getattr(stream, "flush", None)
        if callable(flush):  # pragma: no branch - simple guard
            try:
                flush()
            except Exception:  # pragma: no cover - best effort
                pass


def _build_console(
    stream: Optional[TextIO] = None,
    *,
    force_terminal: bool | None = None,
    color_system: str | None = None,
) -> Console:
    """Construct a Rich console aligned with the active rich-click settings.

    Why:
        Centralises console creation so traceback rendering and error summaries
        inherit the same colour/terminal configuration as Click's help output.
    Parameters:
        stream: Target stream; defaults to ``sys.stderr`` when omitted.
        force_terminal: Explicit override for Rich's terminal detection.
        color_system: Explicit Rich colour system override; ``None`` reuses the
            global setting from rich-click.
    Returns:
        Configured :class:`Console` instance ready for rendering tracebacks.
    """

    target_stream = stream or sys.stderr
    force_flag = rich_config.FORCE_TERMINAL if force_terminal is None else force_terminal
    color_flag = rich_config.COLOR_SYSTEM if color_system is None else color_system
    return Console(
        file=target_stream,
        force_terminal=force_flag,
        color_system=color_flag,
        soft_wrap=True,
    )


def _print_output(exc_info: object, attr: str, stream: Optional[TextIO] = None) -> None:
    """Print captured subprocess output stored on an exception.

    Why:
        :class:`subprocess.CalledProcessError` stores ``stdout``/``stderr`` on the
        exception instance. Surfacing that context aids debugging CLI wrappers.
    Parameters:
        exc_info: Exception potentially carrying process output attributes.
        attr: Attribute name to inspect (``"stdout"`` or ``"stderr"``).
        stream: Target stream; defaults to ``sys.stderr``.
    Side Effects:
        Writes decoded output prefixed with the attribute name when available.
    """

    target = stream or sys.stderr

    if not hasattr(exc_info, attr):
        return

    output = getattr(exc_info, attr)
    if output is None:
        return

    text: Optional[str]
    if isinstance(output, bytes):
        try:
            text = output.decode("utf-8", errors="replace")
        except Exception:
            text = None
    elif isinstance(output, str):
        text = output
    else:
        text = None

    if text:
        print(f"{attr.upper()}: {text}", file=target)


def print_exception_message(
    trace_back: bool = config.traceback,
    length_limit: int = 500,
    stream: Optional[TextIO] = None,
) -> None:
    """Emit the active exception message and optional traceback to ``stream``.

    Why:
        Offer a single choke point for rendering user-facing diagnostics so the
        CLI can toggle between terse and verbose output via configuration.
    Parameters:
        trace_back: When ``True`` render a Rich traceback; otherwise print a
            truncated red summary.
        length_limit: Maximum length of the summary string when tracebacks are
            suppressed.
        stream: Target text stream; defaults to ``sys.stderr``.
    Side Effects:
        Flushes standard streams, inspects ``sys.exc_info()``, and prints via
        Rich using the active colour configuration.
    """

    flush_streams()

    target_stream = stream or sys.stderr
    exc_info = sys.exc_info()[1]
    if exc_info is None:
        return

    _print_output(exc_info, "stdout", target_stream)
    _print_output(exc_info, "stderr", target_stream)

    force_terminal = True if config.traceback_force_color else None
    color_system = "auto" if config.traceback_force_color else None
    console = _build_console(
        target_stream,
        force_terminal=force_terminal,
        color_system=color_system,
    )

    if trace_back:
        tb_renderable = Traceback.from_exception(
            type(exc_info),
            exc_info,
            exc_info.__traceback__,
            show_locals=False,
        )
        console.print(tb_renderable)
    else:
        message = Text(
            f"{type(exc_info).__name__}: {exc_info}",
            style="bold red",
        )
        if len(message.plain) > length_limit:
            truncated = f"{message.plain[:length_limit]} ... [TRUNCATED at {length_limit} characters]"
            message = Text(truncated, style="bold red")
        console.print(message)

    console.file.flush()
    flush_streams()


def handle_cli_exception(
    exc: BaseException,
    *,
    signal_specs: Sequence[SignalSpec] | None = None,
    echo: _Echo | None = None,
) -> int:
    """Convert an exception raised by a CLI into a deterministic exit code.

    Why:
        Keep Click command bodies small by funnelling all error handling,
        signalling, and traceback logic through one reusable helper.
    Parameters:
        exc: Exception propagated by the command execution.
        signal_specs: Optional list of :class:`SignalSpec` definitions.
        echo: Optional callable to replace :func:`click.echo` for message output.
    Returns:
        Integer exit code suitable for :func:`sys.exit`.
    Side Effects:
        May write to stderr, invoke :func:`print_exception_message`, and render
        rich tracebacks when requested.
    """

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
        with contextlib.suppress(Exception):
            return int(exc.code or 0)
        return 1

    if config.traceback:
        print_exception_message(trace_back=True)
        return get_system_exit_code(exc)

    print_exception_message()
    return get_system_exit_code(exc)


def run_cli(
    cli: "click.BaseCommand",
    argv: Sequence[str] | None = None,
    *,
    prog_name: str | None = None,
    signal_specs: Sequence[SignalSpec] | None = None,
    install_signals: bool = True,
    exception_handler: Callable[[BaseException], int] | None = None,
    signal_installer: Callable[[Sequence[SignalSpec] | None], Callable[[], None]] | None = None,
) -> int:
    """Execute a Click command with shared signal/error handling installed.

    Why:
        Guarantee consistent behaviour between console scripts and ``python -m``
        while allowing advanced callers to customise exception handling or
        signal installation.
    Parameters:
        cli: Click command or group to execute.
        argv: Optional list of arguments (excluding program name).
        prog_name: Override for Click's displayed program name.
        signal_specs: Optional signal configuration overriding the defaults.
        install_signals: When ``False`` skips handler registration (useful for
            hosts that already manage signals).
        exception_handler: Callable returning an exit code when exceptions
            occur; defaults to :func:`handle_cli_exception`.
        signal_installer: Callable responsible for installing signal handlers;
            defaults to :func:`install_signal_handlers`.
    Returns:
        Integer exit code suitable for :func:`sys.exit`.
    Side Effects:
        May install process-wide signal handlers, execute the Click command, and
        flush IO streams.
    """

    specs = list(default_signal_specs() if signal_specs is None else signal_specs)

    installer = signal_installer or install_signal_handlers
    restore = installer(specs) if install_signals else None

    handler = exception_handler or (lambda exc: handle_cli_exception(exc, signal_specs=specs))

    try:
        cli.main(args=list(argv) if argv is not None else None, standalone_mode=False, prog_name=prog_name)
        return 0
    except BaseException as exc:  # noqa: BLE001 - single funnel for exit codes
        return handler(exc)
    finally:
        if restore is not None:
            restore()
        flush_streams()
