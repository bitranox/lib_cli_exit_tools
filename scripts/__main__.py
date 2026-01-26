"""Composition root for the scripts CLI.

Installs a SIGINT handler so Ctrl-C exits with POSIX code 130
instead of Click's default Abort (exit 1), then delegates to the
CLI entry point.
"""

from __future__ import annotations

import signal
import sys
from types import FrameType

from .cli import main as cli_main

_EXIT_SIGINT = 130


def _handle_sigint(_signum: int, _frame: FrameType | None) -> None:
    """Raise SystemExit(130) on SIGINT, bypassing Click's Abort handler."""
    sys.exit(_EXIT_SIGINT)


def _install_signal_handlers() -> None:
    """Wire POSIX signal handlers before the CLI takes over."""
    signal.signal(signal.SIGINT, _handle_sigint)


def main() -> None:
    """Composition root: install signal handlers, then run the CLI."""
    _install_signal_handlers()
    cli_main()


if __name__ == "__main__":  # pragma: no cover
    main()
