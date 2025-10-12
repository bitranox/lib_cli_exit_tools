"""Shared pytest fixtures for CLI and module-entry tests."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator

import pytest
from click.testing import CliRunner

import lib_cli_exit_tools

TracebackState = tuple[bool, bool]
ConfigState = dict[str, bool]
ANSI_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")


@pytest.fixture
def cli_runner() -> CliRunner:
    """Provide a fresh :class:`CliRunner` per test."""

    return CliRunner()


@pytest.fixture
def strip_ansi() -> Callable[[str], str]:
    """Return a helper that strips ANSI escape sequences from a string."""

    def _strip(value: str) -> str:
        return ANSI_RE.sub("", value)

    return _strip


@pytest.fixture
def preserve_traceback_state() -> Iterator[None]:
    """Snapshot and restore the ``lib_cli_exit_tools`` traceback configuration."""

    snapshot: TracebackState = (
        bool(getattr(lib_cli_exit_tools.config, "traceback", False)),
        bool(getattr(lib_cli_exit_tools.config, "traceback_force_color", False)),
    )
    try:
        yield
    finally:
        (
            lib_cli_exit_tools.config.traceback,
            lib_cli_exit_tools.config.traceback_force_color,
        ) = snapshot


@pytest.fixture
def isolated_traceback_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset traceback flags to a known baseline before each test."""

    monkeypatch.setattr(lib_cli_exit_tools.config, "traceback", False, raising=False)
    monkeypatch.setattr(lib_cli_exit_tools.config, "traceback_force_color", False, raising=False)
