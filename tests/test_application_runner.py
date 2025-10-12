from __future__ import annotations

import io
import subprocess
import sys
from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager
from types import SimpleNamespace

import click
import pytest

from lib_cli_exit_tools.application import runner
from lib_cli_exit_tools.adapters.signals import SignalSpec
from lib_cli_exit_tools.core import configuration as cfg


class DummyCommand:
    def __init__(self, behaviour: Callable[[], None]) -> None:
        self._behaviour = behaviour

    def main(
        self,
        args: Sequence[str] | None = None,
        prog_name: str | None = None,
        complete_var: str | None = None,
        standalone_mode: bool = False,
        **_: object,
    ) -> None:
        self._behaviour()


@pytest.mark.os_agnostic
def test_when_flush_streams_runs_both_stdout_and_stderr_are_flushed(monkeypatch: pytest.MonkeyPatch) -> None:
    class Recorder:
        def __init__(self) -> None:
            self.flushed = False

        def flush(self) -> None:
            self.flushed = True

    stdout = Recorder()
    stderr = Recorder()
    monkeypatch.setattr(sys, "stdout", stdout)
    monkeypatch.setattr(sys, "stderr", stderr)

    runner.flush_streams()

    assert stdout.flushed is True
    assert stderr.flushed is True


@pytest.mark.os_agnostic
def test_when_print_exception_message_shows_summary_it_mentions_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    buffer = io.StringIO()
    monkeypatch.setattr(sys, "stderr", buffer)
    monkeypatch.setattr(sys, "stdout", io.StringIO())
    cfg.reset_config()

    try:
        raise ValueError("shallow failure")
    except ValueError:
        runner.print_exception_message(length_limit=80)

    output = buffer.getvalue()
    assert "ValueError" in output
    assert "shallow failure" in output


@pytest.mark.os_agnostic
def test_when_print_exception_message_renders_traceback_it_uses_rich_traceback(monkeypatch: pytest.MonkeyPatch) -> None:
    buffer = io.StringIO()
    monkeypatch.setattr(sys, "stderr", buffer)
    monkeypatch.setattr(sys, "stdout", io.StringIO())
    cfg.config.traceback = True

    try:
        raise RuntimeError("deep failure")
    except RuntimeError:
        runner.print_exception_message()

    output = buffer.getvalue()
    assert "RuntimeError" in output
    cfg.reset_config()


@pytest.mark.os_agnostic
def test_when_handle_cli_exception_meets_signal_spec_the_exit_code_matches(monkeypatch: pytest.MonkeyPatch) -> None:
    messages: list[str] = []
    spec = SignalSpec(signum=1, exception=RuntimeError, message="gentle stop", exit_code=9)

    result = runner.handle_cli_exception(
        RuntimeError("boom"),
        signal_specs=[spec],
        echo=lambda message, *, err=True: messages.append(message),
    )

    assert result == 9
    assert messages == ["gentle stop"]


@pytest.mark.os_agnostic
def test_when_handle_cli_exception_meets_broken_pipe_config_is_obeyed() -> None:
    cfg.config.broken_pipe_exit_code = 77
    try:
        assert runner.handle_cli_exception(BrokenPipeError()) == 77
    finally:
        cfg.reset_config()


@pytest.mark.os_agnostic
def test_when_handle_cli_exception_relies_on_default_echo_click_echo_is_used(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[tuple[str, bool]] = []

    def fake_echo(message: str, *, err: bool = True) -> None:
        captured.append((message, err))

    monkeypatch.setattr(runner, "_default_echo", fake_echo)  # pyright: ignore[arg-type]
    spec = SignalSpec(signum=2, exception=RuntimeError, message="default", exit_code=2)

    runner.handle_cli_exception(RuntimeError("boom"), signal_specs=[spec])

    assert captured == [("default", True)]


@pytest.mark.os_agnostic
def test_when_handle_cli_exception_meets_click_exception_their_exit_code_is_returned() -> None:
    exc = click.ClickException("boom")
    called: list[str] = []
    exc.show = lambda *_: called.append("shown")  # type: ignore[assignment]

    result = runner.handle_cli_exception(exc)

    assert result == exc.exit_code
    assert called == ["shown"]


@pytest.mark.os_agnostic
def test_when_handle_cli_exception_meets_system_exit_the_payload_is_used() -> None:
    exit_request = SystemExit(11)
    result = runner.handle_cli_exception(exit_request)
    assert result == 11


@pytest.mark.os_agnostic
def test_when_handle_cli_exception_falls_through_it_renders_then_translates(monkeypatch: pytest.MonkeyPatch) -> None:
    printed: list[tuple[bool, int]] = []

    def fake_print(*, trace_back: bool, length_limit: int = 500, stream: object | None = None) -> None:
        printed.append((trace_back, length_limit))

    def fake_exit(_: BaseException) -> int:
        return 5

    monkeypatch.setattr(runner, "print_exception_message", fake_print)  # pyright: ignore[arg-type]
    monkeypatch.setattr(runner, "get_system_exit_code", fake_exit)  # pyright: ignore[arg-type]

    result = runner.handle_cli_exception(ValueError("fallback"))

    assert result == 5
    assert printed == [(cfg.config.traceback, 500)]


@pytest.mark.os_agnostic
def test_when_streams_to_flush_encounters_missing_stdout_it_only_returns_stderr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "stdout", None)
    fake_stderr = io.StringIO()
    monkeypatch.setattr(sys, "stderr", fake_stderr)

    streams = list(runner._streams_to_flush())  # pyright: ignore[reportPrivateUsage]

    assert streams == [fake_stderr]


@pytest.mark.os_agnostic
def test_when_print_output_lacks_attribute_it_returns_without_output(monkeypatch: pytest.MonkeyPatch) -> None:
    buffer = io.StringIO()
    monkeypatch.setattr(sys, "stderr", buffer)
    exc = SimpleNamespace()

    runner._print_output(exc, "stdout", stream=None)  # pyright: ignore[reportPrivateUsage]

    assert buffer.getvalue() == ""


@pytest.mark.os_agnostic
def test_when_print_output_decodes_bytes_it_prints_uppercase_label(monkeypatch: pytest.MonkeyPatch) -> None:
    buffer = io.StringIO()
    monkeypatch.setattr(sys, "stderr", buffer)
    exc = subprocess.CalledProcessError(returncode=1, cmd=["cmd"], output=b"hello", stderr=b"bye")

    runner._emit_subprocess_output(exc, buffer)  # pyright: ignore[reportPrivateUsage]

    text = buffer.getvalue()
    assert "STDOUT: hello" in text
    assert "STDERR: bye" in text


@pytest.mark.os_agnostic
def test_when_print_output_receives_empty_text_nothing_is_printed(monkeypatch: pytest.MonkeyPatch) -> None:
    buffer = io.StringIO()
    monkeypatch.setattr(sys, "stderr", buffer)
    exc = SimpleNamespace(stdout="")

    runner._print_output(exc, "stdout", stream=None)  # pyright: ignore[reportPrivateUsage]

    assert buffer.getvalue() == ""


@pytest.mark.os_agnostic
def test_when_decode_output_receives_bytes_it_returns_text() -> None:
    assert runner._decode_output(b"content") == "content"  # pyright: ignore[reportPrivateUsage]


@pytest.mark.os_agnostic
def test_when_decode_output_receives_none_it_returns_none() -> None:
    assert runner._decode_output(None) is None  # pyright: ignore[reportPrivateUsage]


@pytest.mark.os_agnostic
def test_when_decode_output_receives_unknown_type_it_returns_none() -> None:
    assert runner._decode_output(12345) is None  # pyright: ignore[reportPrivateUsage]


@pytest.mark.os_agnostic
def test_when_decode_output_receives_string_it_returns_the_same_string() -> None:
    assert runner._decode_output("ready") == "ready"  # pyright: ignore[reportPrivateUsage]


@pytest.mark.os_agnostic
def test_when_truncate_message_exceeds_limit_a_truncation_suffix_is_added() -> None:
    from rich.text import Text

    truncated = runner._truncate_message(Text("abcdef"), length_limit=3)  # pyright: ignore[reportPrivateUsage]
    assert truncated.plain.startswith("abc")
    assert "TRUNCATED" in truncated.plain


@pytest.mark.os_agnostic
def test_when_print_exception_message_has_no_active_exception_it_does_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    buffer = io.StringIO()
    monkeypatch.setattr(sys, "stderr", buffer)
    runner.print_exception_message()
    assert buffer.getvalue() == ""


@pytest.mark.os_agnostic
def test_when_decode_output_encounters_bytes_that_fail_to_decode_it_returns_none() -> None:
    class BadBytes(bytes):
        def decode(self, *args: object, **kwargs: object) -> str:  # type: ignore[override]
            raise UnicodeDecodeError("utf-8", b"", 0, 1, "bad")

    assert runner._decode_output(BadBytes(b"x")) is None  # pyright: ignore[reportPrivateUsage]


@pytest.mark.os_agnostic
def test_when_cli_session_applies_overrides_they_exist_during_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg.reset_config()
    exit_codes: list[int] = []

    def exit_value(_: BaseException) -> int:
        return 17

    monkeypatch.setattr(runner, "get_system_exit_code", exit_value)  # pyright: ignore[arg-type]

    def fake_run_cli(command: runner.ClickCommand, *, exception_handler: Callable[[BaseException], int], **kwargs: object) -> int:
        try:
            command.main()
        except BaseException as exc:  # noqa: BLE001
            result = exception_handler(exc)
            exit_codes.append(result)
            return result
        return 0

    monkeypatch.setattr(runner, "run_cli", fake_run_cli)  # pyright: ignore[arg-type]

    def _raise() -> None:
        raise ValueError("fail")

    with runner.cli_session(overrides={"traceback": True}) as execute:
        code = execute(DummyCommand(_raise))

    assert cfg.config.traceback is False
    assert code == exit_codes[-1] == 17


@pytest.mark.os_agnostic
def test_when_cli_session_uses_restore_false_configuration_changes_persist(monkeypatch: pytest.MonkeyPatch) -> None:
    def run_cli_zero(*_: object, **__: object) -> int:
        return 0

    monkeypatch.setattr(runner, "run_cli", run_cli_zero)  # pyright: ignore[arg-type]
    cfg.reset_config()

    with runner.cli_session(overrides={"traceback": True}, restore=False) as execute:
        execute(DummyCommand(lambda: None))

    assert cfg.config.traceback is True
    cfg.reset_config()


@pytest.mark.os_agnostic
def test_when_run_cli_executes_successfully_zero_is_returned(monkeypatch: pytest.MonkeyPatch) -> None:
    command = DummyCommand(lambda: None)
    restorer_called: list[bool] = []

    def install_handlers(_: Sequence[SignalSpec]) -> Callable[[], None]:
        restorer_called.append(True)

        def restorer() -> None:
            restorer_called.append(False)

        return restorer

    monkeypatch.setattr(runner, "install_signal_handlers", install_handlers)  # pyright: ignore[arg-type]

    result = runner.run_cli(command)

    assert result == 0
    assert restorer_called == [True, False]


@pytest.mark.os_agnostic
def test_when_run_cli_receives_exception_the_handler_result_is_returned(monkeypatch: pytest.MonkeyPatch) -> None:
    handler_called: list[int] = []

    def handler(exc: BaseException) -> int:
        handler_called.append(123)
        return 123

    def raise_error() -> None:
        raise RuntimeError("boom")

    command = DummyCommand(raise_error)
    result = runner.run_cli(command, exception_handler=handler)

    assert result == 123
    assert handler_called == [123]


@pytest.mark.os_agnostic
def test_when_run_cli_skips_signal_installation_no_install_occurs(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[str] = []

    def install_and_record(_: Sequence[SignalSpec]) -> Callable[[], None]:
        called.append("installed")
        return lambda: None

    monkeypatch.setattr(runner, "install_signal_handlers", install_and_record)  # pyright: ignore[arg-type]

    runner.run_cli(DummyCommand(lambda: None), install_signals=False)

    assert called == []


@pytest.mark.os_agnostic
def test_when_safe_system_exit_code_cannot_convert_the_value_it_returns_one() -> None:
    exit_request = SystemExit()
    exit_request.code = object()  # type: ignore[attr-defined]
    assert runner._safe_system_exit_code(exit_request) == 1  # pyright: ignore[reportPrivateUsage]


@pytest.mark.os_agnostic
def test_when_cli_session_runs_without_overrides_it_executes_commands(monkeypatch: pytest.MonkeyPatch) -> None:
    executed: list[str] = []

    def fake_run_cli(command: runner.ClickCommand, **kwargs: object) -> int:
        command.main()
        return 0

    monkeypatch.setattr(runner, "run_cli", fake_run_cli)

    with runner.cli_session() as execute:
        result = execute(DummyCommand(lambda: executed.append("done")))

    assert result == 0
    assert executed == ["done"]


@pytest.mark.os_agnostic
def test_when_session_config_manager_receives_no_overrides_and_restore_false_it_returns_null_context() -> None:
    manager = runner._session_config_manager({}, restore=False)  # pyright: ignore[reportPrivateUsage]
    assert isinstance(manager, AbstractContextManager)
    with manager:
        pass
