"""Public re-export surface for lib_cli_exit_tools helpers.

Purpose:
    Provide a stable import path for consumers (`from lib_cli_exit_tools import run_cli`).
Contents:
    Re-exports signal helpers, configuration, and CLI orchestration functions.
System Integration:
    Keeps the package interface aligned with the module reference documented in
    ``docs/system-design/module_reference.md`` while hiding implementation modules.
"""

from __future__ import annotations

from . import lib_cli_exit_tools as _facade

# Re-export core helpers while keeping a single authoritative list of names in
# the facade module. Attributes are assigned explicitly so static type checkers
# understand the exports, while the debug assertion keeps this module aligned
# with the facade surface.
CliSignalError = _facade.CliSignalError
SigBreakInterrupt = _facade.SigBreakInterrupt
SigIntInterrupt = _facade.SigIntInterrupt
SigTermInterrupt = _facade.SigTermInterrupt
SignalSpec = _facade.SignalSpec
config = _facade.config
config_overrides = _facade.config_overrides
default_signal_specs = _facade.default_signal_specs
flush_streams = _facade.flush_streams
get_system_exit_code = _facade.get_system_exit_code
handle_cli_exception = _facade.handle_cli_exception
i_should_fail = _facade.i_should_fail
install_signal_handlers = _facade.install_signal_handlers
print_exception_message = _facade.print_exception_message
reset_config = _facade.reset_config
run_cli = _facade.run_cli

__all__ = list(_facade.PUBLIC_API)  # pyright: ignore[reportUnsupportedDunderAll]

if __debug__:
    exported = {name for name in __all__ if name in globals()}
    if len(exported) != len(__all__):
        missing = sorted(set(__all__) - exported)
        raise ImportError(f"lib_cli_exit_tools exports out of sync: missing {missing}")
    del exported

del _facade
