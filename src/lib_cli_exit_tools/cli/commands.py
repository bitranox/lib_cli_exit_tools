"""Click subcommands for the lib_cli_exit_tools CLI.

Purpose:
    Define individual CLI subcommands that expose library functionality to
    end users (``info``, ``fail``).
Contents:
    * :data:`CLICK_CONTEXT_SETTINGS` shared context settings for all commands.
    * :func:`cli_info` subcommand reporting distribution metadata.
    * :func:`cli_fail` subcommand triggering a deterministic failure.
System Integration:
    Commands are registered with the root group in :mod:`lib_cli_exit_tools.cli`.
"""

from __future__ import annotations

import rich_click as click

from .. import __init__conf__
from .. import lib_cli_exit_tools

#: Help flag aliases applied to every Click command so documentation and CLI
#: behaviour stay consistent (`-h` mirrors `--help`).
#: Note: This uses dict literal syntax as required by Click framework API.
CLICK_CONTEXT_SETTINGS = {"help_option_names": ["-h", "--help"]}


@click.command("info", context_settings=CLICK_CONTEXT_SETTINGS)
def cli_info() -> None:
    """Display package metadata exported by :mod:`lib_cli_exit_tools.__init__conf__`.

    Why:
        Offer a zero-dependency way for users to confirm the installed version
        and provenance of the CLI.
    Side Effects:
        Writes formatted metadata to stdout.
    Examples:
        >>> from click.testing import CliRunner
        >>> from lib_cli_exit_tools.cli.group import cli
        >>> runner = CliRunner()
        >>> result = runner.invoke(cli, ["info"])
        >>> "Info for" in result.output
        True
    """
    __init__conf__.print_info()


@click.command("fail", context_settings=CLICK_CONTEXT_SETTINGS)
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
        >>> from lib_cli_exit_tools.cli.group import cli
        >>> runner = CliRunner()
        >>> result = runner.invoke(cli, ["fail"])
        >>> result.exit_code != 0
        True
        >>> "i should fail" in str(result.exception)
        True
    """

    lib_cli_exit_tools.i_should_fail()
