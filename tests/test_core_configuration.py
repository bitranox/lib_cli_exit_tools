"""Tests for the configuration module.

Each test verifies exactly one behavior of the configuration system:
- Default values and reset behavior
- Override context manager semantics
- Snapshot and restore operations
- Unknown field rejection
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from lib_cli_exit_tools.core import configuration as cfg


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def modified_config() -> Iterator[None]:
    """Modify all config fields to non-default values."""
    cfg.config.traceback = True
    cfg.config.exit_code_style = "sysexits"
    cfg.config.broken_pipe_exit_code = 0
    cfg.config.traceback_force_color = True
    yield
    cfg.reset_config()


# =============================================================================
# Reset Behavior
# =============================================================================


@pytest.mark.os_agnostic
def test_reset_restores_traceback_to_false(modified_config: None) -> None:
    cfg.reset_config()
    assert cfg.config.traceback is False


@pytest.mark.os_agnostic
def test_reset_restores_exit_code_style_to_errno(modified_config: None) -> None:
    cfg.reset_config()
    assert cfg.config.exit_code_style == "errno"


@pytest.mark.os_agnostic
def test_reset_restores_broken_pipe_exit_code_to_141(modified_config: None) -> None:
    cfg.reset_config()
    assert cfg.config.broken_pipe_exit_code == 141


@pytest.mark.os_agnostic
def test_reset_restores_traceback_force_color_to_false(modified_config: None) -> None:
    cfg.reset_config()
    assert cfg.config.traceback_force_color is False


# =============================================================================
# Override Context Manager
# =============================================================================


@pytest.mark.os_agnostic
def test_override_enables_traceback_inside_context(reset_config: None) -> None:
    with cfg.config_overrides(traceback=True):
        assert cfg.config.traceback is True


@pytest.mark.os_agnostic
def test_override_restores_traceback_after_context(reset_config: None) -> None:
    with cfg.config_overrides(traceback=True):
        pass
    assert cfg.config.traceback is False


@pytest.mark.os_agnostic
def test_override_enables_custom_broken_pipe_code_inside_context(reset_config: None) -> None:
    with cfg.config_overrides(broken_pipe_exit_code=0):
        assert cfg.config.broken_pipe_exit_code == 0


@pytest.mark.os_agnostic
def test_override_restores_broken_pipe_code_after_context(reset_config: None) -> None:
    with cfg.config_overrides(broken_pipe_exit_code=0):
        pass
    assert cfg.config.broken_pipe_exit_code == 141


@pytest.mark.os_agnostic
def test_override_can_change_multiple_fields_at_once(reset_config: None) -> None:
    with cfg.config_overrides(traceback=True, broken_pipe_exit_code=99):
        assert cfg.config.traceback is True
        assert cfg.config.broken_pipe_exit_code == 99


# =============================================================================
# Unknown Field Rejection
# =============================================================================


@pytest.mark.os_agnostic
def test_override_rejects_unknown_field_names() -> None:
    with pytest.raises(AttributeError, match="Unknown configuration fields"):
        with cfg.config_overrides(nonexistent_field=True):  # type: ignore[arg-type]
            pass


@pytest.mark.os_agnostic
def test_override_error_message_includes_field_name() -> None:
    with pytest.raises(AttributeError, match="imaginary"):
        with cfg.config_overrides(imaginary=42):  # type: ignore[arg-type]
            pass


# =============================================================================
# Snapshot Operations
# =============================================================================


@pytest.mark.os_agnostic
def test_snapshot_captures_current_traceback_value(reset_config: None) -> None:
    cfg.config.traceback = True
    snapshot = cfg._snapshot_current_settings()  # pyright: ignore[reportPrivateUsage]
    assert snapshot["traceback"] is True


@pytest.mark.os_agnostic
def test_snapshot_captures_current_exit_code_style(reset_config: None) -> None:
    cfg.config.exit_code_style = "sysexits"
    snapshot = cfg._snapshot_current_settings()  # pyright: ignore[reportPrivateUsage]
    assert snapshot["exit_code_style"] == "sysexits"


@pytest.mark.os_agnostic
def test_snapshot_captures_current_broken_pipe_code(reset_config: None) -> None:
    cfg.config.broken_pipe_exit_code = 77
    snapshot = cfg._snapshot_current_settings()  # pyright: ignore[reportPrivateUsage]
    assert snapshot["broken_pipe_exit_code"] == 77


@pytest.mark.os_agnostic
def test_snapshot_captures_current_force_color_value(reset_config: None) -> None:
    cfg.config.traceback_force_color = True
    snapshot = cfg._snapshot_current_settings()  # pyright: ignore[reportPrivateUsage]
    assert snapshot["traceback_force_color"] is True


@pytest.mark.os_agnostic
def test_snapshot_contains_exactly_four_fields() -> None:
    snapshot = cfg._snapshot_current_settings()  # pyright: ignore[reportPrivateUsage]
    assert len(snapshot) == 4


@pytest.mark.os_agnostic
def test_snapshot_keys_match_config_field_names() -> None:
    snapshot = cfg._snapshot_current_settings()  # pyright: ignore[reportPrivateUsage]
    expected_keys = {"traceback", "exit_code_style", "broken_pipe_exit_code", "traceback_force_color"}
    assert set(snapshot.keys()) == expected_keys
