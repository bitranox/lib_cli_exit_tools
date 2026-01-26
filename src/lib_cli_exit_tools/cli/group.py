"""Root Click group, context state, and CLI entry point.

Purpose:
    Define the top-level Click group with shared options (``--traceback``,
    ``--version``) and the :func:`main` entry point used by console scripts.
Contents:
    * :class:`CliContextState` typed container for Click context state.
    * :func:`cli` root Click group.
    * :func:`main` entry point for console scripts and ``python -m``.
System Integration:
    The CLI mutates :data:`lib_cli_exit_tools.config` based on the ``--traceback``
    flag before handing execution off to :func:`lib_cli_exit_tools.run_cli`.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import rich_click as click

from .. import __init__conf__
from .. import lib_cli_exit_tools
from .commands import CLICK_CONTEXT_SETTINGS
from .styling import _temporary_rich_click_configuration  # pyright: ignore[reportPrivateUsage]


@dataclass
class CliContextState:
    """Type-safe container for Click context object state.

    Why:
        Replaces untyped dict usage in ctx.obj to enforce type safety and
        prevent string literal key access violations.

    Attributes:
        traceback: Whether to show full Python tracebacks on errors.
    """

    traceback: bool = False


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
    """Root Click group that primes shared configuration state.

    Why:
        Accept a single ``--traceback`` flag that determines whether downstream
        helpers emit stack traces.
    Parameters:
        ctx: Click context object for the current invocation.
        traceback: When ``True`` enables traceback output for subsequent commands.
    Side Effects:
        Mutates ``ctx.obj`` and :data:`lib_cli_exit_tools.config.traceback`.
    Examples:
        >>> from click.testing import CliRunner
        >>> runner = CliRunner()
        >>> result = runner.invoke(cli, ["--help"])
        >>> result.exit_code == 0
        True
    """
    _store_traceback_flag(ctx, traceback)
    lib_cli_exit_tools.config.traceback = traceback


def _store_traceback_flag(ctx: click.Context, traceback: bool) -> None:
    """Store traceback flag in typed context state.

    Parameters:
        ctx: Click context object for the current invocation.
        traceback: Whether to show full Python tracebacks on errors.

    Side Effects:
        Initializes ctx.obj as CliContextState if not already set and updates
        the traceback field.
    """
    ctx.ensure_object(CliContextState)
    # Type narrowing: ctx.obj is guaranteed to be CliContextState after ensure_object
    state = ctx.obj
    if isinstance(state, CliContextState):  # nosec B101 - type guard, not assertion
        state.traceback = traceback


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI with :func:`lib_cli_exit_tools.run_cli` wiring.

    Why:
        Serve as the target for console scripts and ``python -m`` execution by
        returning an integer exit code instead of exiting directly.
    Parameters:
        argv: Optional iterable of arguments passed to Click (without program name).
    Returns:
        Integer exit code from :func:`lib_cli_exit_tools.run_cli`.
    Side Effects:
        Delegates to Click and may write to stdout/stderr.
    Examples:
        >>> import contextlib, io
        >>> buffer = io.StringIO()
        >>> with contextlib.redirect_stdout(buffer):
        ...     exit_code = main(["info"])
        >>> exit_code
        0
        >>> "Info for" in buffer.getvalue()
        True
    """
    with _temporary_rich_click_configuration():
        return lib_cli_exit_tools.run_cli(
            cli,
            argv=list(argv) if argv is not None else None,
            prog_name=__init__conf__.shell_command,
        )
