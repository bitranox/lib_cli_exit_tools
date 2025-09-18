"""Public re-export surface for lib_cli_exit_tools helpers.

Purpose:
    Provide a stable import path for consumers (`from lib_cli_exit_tools import run_cli`).
Contents:
    Re-exports signal helpers, configuration, and CLI orchestration functions.
System Integration:
    Keeps the package interface aligned with the module reference documented in
    ``docs/system-design/reference.md`` while hiding implementation modules.
"""

from __future__ import annotations

# Re-export core helpers so consumers avoid deep imports.
from .lib_cli_exit_tools import (
    CliSignalError,
    SigBreakInterrupt,
    SigIntInterrupt,
    SigTermInterrupt,
    SignalSpec,
    config,
    default_signal_specs,
    flush_streams,
    get_system_exit_code,
    handle_cli_exception,
    install_signal_handlers,
    print_exception_message,
    run_cli,
)

#: Public API surface guaranteed by semantic versioning.
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
