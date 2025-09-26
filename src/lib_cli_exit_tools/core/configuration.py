"""Runtime configuration primitives for lib_cli_exit_tools.

Purpose:
    Expose the mutable configuration dataclass shared across the package so
    adapters can toggle behaviour (tracebacks, exit codes, broken-pipe
    semantics) without re-implementing global state.
Contents:
    * :class:`_Config` – dataclass capturing toggleable runtime flags.
    * :data:`config` – module-level singleton mutated by CLI adapters and tests.
System Integration:
    Imported by higher layers (`application.runner`, `adapters.click_adapter`)
    to align behaviour while keeping the configuration schema centralized.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

__all__ = ["_Config", "config"]


@dataclass(slots=True)
class _Config:
    """Centralized runtime flags shared across all CLI executions.

    Why:
        Prevent each CLI adapter from re-implementing toggles for traceback
        emission and exit-code semantics. The Click adapter mutates these fields
        once per process based on global command options.
    What:
        Stores the behavioural switches consulted by error printers and
        exit-code helpers. Values are mutated in place so that successive calls
        reuse the same configuration.
    Fields:
        traceback: Enables stack-trace passthrough when ``True`` to aid
            debugging without altering default UX for end users.
        exit_code_style: Selects the exit-code mapping strategy, allowing
            consumers to opt into BSD ``sysexits`` values when shell scripts rely
            on them.
        broken_pipe_exit_code: Exit code returned when a ``BrokenPipeError``
            occurs; defaults to ``141`` so pipelines can detect truncated
            output.
        traceback_force_color: Force Rich to emit ANSI-coloured tracebacks even
            when stdout/stderr are not detected as TTYs.
    Side Effects:
        Mutations are process wide because :data:`config` exports a module-level
        instance. Callers should restore values in tests to avoid leakage.
    """

    traceback: bool = False
    exit_code_style: Literal["errno", "sysexits"] = "errno"
    broken_pipe_exit_code: int = 141
    traceback_force_color: bool = False


#: Shared configuration singleton consulted by CLI orchestration helpers.
config = _Config()
