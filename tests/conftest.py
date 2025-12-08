"""Shared pytest fixtures and configuration for lib_cli_exit_tools tests.

Provides:
    - Automatic OS-based test skipping via custom markers
    - Shared fixtures for CLI testing, ANSI stripping, and config isolation
    - Configuration reset fixtures to ensure test isolation
"""

from __future__ import annotations

import os
import re
import sys
from collections.abc import Callable, Iterator

import pytest
from click.testing import CliRunner

from lib_cli_exit_tools.core import configuration as cfg


# =============================================================================
# OS Detection Constants
# =============================================================================

IS_POSIX: bool = os.name == "posix"
IS_WINDOWS: bool = sys.platform == "win32"
IS_MACOS: bool = sys.platform == "darwin"

ANSI_ESCAPE_PATTERN: re.Pattern[str] = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


# =============================================================================
# Pytest Hooks for OS-Specific Marker Handling
# =============================================================================


def pytest_runtest_setup(item: pytest.Item) -> None:
    """Skip tests based on OS markers when running on incompatible platforms."""
    if item.get_closest_marker("posix_only") and not IS_POSIX:
        pytest.skip("test requires POSIX platform")

    if item.get_closest_marker("windows_only") and not IS_WINDOWS:
        pytest.skip("test requires Windows platform")

    if item.get_closest_marker("macos_only") and not IS_MACOS:
        pytest.skip("test requires macOS platform")


# =============================================================================
# CLI Testing Fixtures
# =============================================================================


@pytest.fixture
def cli_runner() -> CliRunner:
    """Provide a fresh Click test runner for CLI invocations."""
    return CliRunner()


@pytest.fixture
def strip_ansi() -> Callable[[str], str]:
    """Provide a helper to remove ANSI escape codes from terminal output."""

    def _strip(text: str) -> str:
        return ANSI_ESCAPE_PATTERN.sub("", text)

    return _strip


# =============================================================================
# Configuration Isolation Fixtures
# =============================================================================


@pytest.fixture
def reset_config() -> Iterator[None]:
    """Reset configuration to defaults before and after each test."""
    cfg.reset_config()
    yield
    cfg.reset_config()


@pytest.fixture
def preserve_traceback_state() -> Iterator[None]:
    """Snapshot and restore traceback configuration around a test."""
    original_traceback = cfg.config.traceback
    original_force_color = cfg.config.traceback_force_color
    try:
        yield
    finally:
        cfg.config.traceback = original_traceback
        cfg.config.traceback_force_color = original_force_color


@pytest.fixture
def isolated_traceback_config() -> Iterator[None]:
    """Ensure traceback flags are disabled for the duration of a test."""
    cfg.config.traceback = False
    cfg.config.traceback_force_color = False
    yield
    cfg.reset_config()


@pytest.fixture
def sysexits_mode() -> Iterator[None]:
    """Enable sysexits mode for the duration of a test."""
    cfg.config.exit_code_style = "sysexits"
    yield
    cfg.reset_config()
