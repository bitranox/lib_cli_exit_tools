"""The runner module is rehearsed in carefully worded verses."""

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
from lib_cli_exit_tools.core.configuration import config_overrides


pytestmark = [
    pytest.mark.usefixtures("reset_config_state"),
    pytest.mark.os_agnostic,
]


def test_when_sigint_interrupts_the_exit_code_is_one_hundred_thirty(capsys: pytest.CaptureFixture[str]) -> None:
    assert handle_cli_exception(SigIntInterrupt()) == 130
    capsys.readouterr()  # drain output for cleanliness


def test_when_sigint_interrupts_the_message_mentions_the_abort(capsys: pytest.CaptureFixture[str]) -> None:
    handle_cli_exception(SigIntInterrupt())
    _out, err = capsys.readouterr()
    assert "Aborted" in err


def test_when_broken_pipe_occurs_its_exit_code_follows_configuration() -> None:
    with config_overrides(broken_pipe_exit_code=141):
        assert handle_cli_exception(BrokenPipeError()) == 141


def test_when_broken_pipe_occurs_it_makes_no_noise(capsys: pytest.CaptureFixture[str]) -> None:
    with config_overrides(broken_pipe_exit_code=141):
        handle_cli_exception(BrokenPipeError())
    out, err = capsys.readouterr()
    assert out + err == ""


def test_when_generic_error_arrives_the_resolver_result_is_returned(monkeypatch: pytest.MonkeyPatch) -> None:
    def silent_printer(*_: object, **__: object) -> None:
        return None

    def return_fifty_five(exc: BaseException) -> int:
        return 55

    monkeypatch.setattr(runner_module, "print_exception_message", silent_printer)
    monkeypatch.setattr(runner_module, "get_system_exit_code", return_fifty_five)
    assert handle_cli_exception(RuntimeError("boom")) == 55


def test_when_traceback_is_disabled_the_printer_receives_false(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    def remember_traceback(*_: object, **kwargs: object) -> None:
        seen["trace_back"] = kwargs.get("trace_back")

    def return_zero(exc: BaseException) -> int:
        return 0

    monkeypatch.setattr(runner_module, "print_exception_message", remember_traceback)
    monkeypatch.setattr(runner_module, "get_system_exit_code", return_zero)
    handle_cli_exception(RuntimeError("boom"))
    assert seen["trace_back"] is False


def test_when_traceback_is_enabled_the_printer_receives_true(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    def remember_traceback(*_: object, **kwargs: object) -> None:
        seen["trace_back"] = kwargs.get("trace_back")

    def return_zero(exc: BaseException) -> int:
        return 0

    monkeypatch.setattr(runner_module, "print_exception_message", remember_traceback)
    monkeypatch.setattr(runner_module, "get_system_exit_code", return_zero)
    with config_overrides(traceback=True):
        handle_cli_exception(RuntimeError("boom"))
    assert seen["trace_back"] is True


def test_when_legacy_printer_signature_exists_the_exit_code_is_still_returned(monkeypatch: pytest.MonkeyPatch) -> None:
    def legacy_printer() -> None:
        return None

    def return_three(exc: BaseException) -> int:
        return 3

    monkeypatch.setattr(runner_module, "print_exception_message", legacy_printer)
    monkeypatch.setattr(runner_module, "get_system_exit_code", return_three)
    assert handle_cli_exception(RuntimeError("boom")) == 3


def test_when_legacy_printer_signature_exists_it_is_invoked(monkeypatch: pytest.MonkeyPatch) -> None:
    invoked: list[str] = []

    def legacy_printer() -> None:
        invoked.append("legacy")

    def return_zero(exc: BaseException) -> int:
        return 0

    monkeypatch.setattr(runner_module, "print_exception_message", legacy_printer)
    monkeypatch.setattr(runner_module, "get_system_exit_code", return_zero)
    handle_cli_exception(RuntimeError("boom"))
    assert invoked == ["legacy"]


def test_when_click_exception_is_raised_its_exit_code_is_honoured() -> None:
    class Fussy(click.ClickException):
        def __init__(self) -> None:
            super().__init__("fussy")
            self.exit_code = 5

    assert handle_cli_exception(Fussy()) == 5


def test_when_system_exit_is_raised_its_payload_is_returned() -> None:
    assert handle_cli_exception(SystemExit(22)) == 22


def test_when_summary_is_requested_the_missing_filename_is_spoken() -> None:
    try:
        raise FileNotFoundError("missing.txt")
    except FileNotFoundError:
        buffer = io.StringIO()
        print_exception_message(trace_back=False, stream=buffer)
    assert "missing.txt" in buffer.getvalue()


def test_when_traceback_mode_is_default_and_enabled_the_traceback_appears() -> None:
    with config_overrides(traceback=True):
        try:
            raise ValueError("boom")
        except ValueError:
            buffer = io.StringIO()
            print_exception_message(stream=buffer)
    rendered = buffer.getvalue()
    assert "Traceback" in rendered and "most recent call last" in rendered


def test_when_traceback_is_forced_true_the_traceback_is_printed() -> None:
    try:
        raise ValueError("broken")
    except ValueError:
        buffer = io.StringIO()
        print_exception_message(trace_back=True, stream=buffer)
    rendered = buffer.getvalue()
    assert "Traceback" in rendered and "most recent call last" in rendered


def test_when_summary_is_too_long_it_is_marked_truncated() -> None:
    try:
        raise RuntimeError("overflow " * 20)
    except RuntimeError:
        buffer = io.StringIO()
        print_exception_message(trace_back=False, length_limit=20, stream=buffer)
    assert "TRUNCATED" in buffer.getvalue()


def test_when_no_exception_is_active_nothing_is_written() -> None:
    buffer = io.StringIO()
    print_exception_message(stream=buffer)
    assert buffer.getvalue() == ""


def test_when_force_colour_is_requested_the_console_is_forced(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    class DummyConsole:
        def __init__(self, *, file: TextIO, force_terminal: bool | None, color_system: str | None, soft_wrap: bool) -> None:
            captured["force_terminal"] = force_terminal
            captured["color_system"] = color_system
            self.file = file

        def print(self, renderable: object) -> None:  # pragma: no cover - effect recorded via captured dict
            captured["renderable"] = renderable

    def fake_traceback(*args: object, **kwargs: object) -> str:
        return "trace"

    monkeypatch.setattr(runner_module, "Console", DummyConsole, raising=False)
    monkeypatch.setattr(runner_module.Traceback, "from_exception", fake_traceback)
    with config_overrides(traceback_force_color=True):
        try:
            raise ValueError("boom")
        except ValueError:
            print_exception_message(True, stream=io.StringIO())
    assert (captured.get("force_terminal"), captured.get("color_system")) == (True, "auto")


def test_when_subprocess_output_is_present_it_is_echoed_to_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    class WithStdout(Exception):
        stdout = b"hello"

    try:
        raise WithStdout()
    except WithStdout:
        print_exception_message(trace_back=False)
    _out, err = capsys.readouterr()
    assert "STDOUT: hello" in err


def test_when_subprocess_output_is_none_it_is_ignored(capsys: pytest.CaptureFixture[str]) -> None:
    class WithNone(Exception):
        stdout = None

    try:
        raise WithNone()
    except WithNone:
        print_exception_message(trace_back=False)
    _out, err = capsys.readouterr()
    assert "STDOUT" not in err


def test_when_subprocess_output_is_unexpected_type_it_is_ignored(capsys: pytest.CaptureFixture[str]) -> None:
    class WithUnknown(Exception):
        stdout = 123

    try:
        raise WithUnknown()
    except WithUnknown:
        print_exception_message(trace_back=False)
    _out, err = capsys.readouterr()
    assert "STDOUT" not in err


def test_when_subprocess_output_is_a_string_it_is_echoed_directly(capsys: pytest.CaptureFixture[str]) -> None:
    class WithText(Exception):
        stdout = "hi"

    try:
        raise WithText()
    except WithText:
        print_exception_message(trace_back=False)
    _out, err = capsys.readouterr()
    assert "STDOUT: hi" in err


def test_when_subprocess_output_cannot_be_decoded_nothing_is_printed(capsys: pytest.CaptureFixture[str]) -> None:
    class EvilBytes(bytes):
        def decode(self, *args: object, **kwargs: object) -> str:  # type: ignore[override]
            raise UnicodeDecodeError("utf-8", b"", 0, 1, "boom")

    class WithBadStdout(Exception):
        stdout = EvilBytes(b"danger")

    try:
        raise WithBadStdout()
    except WithBadStdout:
        print_exception_message(trace_back=False)
    _out, err = capsys.readouterr()
    assert "STDOUT" not in err


def test_when_streams_are_flushed_the_function_returns_none() -> None:
    assert flush_streams() is None


def test_when_run_cli_finishes_successfully_it_returns_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    @click.command()
    def hello() -> None:
        pass

    track: list[Sequence[SignalSpec] | None] = []

    def fake_installer(specs: Sequence[SignalSpec] | None) -> Callable[[], None]:
        track.append(specs)
        return lambda: track.append(())

    monkeypatch.setattr(runner_module, "install_signal_handlers", fake_installer)
    assert run_cli(hello, argv=[], install_signals=True) == 0


def test_when_run_cli_finishes_successfully_the_restorer_is_called(monkeypatch: pytest.MonkeyPatch) -> None:
    @click.command()
    def hello() -> None:
        pass

    track: list[Sequence[SignalSpec] | None] = []

    def fake_installer(specs: Sequence[SignalSpec] | None) -> Callable[[], None]:
        track.append(specs)
        return lambda: track.append(())

    monkeypatch.setattr(runner_module, "install_signal_handlers", fake_installer)
    run_cli(hello, argv=[], install_signals=True)
    assert track and track[-1] == ()


def test_when_run_cli_raises_click_exception_that_exit_code_is_returned(monkeypatch: pytest.MonkeyPatch) -> None:
    @click.command()
    def fail() -> None:
        raise click.ClickException("fail")

    def simple_installer(_: Sequence[SignalSpec] | None) -> Callable[[], None]:
        return lambda: None

    monkeypatch.setattr(runner_module, "install_signal_handlers", simple_installer)
    assert run_cli(fail, argv=[], install_signals=True) == 1


def test_when_run_cli_uses_custom_exception_handler_that_value_is_returned(monkeypatch: pytest.MonkeyPatch) -> None:
    @click.command()
    def explode() -> None:
        raise RuntimeError("boom")

    def simple_installer(_: Sequence[SignalSpec] | None) -> Callable[[], None]:
        return lambda: None

    def return_ninety_nine(_: BaseException) -> int:
        return 99

    monkeypatch.setattr(runner_module, "install_signal_handlers", simple_installer)
    assert run_cli(explode, argv=[], exception_handler=return_ninety_nine, install_signals=True) == 99


def test_when_run_cli_uses_custom_signal_installer_it_receives_specs() -> None:
    @click.command()
    def quiet() -> None:
        pass

    seen: list[Sequence[SignalSpec] | None] = []

    def custom_installer(specs: Sequence[SignalSpec] | None) -> Callable[[], None]:
        seen.append(specs)
        return lambda: seen.append(())

    assert run_cli(quiet, argv=[], signal_installer=custom_installer, install_signals=True) == 0


def test_when_run_cli_uses_custom_signal_installer_the_restorer_is_called() -> None:
    @click.command()
    def quiet() -> None:
        pass

    seen: list[Sequence[SignalSpec] | None] = []

    def custom_installer(specs: Sequence[SignalSpec] | None) -> Callable[[], None]:
        seen.append(specs)
        return lambda: seen.append(())

    run_cli(quiet, argv=[], signal_installer=custom_installer, install_signals=True)
    assert seen and seen[-1] == ()


def test_when_run_cli_faces_exception_the_signal_restorer_is_called(monkeypatch: pytest.MonkeyPatch) -> None:
    @click.command()
    def fail() -> None:
        raise RuntimeError("boom")

    restored: list[str] = []

    def fake_installer(_: Sequence[SignalSpec] | None) -> Callable[[], None]:
        return lambda: restored.append("restored")

    monkeypatch.setattr(runner_module, "install_signal_handlers", fake_installer)
    run_cli(fail, argv=[], install_signals=True)
    assert restored == ["restored"]


def test_when_system_exit_code_is_unparseable_it_falls_back_to_one() -> None:
    assert handle_cli_exception(SystemExit("boom")) == 1


def test_when_a_std_stream_is_missing_the_generator_skips_it(monkeypatch: pytest.MonkeyPatch) -> None:
    null_stream = io.StringIO()
    monkeypatch.setattr(runner_module.sys, "stdout", None, raising=False)
    monkeypatch.setattr(runner_module.sys, "stderr", null_stream, raising=False)
    streams_to_flush = getattr(runner_module, "_streams_to_flush")
    flushed = list(streams_to_flush())
    assert flushed == [null_stream]
