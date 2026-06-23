"""Tests for facade helper behaviors.

Each test verifies exactly one behavior of facade helpers:
- i_should_fail() raises RuntimeError
- config_overrides context manager applies and restores settings
- cli_session applies overrides during execution
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, cast

import pytest

import lib_cli_exit_tools
from lib_cli_exit_tools.application import runner as runner_mod


# =============================================================================
# Failure Helper
# =============================================================================


@pytest.mark.os_agnostic
def test_failure_helper_raises_runtime_error() -> None:
    with pytest.raises(RuntimeError):
        lib_cli_exit_tools.i_should_fail()


@pytest.mark.os_agnostic
def test_failure_helper_message_is_correct() -> None:
    with pytest.raises(RuntimeError, match="i should fail"):
        lib_cli_exit_tools.i_should_fail()


# =============================================================================
# Config Overrides - Traceback Setting
# =============================================================================


@pytest.mark.os_agnostic
def test_config_overrides_enables_traceback(reset_config: None) -> None:
    with lib_cli_exit_tools.config_overrides(traceback=True):
        assert lib_cli_exit_tools.config.traceback is True


@pytest.mark.os_agnostic
def test_config_overrides_restores_traceback(reset_config: None) -> None:
    with lib_cli_exit_tools.config_overrides(traceback=True):
        pass
    assert lib_cli_exit_tools.config.traceback is False


# =============================================================================
# Config Overrides - Broken Pipe Exit Code
# =============================================================================


@pytest.mark.os_agnostic
def test_config_overrides_changes_broken_pipe_code(reset_config: None) -> None:
    with lib_cli_exit_tools.config_overrides(broken_pipe_exit_code=0):
        assert lib_cli_exit_tools.config.broken_pipe_exit_code == 0


@pytest.mark.os_agnostic
def test_config_overrides_restores_broken_pipe_code(reset_config: None) -> None:
    with lib_cli_exit_tools.config_overrides(broken_pipe_exit_code=0):
        pass
    assert lib_cli_exit_tools.config.broken_pipe_exit_code == 141


# =============================================================================
# Config Overrides - Force Color Setting
# =============================================================================


@pytest.mark.os_agnostic
def test_config_overrides_enables_force_color(reset_config: None) -> None:
    with lib_cli_exit_tools.config_overrides(traceback_force_color=True):
        assert lib_cli_exit_tools.config.traceback_force_color is True


@pytest.mark.os_agnostic
def test_config_overrides_restores_force_color(reset_config: None) -> None:
    with lib_cli_exit_tools.config_overrides(traceback_force_color=True):
        pass
    assert lib_cli_exit_tools.config.traceback_force_color is False


# =============================================================================
# CLI Session - Overrides Application
# =============================================================================


class DummyCommand:
    """A minimal Click command stub for testing cli_session."""

    def __init__(self, behaviour: Callable[[], None]) -> None:
        self._behaviour = behaviour

    def main(
        self,
        *,
        args: Sequence[str] | None = None,
        prog_name: str | None = None,
        complete_var: str | None = None,
        standalone_mode: bool = False,
        **_: object,
    ) -> None:
        self._behaviour()


@pytest.mark.os_agnostic
def test_cli_session_applies_traceback_override(monkeypatch: pytest.MonkeyPatch, reset_config: None) -> None:
    states: list[bool] = []

    def fake_run_cli(
        command: runner_mod.ClickCommand,
        *,
        argv: Sequence[str] | None = None,
        prog_name: str | None = None,
        signal_specs: Sequence[object] | None = None,
        install_signals: bool = True,
        exception_handler: Callable[[BaseException], int] | None = None,
        signal_installer: Callable[[Sequence[object] | None], Callable[[], None]] | None = None,
    ) -> int:
        states.append(lib_cli_exit_tools.config.traceback)
        command.main(args=argv, prog_name=prog_name, standalone_mode=False)
        return 0

    monkeypatch.setattr(runner_mod, "run_cli", fake_run_cli)

    with lib_cli_exit_tools.cli_session(overrides={"traceback": True}) as execute:
        executor = cast(Callable[..., int], execute)
        executor(DummyCommand(lambda: None))

    assert states == [True]


@pytest.mark.os_agnostic
def test_cli_session_restores_traceback_after_exit(monkeypatch: pytest.MonkeyPatch, reset_config: None) -> None:
    def fake_run_cli(
        command: runner_mod.ClickCommand,
        *,
        argv: Sequence[str] | None = None,
        prog_name: str | None = None,
        signal_specs: Sequence[object] | None = None,
        install_signals: bool = True,
        exception_handler: Callable[[BaseException], int] | None = None,
        signal_installer: Callable[[Sequence[object] | None], Callable[[], None]] | None = None,
    ) -> int:
        command.main(args=argv, prog_name=prog_name, standalone_mode=False)
        return 0

    monkeypatch.setattr(runner_mod, "run_cli", fake_run_cli)

    with lib_cli_exit_tools.cli_session(overrides={"traceback": True}) as execute:
        executor = cast(Callable[..., int], execute)
        executor(DummyCommand(lambda: None))

    assert lib_cli_exit_tools.config.traceback is False


@pytest.mark.os_agnostic
def test_cli_session_returns_exit_code(monkeypatch: pytest.MonkeyPatch, reset_config: None) -> None:
    def fake_print_exception_message(*, trace_back: bool, length_limit: int, stream: Any | None = None) -> None:
        pass

    def fake_get_system_exit_code(exc: BaseException) -> int:
        return 99

    def fake_run_cli(
        command: runner_mod.ClickCommand,
        *,
        argv: Sequence[str] | None = None,
        prog_name: str | None = None,
        signal_specs: Sequence[object] | None = None,
        install_signals: bool = True,
        exception_handler: Callable[[BaseException], int] | None = None,
        signal_installer: Callable[[Sequence[object] | None], Callable[[], None]] | None = None,
    ) -> int:
        try:
            command.main(args=argv, prog_name=prog_name, standalone_mode=False)
        except RuntimeError as exc:
            if exception_handler is None:
                raise
            return exception_handler(exc)
        return 0

    monkeypatch.setattr(runner_mod, "print_exception_message", fake_print_exception_message)
    monkeypatch.setattr(runner_mod, "get_system_exit_code", fake_get_system_exit_code)
    monkeypatch.setattr(runner_mod, "run_cli", fake_run_cli)

    with lib_cli_exit_tools.cli_session(overrides={"traceback": True}) as execute:
        executor = cast(Callable[..., int], execute)
        exit_code = executor(DummyCommand(lambda: (_ for _ in ()).throw(RuntimeError("boom"))), argv=["info"])

    assert exit_code == 99


@pytest.mark.os_agnostic
def test_cli_session_applies_force_color_with_traceback(monkeypatch: pytest.MonkeyPatch, reset_config: None) -> None:
    states: list[tuple[bool, bool]] = []

    def fake_run_cli(
        command: runner_mod.ClickCommand,
        *,
        argv: Sequence[str] | None = None,
        prog_name: str | None = None,
        signal_specs: Sequence[object] | None = None,
        install_signals: bool = True,
        exception_handler: Callable[[BaseException], int] | None = None,
        signal_installer: Callable[[Sequence[object] | None], Callable[[], None]] | None = None,
    ) -> int:
        states.append((lib_cli_exit_tools.config.traceback, lib_cli_exit_tools.config.traceback_force_color))
        command.main(args=argv, prog_name=prog_name, standalone_mode=False)
        return 0

    monkeypatch.setattr(runner_mod, "run_cli", fake_run_cli)

    with lib_cli_exit_tools.cli_session(overrides={"traceback": True}) as execute:
        executor = cast(Callable[..., int], execute)
        executor(DummyCommand(lambda: None))

    assert states == [(True, True)]
