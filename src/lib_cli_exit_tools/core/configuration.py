"""Runtime configuration primitives for lib_cli_exit_tools.

Purpose:
    Expose the mutable configuration dataclass shared across the package so
    adapters can toggle behaviour (tracebacks, exit codes, broken-pipe
    semantics) without re-implementing global state.
Contents:
    * :class:`_Config` – dataclass capturing toggleable runtime flags.
    * :data:`config` – module-level singleton mutated by CLI adapters and tests.
    * :func:`config_overrides` – context manager that snapshots and restores
      configuration state for embedders and tests.
    * :func:`reset_config` – helper that restores defaults defined by
      :class:`_Config`.
System Integration:
    Imported by higher layers (`application.runner`, `adapters.click_adapter`)
    to align behaviour while keeping the configuration schema centralized. The
    additional helpers remove the need for ad-hoc fixtures when temporarily
    tweaking settings in multi-layer integrations.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass, fields
from typing import Literal

__all__ = ["_Config", "config", "config_overrides", "reset_config"]


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


def _field_names() -> tuple[str, ...]:
    """Return the ordered configuration field names."""

    return tuple(field.name for field in fields(_Config))


def _default_values() -> Mapping[str, object]:
    """Return the canonical configuration defaults as a mapping."""

    defaults = _Config()
    return {name: getattr(defaults, name) for name in _field_names()}


def _snapshot_current_settings() -> dict[str, object]:
    """Capture the current configuration values."""

    return {name: getattr(config, name) for name in _field_names()}


def _restore_settings(snapshot: Mapping[str, object]) -> None:
    """Bring :data:`config` back to the provided snapshot."""

    for name, value in snapshot.items():
        setattr(config, name, value)


def _reject_unknown_fields(overrides: Mapping[str, object]) -> None:
    """Guard against typos in override names."""

    known = set(_field_names())
    unknown = set(overrides) - known
    if unknown:
        raise AttributeError(f"Unknown configuration fields: {sorted(unknown)}")


def reset_config() -> None:
    """Restore the shared configuration to its default values."""

    _restore_settings(_default_values())


@contextmanager
def config_overrides(**overrides: object) -> Iterator[_Config]:
    """Snapshot configuration state and optionally apply temporary overrides."""

    _reject_unknown_fields(overrides)
    snapshot = _snapshot_current_settings()

    for name, value in overrides.items():
        setattr(config, name, value)

    try:
        yield config
    finally:
        _restore_settings(snapshot)
