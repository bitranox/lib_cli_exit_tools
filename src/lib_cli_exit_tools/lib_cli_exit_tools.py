"""Facade aggregating the exit-tooling helpers exposed by lib_cli_exit_tools.

Purpose:
    Provide a stable import location for configuration, signal handling, exit
    code translation, and CLI orchestration primitives after the refactor into
    layered modules.
Contents:
    * ``config`` from :mod:`lib_cli_exit_tools.core.configuration`.
    * ``config_overrides`` and ``reset_config`` helpers to manage configuration
      state safely during temporary tweaks.
    * ``get_system_exit_code`` from :mod:`lib_cli_exit_tools.core.exit_codes`.
    * ``handle_cli_exception`` and ``run_cli`` from
      :mod:`lib_cli_exit_tools.application.runner`.
    * :func:`i_should_fail` defined here for intentionally exercising error paths.
    * Signal helpers from :mod:`lib_cli_exit_tools.adapters.signals`.
System Integration:
    The CLI adapter (:mod:`lib_cli_exit_tools.cli`) and external consumers
    continue importing from this facade to avoid knowledge of the new package
    structure.
"""

from __future__ import annotations

from .adapters.signals import (
    CliSignalError,
    SigBreakInterrupt,
    SigIntInterrupt,
    SigTermInterrupt,
    SignalSpec,
    default_signal_specs,
    install_signal_handlers,
)
from .application.runner import (
    flush_streams,
    handle_cli_exception,
    print_exception_message,
    run_cli,
)
from .core.configuration import config, config_overrides, reset_config
from .core.exit_codes import get_system_exit_code

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
    "i_should_fail",
    "run_cli",
    "config_overrides",
    "reset_config",
]

PUBLIC_API = tuple(__all__)


def i_should_fail() -> None:
    """Raise :class:`RuntimeError` to exercise error-handling flows.

    Why:
        Provide a deterministic failure path so engineers can verify traceback
        toggles, exit-code translation, and structured error reporting during
        manual or automated testing.
    Raises:
        RuntimeError: Always raised with a stable message for assertion-friendly
            diagnostics.
    Examples:
        >>> i_should_fail()
        Traceback (most recent call last):
        ...
        RuntimeError: i should fail
    """

    raise RuntimeError("i should fail")
