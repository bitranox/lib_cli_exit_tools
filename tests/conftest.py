"""Shared pytest fixtures for lib_cli_exit_tools tests.

Purpose:
    Provide automatic configuration resets so tests remain isolated without
    repeating setup/teardown logic in each module.
Contents:
    * `_reset_config` fixture restoring the global CLI configuration.
System Integration:
    Imported implicitly by every pytest module to enforce clean state across
    layered test suites.
"""

from __future__ import annotations

import pytest

from lib_cli_exit_tools.core.configuration import _Config, config


@pytest.fixture(autouse=True)
def _reset_config() -> None:
    """Restore global CLI configuration between tests."""

    original = _Config(
        traceback=config.traceback,
        exit_code_style=config.exit_code_style,
        broken_pipe_exit_code=config.broken_pipe_exit_code,
        traceback_force_color=config.traceback_force_color,
    )
    try:
        yield
    finally:
        config.traceback = original.traceback
        config.exit_code_style = original.exit_code_style
        config.broken_pipe_exit_code = original.broken_pipe_exit_code
        config.traceback_force_color = original.traceback_force_color
