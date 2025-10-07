"""Shared pytest fixtures for lib_cli_exit_tools tests.

Purpose:
    Provide automatic configuration resets so tests remain isolated without
    repeating setup/teardown logic in each module.
Contents:
    * ``reset_config`` fixture restoring the global CLI configuration.
System Integration:
    Imported implicitly by every pytest module to enforce clean state across
    layered test suites.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from lib_cli_exit_tools.core.configuration import config


@pytest.fixture(autouse=True)
def reset_config() -> Iterator[None]:
    """Restore global CLI configuration between tests."""

    traceback_value = config.traceback
    exit_code_style_value = config.exit_code_style
    broken_pipe_exit_code_value = config.broken_pipe_exit_code
    traceback_force_color_value = config.traceback_force_color
    try:
        yield
    finally:
        config.traceback = traceback_value
        config.exit_code_style = exit_code_style_value
        config.broken_pipe_exit_code = broken_pipe_exit_code_value
        config.traceback_force_color = traceback_force_color_value
