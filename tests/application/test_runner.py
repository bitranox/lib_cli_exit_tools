"""Runner helpers read like instructions."""

from __future__ import annotations

import io
from collections.abc import Callable, Sequence
from typing import TextIO

import click
import pytest

from lib_cli_exit_tools.adapters.signals import SignalSpec, SigIntInterrupt
from lib_cli_exit_tools.application import runner as runner_module
from lib_cli_exit_tools.application.runner import (
    flush_streams,
    handle_cli_exception,
    print_exception_message,
    run_cli,
)
from lib_cli_exit_tools.core.configuration import config


pytestmark = pytest.mark.usefixtures("reset_config_state")


@pytest.fixture(autouse=True)
def stub_signal_install(monkeypatch: pytest.MonkeyPatch) -> None:
    def install_stub(specs: Sequence[SignalSpec] | None = None) -> Callable[[], None]:  # noqa: ARG001 - signature parity
        return lambda: None

    monkeypatch.setattr(runner_module, "install_signal_handlers", install_stub)


def test_handle_cli_exception_for_signal_echoes_message(capsys: pytest.CaptureFixture[str]) -> None:
    code = handle_cli_exception(SigIntInterrupt())
    _out, err = capsys.readouterr()
    assert code == 130 and "Aborted" in err


def test_handle_cli_exception_for_broken_pipe_obeys_configured_code(capsys: pytest.CaptureFixture[str]) -> None:
    config.broken_pipe_exit_code = 141
    code = handle_cli_exception(BrokenPipeError())
    out, err = capsys.readouterr()
    assert code == 141 and out == "" and err == ""


def test_handle_cli_exception_for_generic_error_calls_printer_and_resolver(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: dict[str, object] = {}

    def fake_printer(*_: object, **kwargs: object) -> None:
        calls["printed"] = kwargs.get("trace_back", False)

    def fake_resolver(exc: BaseException) -> int:
        calls["exc"] = exc
        return 55

    monkeypatch.setattr(runner_module, "print_exception_message", fake_printer)
    monkeypatch.setattr(runner_module, "get_system_exit_code", fake_resolver)
    config.traceback = False

    err = RuntimeError("boom")
    assert handle_cli_exception(err) == 55
    assert calls == {"printed": False, "exc": err}


def test_handle_cli_exception_in_traceback_mode_requests_full_trace(monkeypatch: pytest.MonkeyPatch) -> None:
    call_details: dict[str, object] = {}

    def fake_printer(*_: object, **kwargs: object) -> None:
        call_details["trace_back"] = kwargs.get("trace_back")

    monkeypatch.setattr(runner_module, "print_exception_message", fake_printer)

    def fake_resolver(_: BaseException) -> int:
        return 17

    monkeypatch.setattr(runner_module, "get_system_exit_code", fake_resolver)
    config.traceback = True

    assert handle_cli_exception(RuntimeError("boom")) == 17
    assert call_details == {"trace_back": True}


def test_handle_cli_exception_recovers_from_old_printer_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[str] = []

    def old_printer() -> None:
        calls.append("legacy")

    def resolver(_: BaseException) -> int:
        return 3

    monkeypatch.setattr(runner_module, "print_exception_message", old_printer)
    monkeypatch.setattr(runner_module, "get_system_exit_code", resolver)
    config.traceback = True

    assert handle_cli_exception(RuntimeError("boom")) == 3
    assert calls == ["legacy"]


def test_handle_cli_exception_with_click_exception_returns_click_exit_code() -> None:
    class Fussy(click.ClickException):
        def __init__(self) -> None:
            super().__init__("fussy")
            self.exit_code = 5

    assert handle_cli_exception(Fussy()) == 5


def test_handle_cli_exception_with_system_exit_respects_payload() -> None:
    assert handle_cli_exception(SystemExit(22)) == 22


def test_print_exception_message_writes_summary() -> None:
    try:
        raise FileNotFoundError("missing.txt")
    except FileNotFoundError:
        buffer = io.StringIO()
        print_exception_message(trace_back=False, stream=buffer)
    assert "missing.txt" in buffer.getvalue()


def test_print_exception_message_writes_traceback() -> None:
    try:
        raise ValueError("broken")
    except ValueError:
        buffer = io.StringIO()
        print_exception_message(trace_back=True, stream=buffer)
    assert "Traceback" in buffer.getvalue()


def test_print_exception_message_respects_force_colour(monkeypatch: pytest.MonkeyPatch) -> None:
    recorded: dict[str, object] = {}

    class DummyConsole:
        def __init__(self, *, file: TextIO, force_terminal: bool | None, color_system: str | None, soft_wrap: bool) -> None:
            recorded.update(
                {
                    "file": file,
                    "force_terminal": force_terminal,
                    "color_system": color_system,
                    "soft_wrap": soft_wrap,
                }
            )
            self.file = file

        def print(self, renderable: object) -> None:  # pragma: no cover - mocked side effect only
            recorded["renderable"] = renderable

    monkeypatch.setattr(runner_module, "Console", DummyConsole, raising=False)

    def fake_traceback(*args: object, **_: object) -> str:
        return "trace"

    monkeypatch.setattr(runner_module.Traceback, "from_exception", fake_traceback)
    config.traceback_force_color = True

    try:
        raise ValueError("boom")
    except ValueError:
        print_exception_message(True, stream=io.StringIO())

    assert recorded.get("force_terminal") is True
    assert recorded.get("color_system") == "auto"


def test_print_exception_message_echoes_subprocess_output(capsys: pytest.CaptureFixture[str]) -> None:
    class FakeError(Exception):
        stdout = b"hello"

    try:
        raise FakeError()
    except FakeError:
        print_exception_message(trace_back=False)

    _out, err = capsys.readouterr()
    assert "STDOUT: hello" in err


def test_flush_streams_is_a_quiet_noop() -> None:
    flush_streams()


def test_run_cli_success_returns_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    @click.command()
    def cli_cmd() -> None:
        click.echo("ok")

    exit_code = run_cli(cli_cmd, argv=["--help"], install_signals=False)
    assert exit_code == 0


def test_run_cli_surfaces_click_exception_exit_code() -> None:
    @click.command()
    def cli_cmd() -> None:
        raise click.ClickException("fail")

    exit_code = run_cli(cli_cmd, argv=[], install_signals=False)
    assert exit_code == 1


def test_run_cli_accepts_custom_exception_handler() -> None:
    @click.command()
    def cli_cmd() -> None:
        raise RuntimeError("boom")

    def custom_handler(exc: BaseException) -> int:
        assert isinstance(exc, RuntimeError)
        return 99

    exit_code = run_cli(cli_cmd, argv=[], exception_handler=custom_handler, install_signals=False)
    assert exit_code == 99


def test_run_cli_uses_custom_signal_installer(monkeypatch: pytest.MonkeyPatch) -> None:
    @click.command()
    def cli_cmd() -> None:
        pass

    installed: list[Sequence[SignalSpec]] = []

    def custom_installer(specs: Sequence[SignalSpec] | None) -> Callable[[], None]:
        installed.append(tuple(specs or ()))
        return lambda: installed.append(())

    run_cli(cli_cmd, argv=[], signal_installer=custom_installer, install_signals=True)
    assert installed and installed[-1] == ()
