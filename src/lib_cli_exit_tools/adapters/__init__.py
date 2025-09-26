"""Adapter layer for lib_cli_exit_tools.

Purpose:
    Provide integration points with concrete frameworks (Click, Rich, signal
    handlers) while delegating policy decisions to the core module.
Contents:
    Modules added here will contain Click helpers, signal installers, and other
    I/O-centric code paths.
System Integration:
    Imported by the application layer to wire concrete behaviour without
    violating dependency rules.
"""

from __future__ import annotations

__all__: list[str] = []
