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

# --- Public surface re-exports (backward compatibility) ---
from .commands import cli_fail as cli_fail
from .commands import cli_info as cli_info
from .group import CliContextState as CliContextState
from .group import cli as cli
from .group import main as main

# --- Register subcommands with the root group ---
cli.add_command(cli_info)
cli.add_command(cli_fail)
