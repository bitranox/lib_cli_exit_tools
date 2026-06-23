"""Application orchestration for lib_cli_exit_tools.

Purpose:
    Coordinate core exit-code logic with adapter implementations (Click,
    signal handlers) while exposing a small surface for CLI entry points.
Contents:
    The `runner` module will host the refactored `run_cli` orchestration and any
    supporting protocols.
System Integration:
    Imports only from `lib_cli_exit_tools.core` and adapter packages, keeping the
    dependency direction consistent with Clean Architecture guidelines.
"""

from __future__ import annotations

__all__: list[str] = []
