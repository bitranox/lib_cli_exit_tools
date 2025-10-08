"""Shared pytest fixtures for lib_cli_exit_tools tests.

Purpose:
    Provide automatic configuration resets so tests remain isolated without
    repeating setup/teardown logic in each module.
Contents:
    * ``reset_config_state`` fixture restoring the global CLI configuration.
System Integration:
    Imported implicitly by every pytest module to enforce clean state across
    layered test suites.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from lib_cli_exit_tools.core.configuration import config_overrides, reset_config


@pytest.fixture(autouse=True)
def reset_config_state() -> Iterator[None]:
    """Ensure each test sees default configuration state and restores it."""

    reset_config()
    with config_overrides():
        yield
