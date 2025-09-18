"""Module execution entry point for ``python -m lib_cli_exit_tools``.

Delegates to :func:`lib_cli_exit_tools.cli.main` so module execution behaves the
same as the installed console script.
"""

from . import cli

if __name__ == "__main__":
    # Delegate to the CLI entry point and propagate its exit code.
    raise SystemExit(cli.main())
