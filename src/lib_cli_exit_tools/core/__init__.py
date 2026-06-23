"""Core domain logic for lib_cli_exit_tools.

Purpose:
    Host configuration dataclasses, exit-code mapping helpers, and other
    framework-agnostic primitives consumed by higher layers.
Contents:
    Modules extracted from the legacy monolith will expose configuration
    objects and pure helpers for exit handling.
System Integration:
    Intended to be imported by application orchestration and adapters without
    depending on Click or other I/O frameworks.
"""

from __future__ import annotations

__all__: list[str] = []
