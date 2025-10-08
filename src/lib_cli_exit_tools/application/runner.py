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

import sys
from contextlib import suppress
from typing import Callable, Iterable, Literal, Optional, Protocol, Sequence, TextIO, cast

import rich_click as click
from rich_click import rich_click as rich_config
from rich.console import Console
from rich.text import Text
from rich.traceback import Traceback

from ..adapters.signals import SignalSpec, default_signal_specs, install_signal_handlers
from ..core.configuration import config
from ..core.exit_codes import get_system_exit_code

RichColorSystem = Literal["auto", "standard", "256", "truecolor", "windows"]


class ClickCommand(Protocol):
    """Protocol capturing the subset of Click commands used by the runner."""

    def main(
        self,
        args: Sequence[str] | None = ...,
        prog_name: str | None = ...,
        complete_var: str | None = ...,
        standalone_mode: bool = ...,
        **_: object,
    ) -> None: ...


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
    """Flush standard streams so diagnostics do not linger in buffers.

    Why:
        Rich tracebacks and click output use buffering; flushing ensures users
        see diagnostics even when the process exits immediately afterward.
    Returns:
        ``None``.
    Side Effects:
        Calls ``flush`` on ``sys.stdout`` and ``sys.stderr`` when available.
    """

    for stream in _streams_to_flush():
        _flush_stream(stream)


def _streams_to_flush() -> Iterable[object]:
    """Yield stream objects that should be flushed before exiting.

    Why:
        Factoring iteration into a helper simplifies testing and keeps the
        flush logic symmetric for stdout and stderr.
    Returns:
        Generator producing available stream objects.
    """
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is not None:
            yield stream


def _flush_stream(stream: object) -> None:
    """Flush ``stream`` if it exposes a callable ``flush`` attribute.

    Parameters:
        stream: Object potentially offering a ``flush`` method.
    Returns:
        ``None``; silently ignores errors because flushing is best-effort.
    """
    flush = getattr(stream, "flush", None)
    if callable(flush):  # pragma: no branch - simple guard
        with suppress(Exception):  # pragma: no cover - best effort
            flush()


def _build_console(
    stream: Optional[TextIO] = None,
    *,
    force_terminal: bool | None = None,
    color_system: RichColorSystem | None = None,
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
    default_color = cast(RichColorSystem | None, getattr(rich_config, "COLOR_SYSTEM", None))
    color_flag = default_color if color_system is None else color_system
    return Console(
        file=target_stream,
        force_terminal=force_flag,
        color_system=color_flag,
        soft_wrap=True,
    )


def _print_output(exc_info: object, attr: str, stream: Optional[TextIO] = None) -> None:
    """Print captured subprocess output stored on ``exc_info``.

    Why:
        ``click`` surfaces subprocess errors by attaching ``stdout``/``stderr``
        to exceptions; mirroring that output aids debugging.
    Parameters:
        exc_info: Exception object potentially carrying the output attribute.
        attr: Attribute name to inspect (``"stdout"`` or ``"stderr"``).
        stream: Destination stream; defaults to ``sys.stderr`` when ``None``.
    Returns:
        ``None``.
    """

    target = stream or sys.stderr
    if not hasattr(exc_info, attr):
        return

    text = _decode_output(getattr(exc_info, attr))
    if text:
        print(f"{attr.upper()}: {text}", file=target)


def _decode_output(output: object) -> Optional[str]:
    """Convert subprocess output into text, tolerating bytes and ``None``.

    Parameters:
        output: Raw value stored on an exception object.
    Returns:
        Decoded string when possible; ``None`` when the value is unusable.
    """
    if output is None:
        return None
    if isinstance(output, bytes):
        try:
            return output.decode("utf-8", errors="replace")
        except Exception:
            return None
    if isinstance(output, str):
        return output
    return None


def print_exception_message(
    trace_back: bool | None = None,
    length_limit: int = 500,
    stream: Optional[TextIO] = None,
) -> None:
    """Emit the active exception message and optional traceback to ``stream``.

    Why:
        Offer a single choke point for rendering user-facing diagnostics so the
        CLI can toggle between terse and verbose output via configuration.
    Parameters:
        trace_back: When ``None`` (default) reuse :data:`config.traceback`.
            When ``True`` render a Rich traceback; otherwise print a truncated
            red summary.
        length_limit: Maximum length of the summary string when tracebacks are
            suppressed.
        stream: Target text stream; defaults to ``sys.stderr``.
    Side Effects:
        Flushes standard streams, inspects ``sys.exc_info()``, and prints via
        Rich using the active colour configuration.
    """

    flush_streams()

    effective_traceback = config.traceback if trace_back is None else trace_back

    exc_info = _active_exception()
    if exc_info is None:
        return

    target_stream = stream or sys.stderr
    _emit_subprocess_output(exc_info, target_stream)

    console = _console_for_tracebacks(target_stream)
    if effective_traceback:
        _render_traceback(console, exc_info)
    else:
        _render_summary(console, exc_info, length_limit)

    _finalise_console(console)
    flush_streams()


def _active_exception() -> BaseException | None:
    """Return the currently active exception from ``sys.exc_info``."""
    return sys.exc_info()[1]


def _emit_subprocess_output(exc_info: BaseException, stream: TextIO) -> None:
    """Write any subprocess ``stdout``/``stderr`` captured on ``exc_info``."""
    for attr in ("stdout", "stderr"):
        _print_output(exc_info, attr, stream)


def _console_for_tracebacks(stream: TextIO) -> Console:
    """Build a :class:`Console` configured for traceback rendering."""
    force_terminal, color_system = _traceback_colour_preferences()
    return _build_console(stream, force_terminal=force_terminal, color_system=color_system)


def _traceback_colour_preferences() -> tuple[bool | None, RichColorSystem | None]:
    """Determine whether tracebacks should force colour output."""
    if config.traceback_force_color:
        return True, "auto"
    return None, None


def _render_traceback(console: Console, exc_info: BaseException) -> None:
    """Render a Rich traceback for ``exc_info`` to ``console``."""
    renderable = Traceback.from_exception(
        type(exc_info),
        exc_info,
        exc_info.__traceback__,
        show_locals=False,
    )
    console.print(renderable)


def _render_summary(console: Console, exc_info: BaseException, length_limit: int) -> None:
    """Render a concise summary for ``exc_info`` with truncation support."""
    message = Text(f"{type(exc_info).__name__}: {exc_info}", style="bold red")
    summary = _truncate_message(message, length_limit)
    console.print(summary)


def _truncate_message(message: Text, length_limit: int) -> Text:
    """Return ``message`` truncated to ``length_limit`` characters when needed."""
    if len(message.plain) <= length_limit:
        return message
    truncated = f"{message.plain[:length_limit]} ... [TRUNCATED at {length_limit} characters]"
    return Text(truncated, style=message.style)


def _finalise_console(console: Console) -> None:
    """Flush the console file handle to ensure output reaches the user."""
    console.file.flush()


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

    specs = _resolve_signal_specs(signal_specs)
    echo_fn = echo if echo is not None else _default_echo

    code = _signal_exit_code(exc, specs, echo_fn)
    if code is not None:
        return code

    code = _broken_pipe_exit(exc)
    if code is not None:
        return code

    code = _click_exit_code(exc)
    if code is not None:
        return code

    code = _system_exit_code(exc)
    if code is not None:
        return code

    return _render_and_translate(exc)


def _resolve_signal_specs(specs: Sequence[SignalSpec] | None) -> Sequence[SignalSpec]:
    """Resolve caller-provided signal specs, defaulting to standard ones."""
    return specs if specs is not None else default_signal_specs()


def _signal_exit_code(exc: BaseException, specs: Sequence[SignalSpec], echo: _Echo) -> int | None:
    """Return a signal exit code when ``exc`` matches one of ``specs``."""
    for spec in specs:
        if isinstance(exc, spec.exception):
            echo(spec.message, err=True)
            return spec.exit_code
    return None


def _broken_pipe_exit(exc: BaseException) -> int | None:
    """Return the configured broken-pipe exit code when applicable."""
    if isinstance(exc, BrokenPipeError):
        return int(config.broken_pipe_exit_code)
    return None


def _click_exit_code(exc: BaseException) -> int | None:
    """Let Click exceptions decide their own exit codes."""
    if isinstance(exc, click.ClickException):
        exc.show()
        return exc.exit_code
    return None


def _system_exit_code(exc: BaseException) -> int | None:
    """Extract the integer payload from ``SystemExit`` when present."""
    if not isinstance(exc, SystemExit):
        return None
    return _safe_system_exit_code(exc)


def _safe_system_exit_code(exc: SystemExit) -> int:
    """Read the ``SystemExit`` payload defensively, defaulting to failure.

    Parameters:
        exc: ``SystemExit`` raised by user code or Click internals.
    Returns:
        Integer payload when coercible; otherwise ``1``.
    """
    with suppress(Exception):
        return int(exc.code or 0)
    return 1


def _render_and_translate(exc: BaseException) -> int:
    """Render the exception according to configuration, then resolve a code."""
    _print_exception_with_active_mode()
    return get_system_exit_code(exc)


def _print_exception_with_active_mode() -> None:
    """Invoke :func:`print_exception_message`, tolerating legacy signatures."""
    try:
        print_exception_message(trace_back=config.traceback)
    except TypeError:
        print_exception_message()


def run_cli(
    cli: ClickCommand,
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

    specs = _resolve_signal_specs(signal_specs)
    handler = exception_handler or _default_exception_handler(specs)
    restore = _maybe_install_signals(install_signals, signal_installer, specs)

    try:
        _invoke_command(cli, argv, prog_name)
        return 0
    except BaseException as exc:  # noqa: BLE001 - single funnel for exit codes
        return handler(exc)
    finally:
        _restore_handlers_if_needed(restore)
        flush_streams()


def _default_exception_handler(specs: Sequence[SignalSpec]) -> Callable[[BaseException], int]:
    """Build the default exception handler bound to ``specs``."""

    def _handler(exc: BaseException) -> int:
        return handle_cli_exception(exc, signal_specs=specs)

    return _handler


def _maybe_install_signals(
    install_signals: bool,
    signal_installer: Callable[[Sequence[SignalSpec] | None], Callable[[], None]] | None,
    specs: Sequence[SignalSpec],
) -> Callable[[], None] | None:
    """Install signal handlers when requested and return a restorer."""
    if not install_signals:
        return None
    installer = signal_installer or install_signal_handlers
    return installer(specs)


def _invoke_command(cli: ClickCommand, argv: Sequence[str] | None, prog_name: str | None) -> None:
    """Invoke the Click command with ``standalone_mode`` disabled."""
    cli.main(args=_normalised_args(argv), standalone_mode=False, prog_name=prog_name)


def _normalised_args(argv: Sequence[str] | None) -> Sequence[str] | None:
    """Return ``argv`` as a mutable list when provided, otherwise ``None``."""
    return list(argv) if argv is not None else None


def _restore_handlers_if_needed(restore: Callable[[], None] | None) -> None:
    """Invoke the signal restorer callback when one was provided."""
    if restore is None:
        return
    restore()
