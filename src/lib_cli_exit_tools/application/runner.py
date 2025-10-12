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
from contextlib import contextmanager, nullcontext, suppress
from typing import Callable, ContextManager, Iterable, Iterator, Literal, Mapping, Protocol, Sequence, TextIO, cast

import rich_click as click
from rich_click import rich_click as rich_config
from rich.console import Console
from rich.text import Text
from rich.traceback import Traceback

from ..adapters.signals import SignalSpec, default_signal_specs, install_signal_handlers
from ..core.configuration import config, config_overrides
from ..core.exit_codes import get_system_exit_code

RichColorSystem = Literal["auto", "standard", "256", "truecolor", "windows"]
ExitResolver = Callable[[BaseException], int | None]


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
    "cli_session",
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
    stream: TextIO | None = None,
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


def _print_output(exc_info: object, attr: str, stream: TextIO | None = None) -> None:
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


def _decode_output(output: object) -> str | None:
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
    stream: TextIO | None = None,
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
    exc_info = _active_exception()
    if exc_info is None:
        return

    target_stream = _target_stream(stream)
    _emit_subprocess_output(exc_info, target_stream)

    render_traceback = _resolve_traceback_choice(trace_back)
    console = _console_for_tracebacks(target_stream)

    _render_exception_view(console, exc_info, render_traceback, length_limit)
    _finalise_console(console)
    flush_streams()


def _active_exception() -> BaseException | None:
    """Return the currently active exception from ``sys.exc_info``."""
    return sys.exc_info()[1]


def _target_stream(stream: TextIO | None) -> TextIO:
    """Resolve the diagnostics stream, defaulting to ``sys.stderr``."""
    return stream or sys.stderr


def _resolve_traceback_choice(trace_back: bool | None) -> bool:
    """Decide whether to render a traceback based on explicit or global flags."""
    return config.traceback if trace_back is None else trace_back


def _emit_subprocess_output(exc_info: BaseException, stream: TextIO) -> None:
    """Write any subprocess ``stdout``/``stderr`` captured on ``exc_info``."""
    for attr in ("stdout", "stderr"):
        _print_output(exc_info, attr, stream)


def _console_for_tracebacks(stream: TextIO) -> Console:
    """Build a :class:`Console` configured for traceback rendering."""
    force_terminal, color_system = _traceback_colour_preferences()
    return _build_console(stream, force_terminal=force_terminal, color_system=color_system)


def _render_exception_view(
    console: Console,
    exc_info: BaseException,
    render_traceback: bool,
    length_limit: int,
) -> None:
    """Render the chosen diagnostic view for ``exc_info``."""
    if render_traceback:
        _render_traceback(console, exc_info)
        return
    _render_summary(console, exc_info, length_limit)


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
    echo_fn = _choose_echo(echo)
    return _resolve_exit_code(exc, specs, echo_fn)


def _choose_echo(echo: _Echo | None) -> _Echo:
    """Select the echo function, defaulting to click's standard helper."""
    return echo if echo is not None else _default_echo


def _resolve_exit_code(
    exc: BaseException,
    specs: Sequence[SignalSpec],
    echo: _Echo,
) -> int:
    """Walk the resolver chain until a numeric exit code emerges."""
    for resolver in _exception_resolvers(specs, echo):
        code = resolver(exc)
        if code is not None:
            return code
    return _render_and_translate(exc)


def _exception_resolvers(
    specs: Sequence[SignalSpec],
    echo: _Echo,
) -> Iterable[ExitResolver]:
    """Yield exit-code resolver callables in priority order."""
    yield _signal_resolver(specs, echo)
    yield _broken_pipe_exit
    yield _click_exit_code
    yield _system_exit_code


def _signal_resolver(
    specs: Sequence[SignalSpec],
    echo: _Echo,
) -> ExitResolver:
    """Wrap :func:`_signal_exit_code` with the captured context."""

    def _resolver(exc: BaseException) -> int | None:
        return _signal_exit_code(exc, specs, echo)

    return _resolver


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
    print_exception_message(trace_back=config.traceback)
    return get_system_exit_code(exc)


@contextmanager
def cli_session(
    *,
    summary_limit: int = 500,
    verbose_limit: int = 10_000,
    overrides: Mapping[str, object] | None = None,
    restore: bool = True,
) -> Iterator[
    Callable[
        [
            ClickCommand,
        ],
        int,
    ]
    | Callable[..., int]
]:
    """Provide a managed execution context around :func:`run_cli`.

    Why
        Embedders often need to flip :data:`config.traceback` while ensuring
        the previous state is restored even if command execution raises. This
        helper centralises that lifecycle and reuses the standard exception
        handler so callers no longer duplicate try/except scaffolding.

    What
        Snapshots the global configuration, applies ``overrides`` for the
        duration of the session, and yields a callable that executes
        :func:`run_cli` with a preconfigured exception handler honouring the
        provided ``summary_limit``/``verbose_limit`` thresholds. When the
        context exits, configuration reverts to its prior values regardless of
        success or failure.

    Parameters
    ----------
    summary_limit:
        Truncation budget used when tracebacks are disabled.
    verbose_limit:
        Character budget used when tracebacks are enabled.
    overrides:
        Optional mapping of configuration fields temporarily applied during
        the session. When ``traceback`` is supplied and
        ``traceback_force_color`` is omitted, colour output is forced to align
        with the verbose mode.
    restore:
        When ``True`` (default) configuration state is restored after the
        session. Set to ``False`` to leave any overrides or runtime mutations
        in place once the context exits.

    Yields
    ------
    Callable
        Function that accepts a Click command and forwards optional ``run_cli``
        keyword arguments, returning the resulting exit code.
    """

    applied = _normalise_session_overrides(overrides)
    manager = _session_config_manager(applied, restore)

    with manager:
        handler = _session_exception_handler(summary_limit, verbose_limit)

        def _run(
            command: ClickCommand,
            *,
            argv: Sequence[str] | None = None,
            prog_name: str | None = None,
            signal_specs: Sequence[SignalSpec] | None = None,
            install_signals: bool = True,
            exception_handler: Callable[[BaseException], int] | None = None,
            signal_installer: Callable[[Sequence[SignalSpec] | None], Callable[[], None]] | None = None,
        ) -> int:
            chosen_handler = exception_handler or handler
            return run_cli(
                command,
                argv=argv,
                prog_name=prog_name,
                signal_specs=signal_specs,
                install_signals=install_signals,
                exception_handler=chosen_handler,
                signal_installer=signal_installer,
            )

        yield _run


def _normalise_session_overrides(overrides: Mapping[str, object] | None) -> dict[str, object]:
    """Prepare configuration overrides, forcing colour when verbose tracebacks are enabled."""
    applied = dict(overrides or {})
    if "traceback" in applied and "traceback_force_color" not in applied:
        applied["traceback_force_color"] = bool(applied["traceback"])
    return applied


def _session_config_manager(applied: Mapping[str, object], restore: bool) -> ContextManager[object]:
    """Return the context manager used to apply session overrides."""
    if restore:
        return config_overrides(**applied)
    if not applied:
        return nullcontext()
    return _apply_overrides_without_restore(applied)


@contextmanager
def _apply_overrides_without_restore(applied: Mapping[str, object]) -> Iterator[None]:
    """Apply overrides without restoring prior state on exit."""
    for name, value in applied.items():
        setattr(config, name, value)
    yield


def _session_exception_handler(summary_limit: int, verbose_limit: int) -> Callable[[BaseException], int]:
    """Build the exception handler used inside :func:`cli_session`."""

    def _handler(exc: BaseException) -> int:
        active = bool(config.traceback)
        limit = verbose_limit if active else summary_limit
        print_exception_message(trace_back=active, length_limit=limit)
        return get_system_exit_code(exc)

    return _handler


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
    handler = _choose_exception_handler(exception_handler, specs)
    restorer = _install_signal_handlers_when_requested(install_signals, signal_installer, specs)

    try:
        return _run_command_with_handler(cli, argv, prog_name, handler)
    finally:
        _finalise_cli_run(restorer)


def _choose_exception_handler(
    override: Callable[[BaseException], int] | None,
    specs: Sequence[SignalSpec],
) -> Callable[[BaseException], int]:
    """Select the exception handler, defaulting to :func:`handle_cli_exception`."""
    if override is not None:
        return override
    return _default_exception_handler(specs)


def _default_exception_handler(specs: Sequence[SignalSpec]) -> Callable[[BaseException], int]:
    """Build the default exception handler bound to ``specs``."""

    def _handler(exc: BaseException) -> int:
        return handle_cli_exception(exc, signal_specs=specs)

    return _handler


def _install_signal_handlers_when_requested(
    install_signals: bool,
    signal_installer: Callable[[Sequence[SignalSpec] | None], Callable[[], None]] | None,
    specs: Sequence[SignalSpec],
) -> Callable[[], None] | None:
    """Install signal handlers when requested and return a restorer."""
    if not install_signals:
        return None
    installer = signal_installer or install_signal_handlers
    return installer(specs)


def _run_command_with_handler(
    cli: ClickCommand,
    argv: Sequence[str] | None,
    prog_name: str | None,
    handler: Callable[[BaseException], int],
) -> int:
    """Invoke the Click command and delegate failures to ``handler``."""
    try:
        _invoke_command(cli, argv, prog_name)
    except BaseException as exc:  # noqa: BLE001 - single funnel for exit codes
        return handler(exc)
    return 0


def _finalise_cli_run(restorer: Callable[[], None] | None) -> None:
    """Restore signal handlers when needed and flush IO buffers."""
    _restore_handlers_if_needed(restorer)
    flush_streams()


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
