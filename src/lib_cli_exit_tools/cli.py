"""Click-based CLI adapter for lib_cli_exit_tools.

Purpose:
    Provide the end-user command-line surface while delegating error-handling
    and exit-code logic to :mod:`lib_cli_exit_tools.lib_cli_exit_tools`.
Contents:
    * :func:`cli` group exposing shared options.
    * :func:`cli_info` subcommand reporting distribution metadata.
    * :func:`cli_fail` subcommand triggering a deterministic failure for testing error paths.
    * :func:`main` entry point used by console scripts and ``python -m``.
System Integration:
    The CLI mutates :data:`lib_cli_exit_tools.config` based on the ``--traceback``
    flag before handing execution off to :func:`lib_cli_exit_tools.run_cli`.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Optional, Sequence

import rich_click as click
from rich_click import rich_click as rich_config

from . import __init__conf__
from . import lib_cli_exit_tools

#: Help flag aliases applied to every Click command so documentation and CLI
#: behaviour stay consistent (`-h` mirrors `--help`).
CLICK_CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])  # noqa: C408


def _needs_plain_output(stream: object) -> bool:
    """Return ``True`` when ``stream`` cannot safely render Rich styling."""
    return (not _stream_is_tty(stream)) or (not _stream_supports_utf(stream))


def _stream_is_tty(stream: object) -> bool:
    """Return ``True`` when ``stream`` reports itself as a TTY."""
    checker = getattr(stream, "isatty", lambda: False)
    try:
        return bool(checker())
    except Exception:  # pragma: no cover - defensive
        return False


def _stream_supports_utf(stream: object) -> bool:
    """Return ``True`` when ``stream`` advertises a UTF-capable encoding."""
    encoding = (getattr(stream, "encoding", "") or "").lower()
    return "utf" in encoding


def _prefer_ascii_layout() -> None:
    """Downgrade rich-click global styling to ASCII-friendly defaults."""
    rich_config.FORCE_TERMINAL = False
    rich_config.COLOR_SYSTEM = None
    rich_config.STYLE_OPTIONS_PANEL_BOX = None
    rich_config.STYLE_COMMANDS_PANEL_BOX = None
    rich_config.STYLE_ERRORS_PANEL_BOX = None


def _snapshot_rich_click_options() -> dict[str, object]:
    """Capture rich-click global styling toggles for later restoration."""

    attributes = (
        "FORCE_TERMINAL",
        "COLOR_SYSTEM",
        "STYLE_OPTIONS_PANEL_BOX",
        "STYLE_COMMANDS_PANEL_BOX",
        "STYLE_ERRORS_PANEL_BOX",
    )
    return {name: getattr(rich_config, name, None) for name in attributes}


def _restore_rich_click_options(snapshot: dict[str, object]) -> None:
    """Restore rich-click globals to the captured snapshot."""

    for name, value in snapshot.items():
        setattr(rich_config, name, value)


@contextmanager
def _temporary_rich_click_configuration() -> Iterator[None]:
    """Apply plain-output safeguards and restore rich-click globals afterwards."""

    snapshot = _snapshot_rich_click_options()
    stdout_stream = click.get_text_stream("stdout")
    stderr_stream = click.get_text_stream("stderr")
    if _needs_plain_output(stdout_stream) and _needs_plain_output(stderr_stream):
        _prefer_ascii_layout()
    try:
        yield
    finally:
        _restore_rich_click_options(snapshot)


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
    _remember_traceback_flag(ctx, traceback)
    lib_cli_exit_tools.config.traceback = traceback


def _remember_traceback_flag(ctx: click.Context, traceback: bool) -> None:
    ctx.ensure_object(dict)
    ctx.obj["traceback"] = traceback


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


@cli.command("fail", context_settings=CLICK_CONTEXT_SETTINGS)
def cli_fail() -> None:
    """Intentionally raise a failure to validate error handling.

    Why:
        Exercise the error-reporting path so engineers can confirm exit-code
        translation and optional traceback behaviour without crafting custom
        failing commands.
    Side Effects:
        Delegates to :func:`lib_cli_exit_tools.i_should_fail`, which raises
        ``RuntimeError`` for the caller to handle.
    Examples:
        >>> from click.testing import CliRunner
        >>> runner = CliRunner()
        >>> result = runner.invoke(cli, ["fail"])
        >>> result.exit_code != 0
        True
        >>> "i should fail" in result.output or "i should fail" in result.stderr
        True
    """

    lib_cli_exit_tools.i_should_fail()


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
    with _temporary_rich_click_configuration():
        return lib_cli_exit_tools.run_cli(
            cli,
            argv=_normalised_arguments(argv),
            prog_name=__init__conf__.shell_command,
        )


def _normalised_arguments(argv: Optional[Sequence[str]]) -> Optional[Sequence[str]]:
    """Convert optional sequences to mutable lists for Click consumption."""
    return list(argv) if argv is not None else None
