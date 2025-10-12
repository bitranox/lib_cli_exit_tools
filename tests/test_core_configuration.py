from __future__ import annotations

import pytest

from lib_cli_exit_tools.core import configuration as cfg


@pytest.mark.os_agnostic
def test_when_config_is_reset_every_field_returns_to_default() -> None:
    cfg.config.traceback = True
    cfg.config.exit_code_style = "sysexits"
    cfg.config.broken_pipe_exit_code = 0
    cfg.config.traceback_force_color = True

    cfg.reset_config()

    assert cfg.config == cfg._Config()  # pyright: ignore[reportPrivateUsage]


@pytest.mark.os_agnostic
def test_when_config_overrides_apply_the_previous_state_returns_afterwards() -> None:
    before = cfg._snapshot_current_settings()  # pyright: ignore[reportPrivateUsage]

    with cfg.config_overrides(traceback=True, broken_pipe_exit_code=0):
        assert cfg.config.traceback is True
        assert cfg.config.broken_pipe_exit_code == 0

    after = cfg._snapshot_current_settings()  # pyright: ignore[reportPrivateUsage]
    assert after == before


@pytest.mark.os_agnostic
def test_when_config_override_uses_unknown_field_an_attribute_error_surfaces() -> None:
    with pytest.raises(AttributeError, match="Unknown configuration fields"):
        with cfg.config_overrides(spellcheck=True):  # type: ignore[arg-type]
            pass


@pytest.mark.os_agnostic
def test_when_config_snapshot_is_taken_it_matches_current_values() -> None:
    snapshot = cfg._snapshot_current_settings()  # pyright: ignore[reportPrivateUsage]
    assert snapshot == {
        "traceback": cfg.config.traceback,
        "exit_code_style": cfg.config.exit_code_style,
        "broken_pipe_exit_code": cfg.config.broken_pipe_exit_code,
        "traceback_force_color": cfg.config.traceback_force_color,
    }
