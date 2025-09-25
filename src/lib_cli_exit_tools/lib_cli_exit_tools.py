"""CLI exit orchestration helpers used by the lib-cli-exit-tools package.

Purpose:
    Provide reusable building blocks for Click-based CLIs so they translate
    Python exceptions, OS signals, and subprocess failures into deterministic
    exit codes without leaking stack traces by default.
Contents:
    * `_Config` and the shared `config` object that let transports toggle
      traceback emission, exit-code styles, and broken-pipe behavior.
    * Signal-related types (`SignalSpec`, `CliSignalError` subclasses) and the
      `install_signal_handlers` helper that wire POSIX/Windows signals into
      structured Python exceptions.
    * Exit-code helpers (`handle_cli_exception`, `get_system_exit_code`,
      `_sysexits_mapping`) and CLI orchestration (`run_cli`).
System Integration:
    The CLI adapter defined in :mod:`lib_cli_exit_tools.cli` mutates `config`
    based on global Click options and delegates command execution to
    :func:`run_cli`. API consumers import this module directly when they need
    signal registration or exit-code derivation outside the bundled CLI.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
from dataclasses import dataclass
from types import FrameType
from typing import Any, Callable, List, Literal, Optional, Protocol, Sequence, TextIO

import rich_click as click
from rich_click import rich_click as rich_config
from rich.console import Console
from rich.text import Text
from rich.traceback import Traceback

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
    """Centralized runtime flags shared across all CLI executions.

    Why:
        Prevent each CLI adapter from re-implementing toggles for traceback
        emission and exit-code semantics. The Click adapter mutates these fields
        once per process based on global command options.
    What:
        Stores the behavioral switches consulted by error printers and
        exit-code helpers. Values are mutated in place so that successive calls
        reuse the same configuration.
    Fields:
        traceback (bool): Enables stack-trace passthrough when ``True`` to aid
            debugging without altering default UX for end users.
        exit_code_style (Literal['errno', 'sysexits']): Selects the exit-code
            mapping strategy, allowing consumers to opt into BSD ``sysexits``
            values when shell scripts rely on them.
        broken_pipe_exit_code (int): Exit code returned when a
            ``BrokenPipeError`` occurs; defaults to ``141`` so pipelines can
            detect truncated output.
        traceback_force_color (bool): Force Rich to emit ANSI-coloured
            tracebacks even when stdout/stderr are not detected as TTYs.
    Side Effects:
        Mutations are process wide because :data:`config` exports a module-level
        instance. Callers should restore values in tests to avoid leakage.
    """

    traceback: bool = False
    exit_code_style: Literal["errno", "sysexits"] = "errno"
    broken_pipe_exit_code: int = 141
    traceback_force_color: bool = False


#: Shared configuration singleton consulted by CLI orchestration helpers.
config = _Config()


class CliSignalError(RuntimeError):
    """Marker exception bridging OS signals with exit-code translation.

    Why:
        Provide a dedicated hierarchy so tests and callers can catch
        signal-driven interruptions separately from generic runtime errors.
    What:
        Subclasses represent specific signals (SIGINT, SIGTERM, SIGBREAK) and
        allow :func:`handle_cli_exception` to map them back to deterministic
        exit codes.
    Side Effects:
        None. Instances carry no extra state beyond the chosen subclass.
    """


class SigIntInterrupt(CliSignalError):
    """Raised when the process receives ``SIGINT`` (Ctrl+C).

    Why:
        Helps :func:`handle_cli_exception` distinguish user-initiated
        interruptions from other runtime failures.
    """


class SigTermInterrupt(CliSignalError):
    """Raised when the process receives ``SIGTERM`` (termination request).

    Why:
        Enables consistent exit-code mapping for orchestration systems that send
        termination signals (e.g., Kubernetes, systemd).
    """


class SigBreakInterrupt(CliSignalError):
    """Raised when the process receives ``SIGBREAK`` on Windows consoles.

    Why:
        Allows Windows users to map Ctrl+Break to a deterministic exit code
        instead of propagating a less descriptive error.
    """


@dataclass(slots=True)
class SignalSpec:
    """Describe how to translate a low-level signal into CLI-facing behavior.

    Why:
        Capture signal metadata in a structured form so installers and
        exception handlers agree on signum-to-exit-code mappings.
    Fields:
        signum (int): The numeric signal identifier to register with
            :mod:`signal`.
        exception (type[BaseException]): The exception type instantiated by the
            handler so :func:`handle_cli_exception` can inspect the raised
            value.
        message (str): User-facing text echoed to stderr when the signal is
            encountered.
        exit_code (int): Numeric exit code returned to the operating system.
    Side Effects:
        None; instances are immutable dataclasses and safe to reuse.
    """

    signum: int
    exception: type[BaseException]
    message: str
    exit_code: int


class _Echo(Protocol):
    """Protocol describing the echo interface expected by error handlers.

    Why:
        Allow tests to supply lightweight stand-ins for :func:`click.echo`
        without importing Click.
    """

    def __call__(self, message: str, *, err: bool = ...) -> None: ...  # pragma: no cover - structural typing


#: Type alias for signal handlers compatible with :func:`signal.signal`.
_Handler = Callable[[int, FrameType | None], None]


def _default_echo(message: str, *, err: bool = True) -> None:
    """Proxy to :func:`click.echo` used when callers do not supply one.

    Why:
        Keep :func:`handle_cli_exception` decoupled from Click while offering a
        sensible default for stderr logging. Dependency injection makes the
        helper testable without monkey-patching :mod:`click` globally.
    Parameters:
        message: Text to emit.
        err: When ``True`` (default) the message targets stderr; Click falls back
            to stdout otherwise.
    Returns:
        ``None``. The effect is purely the emitted text.
    Side Effects:
        Writes a newline-terminated string to stdout/stderr via Click's IO
        abstraction.
    Examples:
        >>> from click.testing import CliRunner
        >>> runner = CliRunner()
        >>> @click.command()
        ... def _cmd():
        ...     _default_echo("hi", err=False)
        >>> result = runner.invoke(_cmd)
        >>> result.output.strip()
        'hi'
    """

    click.echo(message, err=err)


def default_signal_specs() -> List[SignalSpec]:
    """Build the default list of signal specifications for the host platform.

    Why:
        Provide a single source of truth for signal-to-exit mappings so both
        :func:`install_signal_handlers` and :func:`handle_cli_exception` behave
        consistently on POSIX and Windows.
    Returns:
        ``list[SignalSpec]`` where each item represents a supported signal.
        ``SIGINT`` is always present; ``SIGTERM``/``SIGBREAK`` are added when the
        runtime exposes them.
    Side Effects:
        None. The list is newly constructed on each call.
    Examples:
        >>> specs = default_signal_specs()
        >>> specs[0].exception is SigIntInterrupt
        True
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

    return specs


def _make_raise_handler(exc_type: type[BaseException]) -> _Handler:
    """Wrap ``exc_type`` in a signal-compatible callable.

    Why:
        ``signal.signal`` expects a handler signature ``(signum, frame)``. By
        generating one on demand we keep installation code concise and avoid
        repeating the raising logic for every signal.
    Parameters:
        exc_type: Exception subclass to raise when the handler runs.
    Returns:
        Callable that ignores its inputs and raises ``exc_type`` immediately.
    Side Effects:
        None at creation time; the returned handler raises when invoked.
    Examples:
        >>> handler = _make_raise_handler(SigIntInterrupt)
        >>> try:
        ...     handler(signal.SIGINT, None)
        ... except SigIntInterrupt:
        ...     caught = True
        ... else:
        ...     caught = False
        >>> caught
        True
    """

    def _handler(signo: int, frame: FrameType | None) -> None:  # pragma: no cover - just raises
        raise exc_type()

    return _handler


def install_signal_handlers(specs: Sequence[SignalSpec] | None = None) -> Callable[[], None]:
    """Install signal handlers that re-raise as structured exceptions.

    Why:
        Centralize signal wiring so CLI entry points can opt in to robust
        interruption handling without duplicating boilerplate.
    Parameters:
        specs: Optional iterable of :class:`SignalSpec`. When omitted the
            defaults from :func:`default_signal_specs` are used.
    Returns:
        Callable that, when executed, restores the previous signal handlers.
    Side Effects:
        Registers handlers with :mod:`signal` for each provided specification.
        Handlers are process-wide; callers must invoke the returned restore
        function to avoid leaking state.
    Examples:
        >>> restore = install_signal_handlers([])
        >>> callable(restore)
        True
        >>> restore()  # nothing was installed, so this is a no-op
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
    """Convert an exception raised by a CLI into a deterministic exit code.

    Why:
        Keep ``click`` command invocations small by centralising how we surface
        failures, map signals, and honour the global traceback toggle.
    Parameters:
        exc: Exception propagated by the command execution.
        signal_specs: Optional custom signal specifications.
        echo: Optional callable used to emit human-readable signal messages.
    Returns:
        Integer exit code suitable for :func:`sys.exit` (values differ between
        POSIX and Windows because we mirror platform-specific errno codes).
    Side Effects:
        May write to stderr via ``echo``, call :func:`print_exception_message`,
        or raise ``exc`` again when ``config.traceback`` is ``True``.
    Examples:
        >>> handle_cli_exception(ValueError("bad input")) in {22, 87}
        True
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
    """Execute a Click command with shared signal/error handling installed.

    Why:
        Guarantee that all entry points (console scripts, ``python -m``) share
        the same policy for signal registration, exit-code derivation, and
        stream flushing.
    Parameters:
        cli: Click command or group to execute.
        argv: Optional sequence of arguments, excluding the program name.
        prog_name: Overrides the program name shown in Click help/version.
        signal_specs: Optional custom signal specifications.
        install_signals: Skip signal wiring when ``False`` (useful for tests).
    Returns:
        Integer exit code suitable for :func:`sys.exit`.
    Side Effects:
        May install process-wide signal handlers, execute the command, flush
        stdio, and emit output.
    Examples:
        >>> @click.command()
        ... def _demo():
        ...     click.echo("hi")
        >>> import contextlib, io
        >>> buffer = io.StringIO()
        >>> with contextlib.redirect_stdout(buffer):
        ...     result = run_cli(_demo, argv=[])
        >>> result
        0
        >>> buffer.getvalue().strip()
        'hi'
    """

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
    """Map an exception to an OS-appropriate exit status.

    Why:
        Provide a predictable fallback when Click or signal-specific handlers do
        not supply an explicit exit code.
    Parameters:
        exc: Exception raised by application logic.
    Returns:
        Integer exit code honouring Windows ``winerror`` values, POSIX ``errno``
        codes, or BSD ``sysexits`` depending on :data:`config`.
        (POSIX maps ``ValueError`` to 22, while Windows maps it to 87.)
    Side Effects:
        None.
    Examples:
        >>> get_system_exit_code(ValueError("bad input")) in {22, 87}
        True
    """

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
    """Translate an exception into BSD ``sysexits`` semantics.

    Why:
        Provide shell-friendly exit codes when ``config.exit_code_style`` is set
        to ``"sysexits"``.
    Parameters:
        exc: Exception raised by application logic.
    Returns:
        Integer drawn from the ``sysexits`` range (e.g., 64 for usage errors).
    Side Effects:
        None.
    Examples:
        >>> _sysexits_mapping(ValueError("bad"))
        64
    """

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


def _build_console(
    stream: Optional[TextIO] = None,
    *,
    force_terminal: bool | None = None,
    color_system: str | None = None,
) -> Console:
    """Construct a Rich console that mirrors rich-click global settings.

    Why:
        Avoid duplicating console configuration whenever we need to emit
        coloured output, ensuring help and error styling stay consistent.
    Parameters:
        stream: Optional target stream; defaults to :data:`sys.stderr`.
        force_terminal: Explicit override for Rich's terminal detection. When
            ``None`` the global rich-click flag is used.
        color_system: Optional override for the Rich colour system. When
            ``None`` the rich-click default is reused.
    Returns:
        Configured :class:`rich.console.Console` instance.
    Side Effects:
        None.
    Examples:
        >>> console = _build_console()
        >>> isinstance(console, Console)
        True
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


def print_exception_message(
    trace_back: bool = config.traceback,
    length_limit: int = 500,
    stream: Optional[TextIO] = None,
) -> None:
    """Emit the active exception message and optional traceback to ``stream``.

    Why:
        Provide consistent, truncated error output when tracebacks are
        suppressed while presenting syntax-highlighted tracebacks for
        debugging when requested.
    Parameters:
        trace_back: When ``True`` render a Rich traceback; otherwise emit a
            single-line summary in red.
        length_limit: Maximum number of characters to emit for summary output.
        stream: Target text stream; defaults to stderr.
            Colour output honours :data:`config.traceback_force_color`, forcing
            ANSI styling when enabled even if Rich detects a non-TTY stream.
    Returns:
        ``None``.
    Side Effects:
        Flushes stdout/stderr, reads :func:`sys.exc_info`, and writes to the
        chosen stream. No output is produced if no exception is active.
    Examples:
        >>> import io
        >>> try:
        ...     raise ValueError("boom")
        ... except ValueError:
        ...     buf = io.StringIO()
        ...     print_exception_message(trace_back=False, stream=buf)
        ...     "ValueError: boom" in buf.getvalue()
        True
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


def _print_output(exc_info: Any, attr: str, stream: Optional[TextIO] = None) -> None:
    """Print captured subprocess output stored on an exception.

    Why:
        :class:`subprocess.CalledProcessError` instances hang on to ``stdout`` and
        ``stderr`` attributes. Surfacing them helps users debug failing commands.
    Parameters:
        exc_info: Exception carrying potential ``stdout``/``stderr`` values.
        attr: Attribute name to inspect (``"stdout"`` or ``"stderr"``).
        stream: Target text stream; defaults to stderr.
    Side Effects:
        Writes decoded output to ``stream`` if present.
    Examples:
        >>> class _Exc:
        ...     stdout = b"hello"
        ...     stderr = None
        >>> import io
        >>> buf = io.StringIO()
        >>> _print_output(_Exc(), "stdout", stream=buf)
        >>> buf.getvalue().strip()
        'STDOUT: hello'
    """

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
    """Best-effort flush of ``stdout`` and ``stderr``.

    Why:
        Prevent buffered output from being lost when the CLI terminates early,
        especially after writing to streams during error handling.
    Returns:
        ``None``.
    Side Effects:
        Invokes ``flush`` on ``sys.stdout`` and ``sys.stderr``; suppresses
        unexpected exceptions from non-standard stream objects.
    Examples:
        >>> flush_streams()
    """

    try:
        sys.stdout.flush()
    except Exception:  # pragma: no cover - best effort
        pass
    try:
        sys.stderr.flush()
    except Exception:  # pragma: no cover
        pass
