from __future__ import annotations

import platform
import signal
from typing import Optional, List
from types import FrameType

import click

from . import __init__conf__
from . import lib_cli_exit_tools as tools

is_windows = platform.system().lower() == "windows"
is_posix = not is_windows


class SigIntError(Exception):
    """Raised on SIGINT (Ctrl+C)."""


class SigTermError(Exception):
    """Raised on SIGTERM (POSIX) or SIGBREAK (Windows)."""


class SigBreakError(Exception):
    """Raised on SIGBREAK (Windows Ctrl+Break)."""


def _sigint_handler(signo: int, frame: FrameType | None) -> None:
    raise SigIntError()


def _sigterm_handler(signo: int, frame: FrameType | None) -> None:
    raise SigTermError()


def _install_signal_handlers() -> None:
    """Install minimal, portable signal handlers.

    * Always handle SIGINT.
    * On POSIX, also handle SIGTERM.
    * On Windows, handle SIGBREAK (Ctrl+Break) as a best-effort replacement for SIGTERM.
    """
    signal.signal(signal.SIGINT, _sigint_handler)
    if is_posix:
        signal.signal(signal.SIGTERM, _sigterm_handler)
    else:
        # SIGBREAK exists on Windows
        try:

            def _sigbreak_handler(signo: int, frame: FrameType | None) -> None:
                raise SigBreakError()

            signal.signal(signal.SIGBREAK, _sigbreak_handler)  # type: ignore[attr-defined]
        except Exception:
            pass


CLICK_CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])  # noqa: C408


@click.group(help=__init__conf__.title, context_settings=CLICK_CONTEXT_SETTINGS)
@click.version_option(
    version=__init__conf__.version,
    prog_name=__init__conf__.shell_command,
    message=f"{__init__conf__.shell_command} version {__init__conf__.version}",
)
@click.option(
    "--traceback/--no-traceback",
    is_flag=True,
    default=False,
    help="Show full Python traceback on errors",
)
@click.pass_context
def cli(ctx: click.Context, traceback: bool) -> None:
    """Root CLI group. Stores global opts in context & tools.config."""
    ctx.ensure_object(dict)
    ctx.obj["traceback"] = traceback
    tools.config.traceback = traceback


@cli.command("info", context_settings=CLICK_CONTEXT_SETTINGS)
def cli_info() -> None:
    """Print project information."""
    __init__conf__.print_info()


def _handle_exception(e: BaseException) -> int:
    """Centralized exception → exit-code + printing.

    Respects tools.config.traceback and uses tools.print_exception_message.
    Returns an integer once (single return style).
    """
    result: int | None = None
    if isinstance(e, (SigIntError, KeyboardInterrupt)):
        click.echo("Aborted (SIGINT).", err=True)
        result = 130  # 128 + SIGINT(2)
    elif isinstance(e, SigTermError):
        click.echo("Terminated (SIGTERM/SIGBREAK).", err=True)
        result = 143  # 128 + SIGTERM(15)
    elif isinstance(e, SigBreakError):  # precise mapping for Windows Ctrl+Break
        click.echo("Terminated (SIGBREAK).", err=True)
        result = 149  # 128 + SIGBREAK(21)
    elif isinstance(e, BrokenPipeError):
        # Broken pipe: stay quiet and exit with configured code
        result = int(tools.config.broken_pipe_exit_code)
    elif isinstance(e, click.ClickException):
        e.show()
        result = e.exit_code
    elif isinstance(e, SystemExit):
        try:
            result = int(e.code or 0)
        except Exception:
            result = 1
    else:
        # Unexpected exception: print nicely or with traceback depending on config
        if tools.config.traceback:
            # Re-raise so Python prints full traceback (useful in CI/dev)
            raise
        tools.print_exception_message()
        result = tools.get_system_exit_code(e)
    return int(result)


def main(argv: Optional[List[str]] = None) -> int:
    """Entrypoint returning an int exit code.

    Use via `python -m lib_cli_exit_tools` or console script.
    """
    _install_signal_handlers()
    try:
        # Do not let Click exit the process; we want to convert to int code
        cli.main(args=argv, standalone_mode=False, prog_name=__init__conf__.shell_command)
        return 0
    except BaseException as e:  # noqa: BLE001 - we want a single exit funnel
        return _handle_exception(e)
    finally:
        tools.flush_streams()
