"""Click-based CLI adapter for lib_cli_exit_tools.

Purpose:
    Provide the end-user command-line surface while delegating error-handling
    and exit-code logic to :mod:`lib_cli_exit_tools.lib_cli_exit_tools`.
Contents:
    * :func:`cli` group exposing shared options.
    * :func:`cli_info` subcommand reporting distribution metadata.
    * :func:`main` entry point used by console scripts and ``python -m``.
System Integration:
    The CLI mutates :data:`lib_cli_exit_tools.config` based on the ``--traceback``
    flag before handing execution off to :func:`lib_cli_exit_tools.run_cli`.
"""

from __future__ import annotations

from typing import Optional, Sequence

import rich_click as click
from rich_click import rich_click as rich_config

from . import __init__conf__
from . import lib_cli_exit_tools

#: Consistent help flag aliases reused across all lib-cli-exit-tools commands.
CLICK_CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])  # noqa: C408


def _configure_rich_click_output() -> None:
    """Keep rich-click help rendering compatible with limited encodings.

    Why:
        GitHub Actions on Windows sets ``GITHUB_ACTIONS=true`` which causes
        rich-click to force rich formatting even when stdout is a pipe. When the
        pipe uses a legacy ``charmap`` codec, box-drawing characters in the rich
        layout trigger ``UnicodeEncodeError`` and surface as an exit status of
        ``87`` (``ERROR_INVALID_PARAMETER``). Disabling the forced terminal mode
        and the decorative boxes keeps the help output ASCII-only so Windows
        pipes can consume it reliably.
    Side Effects:
        Mutates global rich-click configuration before any commands run. The
        tweak applies process-wide but only removes styling when stdout is not a
        TTY or exposes a non-UTF encoding.
    Examples:
        >>> class _FakeStream:
        ...     encoding = "cp1252"
        ...     def isatty(self) -> bool:
        ...         return False
        >>> original = click.get_text_stream
        >>> click.get_text_stream = lambda _: _FakeStream()
        >>> try:
        ...     rich_config.FORCE_TERMINAL = True
        ...     _configure_rich_click_output()
        ...     rich_config.FORCE_TERMINAL
        ... finally:
        ...     click.get_text_stream = original
        False
    """

    stream = click.get_text_stream("stdout")
    encoding = (getattr(stream, "encoding", "") or "").lower()
    is_tty = bool(getattr(stream, "isatty", lambda: False)())
    supports_utf8 = "utf" in encoding

    if not is_tty or not supports_utf8:
        rich_config.FORCE_TERMINAL = False
        rich_config.COLOR_SYSTEM = None
        rich_config.STYLE_OPTIONS_PANEL_BOX = None
        rich_config.STYLE_COMMANDS_PANEL_BOX = None
        rich_config.STYLE_ERRORS_PANEL_BOX = None


_configure_rich_click_output()


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
    ctx.ensure_object(dict)
    ctx.obj["traceback"] = traceback
    lib_cli_exit_tools.config.traceback = traceback


@cli.command("info", context_settings=CLICK_CONTEXT_SETTINGS)
def cli_info() -> None:
    """Display package metadata sourced from :mod:`importlib.metadata`.

    Why:
        Offer a zero-dependency way for users to confirm the installed version
        and provenance of the CLI.
    Side Effects:
        Writes formatted metadata to stdout.
    Examples:
        >>> from click.testing import CliRunner
        >>> runner = CliRunner()
        >>> result = runner.invoke(cli, ["info"])
        >>> "Info for" in result.output
        True
    """
    __init__conf__.print_info()


def main(argv: Optional[Sequence[str]] = None) -> int:
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
    return lib_cli_exit_tools.run_cli(
        cli,
        argv=list(argv) if argv is not None else None,
        prog_name=__init__conf__.shell_command,
    )
