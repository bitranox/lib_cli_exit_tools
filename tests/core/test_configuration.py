"""Configuration helpers tell a simple story."""

from __future__ import annotations

import pytest

from lib_cli_exit_tools.core.configuration import config, config_overrides, reset_config


pytestmark = pytest.mark.usefixtures("reset_config_state")


def test_config_overrides_toggles_traceback_like_a_switch() -> None:
    baseline = config.traceback
    with config_overrides(traceback=not baseline):
        assert config.traceback is (not baseline)
    assert config.traceback is baseline


def test_config_overrides_lends_custom_broken_pipe_exit_code() -> None:
    baseline = config.broken_pipe_exit_code
    with config_overrides(broken_pipe_exit_code=999):
        assert config.broken_pipe_exit_code == 999
    assert config.broken_pipe_exit_code == baseline


def test_config_overrides_allows_manual_mutation_but_restores_defaults() -> None:
    baseline_style = config.exit_code_style
    baseline_colour = config.traceback_force_color

    with config_overrides():
        config.exit_code_style = "sysexits"
        config.traceback_force_color = not baseline_colour

    assert config.exit_code_style == baseline_style
    assert config.traceback_force_color is baseline_colour


def test_config_overrides_refuses_unknown_fields() -> None:
    with pytest.raises(AttributeError, match="Unknown configuration fields"):
        with config_overrides(nonexistent=True):  # type: ignore[arg-type]
            pass


def test_reset_config_returns_to_defaults_after_manual_changes() -> None:
    reset_config()
    baseline_traceback = config.traceback
    baseline_style = config.exit_code_style
    baseline_broken_pipe = config.broken_pipe_exit_code

    config.traceback = not baseline_traceback
    config.exit_code_style = "sysexits"
    config.broken_pipe_exit_code = baseline_broken_pipe + 5

    reset_config()

    assert config.traceback is baseline_traceback
    assert config.exit_code_style == baseline_style
    assert config.broken_pipe_exit_code == baseline_broken_pipe


def test_config_overrides_can_nest_and_restore_in_sequence() -> None:
    reset_config()
    outer_traceback = config.traceback

    with config_overrides(traceback=not outer_traceback):
        inner_broken_pipe = config.broken_pipe_exit_code
        with config_overrides(broken_pipe_exit_code=inner_broken_pipe + 1):
            assert config.traceback is (not outer_traceback)
            assert config.broken_pipe_exit_code == inner_broken_pipe + 1
        assert config.broken_pipe_exit_code == inner_broken_pipe

    assert config.traceback is outer_traceback
