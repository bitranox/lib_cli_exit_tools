"""Behaviour-layer stories verifying facade helpers behave as expected."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, cast

import pytest

import lib_cli_exit_tools
from lib_cli_exit_tools.application import runner as runner_mod


@pytest.mark.os_agnostic
def test_when_failure_helper_is_called_it_raises_runtime_error() -> None:
    with pytest.raises(RuntimeError, match="i should fail"):
        lib_cli_exit_tools.i_should_fail()


@pytest.mark.os_agnostic
def test_config_overrides_restore_runtime_defaults() -> None:
    lib_cli_exit_tools.reset_config()

    baseline = (
        lib_cli_exit_tools.config.traceback,
        lib_cli_exit_tools.config.broken_pipe_exit_code,
        lib_cli_exit_tools.config.traceback_force_color,
    )

    with lib_cli_exit_tools.config_overrides(traceback=True, broken_pipe_exit_code=0, traceback_force_color=True):
        assert lib_cli_exit_tools.config.traceback is True
        assert lib_cli_exit_tools.config.broken_pipe_exit_code == 0
        assert lib_cli_exit_tools.config.traceback_force_color is True

    assert (
        lib_cli_exit_tools.config.traceback,
        lib_cli_exit_tools.config.broken_pipe_exit_code,
        lib_cli_exit_tools.config.traceback_force_color,
    ) == baseline


@pytest.mark.os_agnostic
def test_cli_session_applies_overrides_and_restores(monkeypatch: pytest.MonkeyPatch) -> None:
    lib_cli_exit_tools.reset_config()

    states: list[tuple[bool, bool]] = []
    summaries: list[tuple[bool, int]] = []

    def fake_print_exception_message(*, trace_back: bool, length_limit: int, stream: Any | None = None) -> None:
        summaries.append((trace_back, length_limit))

    def fake_get_system_exit_code(exc: BaseException) -> int:
        return 99

    monkeypatch.setattr(runner_mod, "print_exception_message", fake_print_exception_message)
    monkeypatch.setattr(runner_mod, "get_system_exit_code", fake_get_system_exit_code)

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
        try:
            command.main(args=argv, prog_name=prog_name, standalone_mode=False)
        except RuntimeError as exc:  # noqa: BLE001 - intentional test trigger
            if exception_handler is None:
                raise
            return exception_handler(exc)
        return 0

    monkeypatch.setattr(runner_mod, "run_cli", fake_run_cli)

    class DummyCommand:
        def main(
            self,
            *,
            args: Sequence[str] | None = None,
            prog_name: str | None = None,
            complete_var: str | None = None,
            standalone_mode: bool = False,
            **_: object,
        ) -> None:
            raise RuntimeError("boom")

    with lib_cli_exit_tools.cli_session(overrides={"traceback": True}) as execute:
        executor = cast(Callable[..., int], execute)
        exit_code = executor(DummyCommand(), argv=["info"])

    assert exit_code == 99
    assert states == [(True, True)]
    assert summaries == [(True, 10_000)]
    assert lib_cli_exit_tools.config.traceback is False
    assert lib_cli_exit_tools.config.traceback_force_color is False
