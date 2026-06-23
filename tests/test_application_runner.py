"""Tests for the application runner module.

Each test verifies exactly one behavior:
- Stream flushing operations
- Exception message printing
- Exception handling and exit code resolution
- CLI session management
- Output decoding and truncation
"""

from __future__ import annotations

import io
import subprocess
import sys
from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager
from types import SimpleNamespace

import click
import pytest
from rich.text import Text

from lib_cli_exit_tools.adapters.signals import SignalSpec
from lib_cli_exit_tools.application import runner
from lib_cli_exit_tools.core import configuration as cfg


# =============================================================================
# Fixtures
# =============================================================================


class DummyCommand:
    """A minimal Click command stub for testing run_cli."""

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


@pytest.fixture
def captured_stderr(monkeypatch: pytest.MonkeyPatch) -> io.StringIO:
    """Redirect stderr to a StringIO buffer for assertion."""
    buffer = io.StringIO()
    monkeypatch.setattr(sys, "stderr", buffer)
    monkeypatch.setattr(sys, "stdout", io.StringIO())
    return buffer


# =============================================================================
# Stream Flushing
# =============================================================================


@pytest.mark.os_agnostic
def test_flush_streams_flushes_stdout(monkeypatch: pytest.MonkeyPatch) -> None:
    class Recorder:
        flushed = False

        def flush(self) -> None:
            self.flushed = True

    stdout = Recorder()
    monkeypatch.setattr(sys, "stdout", stdout)
    monkeypatch.setattr(sys, "stderr", Recorder())

    runner.flush_streams()

    assert stdout.flushed is True


@pytest.mark.os_agnostic
def test_flush_streams_flushes_stderr(monkeypatch: pytest.MonkeyPatch) -> None:
    class Recorder:
        flushed = False

        def flush(self) -> None:
            self.flushed = True

    stderr = Recorder()
    monkeypatch.setattr(sys, "stdout", Recorder())
    monkeypatch.setattr(sys, "stderr", stderr)

    runner.flush_streams()

    assert stderr.flushed is True


@pytest.mark.os_agnostic
def test_streams_to_flush_skips_missing_stdout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "stdout", None)
    fake_stderr = io.StringIO()
    monkeypatch.setattr(sys, "stderr", fake_stderr)

    streams = list(runner._streams_to_flush())  # pyright: ignore[reportPrivateUsage]

    assert streams == [fake_stderr]


# =============================================================================
# Exception Message Printing
# =============================================================================


@pytest.mark.os_agnostic
def test_print_exception_message_shows_exception_type(captured_stderr: io.StringIO, reset_config: None) -> None:
    try:
        raise ValueError("shallow failure")
    except ValueError:
        runner.print_exception_message(trace_back=False, length_limit=80, stream=captured_stderr)

    assert "ValueError" in captured_stderr.getvalue()


@pytest.mark.os_agnostic
def test_print_exception_message_shows_exception_message(captured_stderr: io.StringIO, reset_config: None) -> None:
    try:
        raise ValueError("shallow failure")
    except ValueError:
        runner.print_exception_message(trace_back=False, length_limit=80, stream=captured_stderr)

    assert "shallow failure" in captured_stderr.getvalue()


@pytest.mark.os_agnostic
def test_print_exception_message_with_traceback_shows_traceback(captured_stderr: io.StringIO, reset_config: None) -> None:
    cfg.config.traceback = True
    try:
        raise RuntimeError("deep failure")
    except RuntimeError:
        runner.print_exception_message(stream=captured_stderr)

    assert "RuntimeError" in captured_stderr.getvalue()


@pytest.mark.os_agnostic
def test_print_exception_message_with_no_exception_does_nothing(captured_stderr: io.StringIO) -> None:
    runner.print_exception_message()
    assert captured_stderr.getvalue() == ""


# =============================================================================
# Output Decoding
# =============================================================================


@pytest.mark.os_agnostic
def test_decode_output_converts_bytes_to_string() -> None:
    assert runner._decode_output(b"content") == "content"  # pyright: ignore[reportPrivateUsage]


@pytest.mark.os_agnostic
def test_decode_output_returns_string_unchanged() -> None:
    assert runner._decode_output("ready") == "ready"  # pyright: ignore[reportPrivateUsage]


@pytest.mark.os_agnostic
def test_decode_output_returns_none_for_none() -> None:
    assert runner._decode_output(None) is None  # pyright: ignore[reportPrivateUsage]


@pytest.mark.os_agnostic
def test_decode_output_returns_none_for_integer() -> None:
    assert runner._decode_output(12345) is None  # pyright: ignore[reportPrivateUsage]


@pytest.mark.os_agnostic
def test_decode_output_returns_none_for_decode_failure() -> None:
    class BadBytes(bytes):
        def decode(self, *args: object, **kwargs: object) -> str:  # type: ignore[override]
            raise UnicodeDecodeError("utf-8", b"", 0, 1, "bad")

    assert runner._decode_output(BadBytes(b"x")) is None  # pyright: ignore[reportPrivateUsage]


# =============================================================================
# Print Output
# =============================================================================


@pytest.mark.os_agnostic
def test_print_output_does_nothing_when_attribute_missing(captured_stderr: io.StringIO) -> None:
    exc = SimpleNamespace()
    runner._print_output(exc, "stdout", stream=None)  # pyright: ignore[reportPrivateUsage]
    assert captured_stderr.getvalue() == ""


@pytest.mark.os_agnostic
def test_print_output_does_nothing_for_empty_string(captured_stderr: io.StringIO) -> None:
    exc = SimpleNamespace(stdout="")
    runner._print_output(exc, "stdout", stream=None)  # pyright: ignore[reportPrivateUsage]
    assert captured_stderr.getvalue() == ""


@pytest.mark.os_agnostic
def test_print_output_prints_decoded_bytes_with_label(captured_stderr: io.StringIO) -> None:
    exc = subprocess.CalledProcessError(returncode=1, cmd=["cmd"], output=b"hello", stderr=b"bye")
    runner._emit_subprocess_output(exc, captured_stderr)  # pyright: ignore[reportPrivateUsage]
    text = captured_stderr.getvalue()
    assert "STDOUT: hello" in text
    assert "STDERR: bye" in text


# =============================================================================
# Message Truncation
# =============================================================================


@pytest.mark.os_agnostic
def test_truncate_message_adds_suffix_when_too_long() -> None:
    truncated = runner._truncate_message(Text("abcdef"), length_limit=3)  # pyright: ignore[reportPrivateUsage]
    assert truncated.plain.startswith("abc")
    assert "TRUNCATED" in truncated.plain


@pytest.mark.os_agnostic
def test_truncate_message_preserves_short_messages() -> None:
    original = Text("abc")
    truncated = runner._truncate_message(original, length_limit=10)  # pyright: ignore[reportPrivateUsage]
    assert truncated.plain == "abc"


# =============================================================================
# Exception Handling - Signal Specs
# =============================================================================


@pytest.mark.os_agnostic
def test_handle_exception_with_matching_signal_spec_returns_exit_code() -> None:
    spec = SignalSpec(signum=1, exception=RuntimeError, message="gentle stop", exit_code=9)
    messages: list[str] = []

    result = runner.handle_cli_exception(
        RuntimeError("boom"),
        signal_specs=[spec],
        echo=lambda message, *, err=True: messages.append(message),
    )

    assert result == 9


@pytest.mark.os_agnostic
def test_handle_exception_with_matching_signal_spec_echoes_message() -> None:
    spec = SignalSpec(signum=1, exception=RuntimeError, message="gentle stop", exit_code=9)
    messages: list[str] = []

    runner.handle_cli_exception(
        RuntimeError("boom"),
        signal_specs=[spec],
        echo=lambda message, *, err=True: messages.append(message),
    )

    assert messages == ["gentle stop"]


# =============================================================================
# Exception Handling - BrokenPipeError
# =============================================================================


@pytest.mark.os_agnostic
def test_handle_exception_for_broken_pipe_uses_configured_code(reset_config: None) -> None:
    cfg.config.broken_pipe_exit_code = 77
    assert runner.handle_cli_exception(BrokenPipeError()) == 77


# =============================================================================
# Exception Handling - Click Exceptions
# =============================================================================


@pytest.mark.os_agnostic
def test_handle_exception_for_click_exception_returns_its_exit_code() -> None:
    exc = click.ClickException("boom")
    exc.show = lambda *_: None  # type: ignore[assignment]
    result = runner.handle_cli_exception(exc)
    assert result == exc.exit_code


@pytest.mark.os_agnostic
def test_handle_exception_for_click_exception_calls_show() -> None:
    exc = click.ClickException("boom")
    called: list[str] = []
    exc.show = lambda *_: called.append("shown")  # type: ignore[assignment]
    runner.handle_cli_exception(exc)
    assert called == ["shown"]


# =============================================================================
# Exception Handling - SystemExit
# =============================================================================


@pytest.mark.os_agnostic
def test_handle_exception_for_system_exit_uses_payload() -> None:
    result = runner.handle_cli_exception(SystemExit(11))
    assert result == 11


@pytest.mark.os_agnostic
def test_safe_system_exit_code_returns_one_for_unconvertible_payload() -> None:
    exit_request = SystemExit()
    exit_request.code = object()  # type: ignore[attr-defined]
    assert runner._safe_system_exit_code(exit_request) == 1  # pyright: ignore[reportPrivateUsage]


# =============================================================================
# Exception Handling - Fallback
# =============================================================================


@pytest.mark.os_agnostic
def test_handle_exception_fallback_prints_and_translates(monkeypatch: pytest.MonkeyPatch) -> None:
    printed: list[bool] = []

    def fake_print(*, trace_back: bool, length_limit: int = 500, stream: object | None = None) -> None:
        printed.append(trace_back)

    def fake_exit(_: BaseException) -> int:
        return 5

    monkeypatch.setattr(runner, "print_exception_message", fake_print)  # pyright: ignore[arg-type]
    monkeypatch.setattr(runner, "get_system_exit_code", fake_exit)  # pyright: ignore[arg-type]

    result = runner.handle_cli_exception(ValueError("fallback"))

    assert result == 5
    assert printed == [cfg.config.traceback]


# =============================================================================
# CLI Session
# =============================================================================


@pytest.mark.os_agnostic
def test_cli_session_applies_traceback_override(reset_config: None) -> None:
    states: list[bool] = []

    def fake_run_cli(command: runner.ClickCommand, **kwargs: object) -> int:
        states.append(cfg.config.traceback)
        command.main()
        return 0

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(runner, "run_cli", fake_run_cli)

        with runner.cli_session(overrides={"traceback": True}) as execute:
            execute(DummyCommand(lambda: None))

    assert states == [True]


@pytest.mark.os_agnostic
def test_cli_session_restores_config_after_exit(reset_config: None) -> None:
    def fake_run_cli(command: runner.ClickCommand, **kwargs: object) -> int:
        command.main()
        return 0

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(runner, "run_cli", fake_run_cli)

        with runner.cli_session(overrides={"traceback": True}) as execute:
            execute(DummyCommand(lambda: None))

    assert cfg.config.traceback is False


@pytest.mark.os_agnostic
def test_cli_session_restore_false_preserves_changes(reset_config: None) -> None:
    def fake_run_cli(*_: object, **__: object) -> int:
        return 0

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(runner, "run_cli", fake_run_cli)

        with runner.cli_session(overrides={"traceback": True}, restore=False) as execute:
            execute(DummyCommand(lambda: None))

    assert cfg.config.traceback is True


@pytest.mark.os_agnostic
def test_cli_session_without_overrides_executes_command(monkeypatch: pytest.MonkeyPatch) -> None:
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
def test_session_config_manager_with_no_overrides_returns_null_context() -> None:
    manager = runner._session_config_manager({}, restore=False)  # pyright: ignore[reportPrivateUsage]
    assert isinstance(manager, AbstractContextManager)
    with manager:
        pass  # Should not raise


# =============================================================================
# Run CLI
# =============================================================================


@pytest.mark.os_agnostic
def test_run_cli_returns_zero_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    def install_handlers(_: Sequence[SignalSpec]) -> Callable[[], None]:
        return lambda: None

    monkeypatch.setattr(runner, "install_signal_handlers", install_handlers)

    result = runner.run_cli(DummyCommand(lambda: None))

    assert result == 0


@pytest.mark.os_agnostic
def test_run_cli_returns_handler_result_on_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(exc: BaseException) -> int:
        return 123

    def raise_error() -> None:
        raise RuntimeError("boom")

    result = runner.run_cli(DummyCommand(raise_error), exception_handler=handler)

    assert result == 123


@pytest.mark.os_agnostic
def test_run_cli_installs_signal_handlers(monkeypatch: pytest.MonkeyPatch) -> None:
    installed: list[str] = []

    def install_and_record(_: Sequence[SignalSpec]) -> Callable[[], None]:
        installed.append("installed")
        return lambda: installed.append("restored")

    monkeypatch.setattr(runner, "install_signal_handlers", install_and_record)

    runner.run_cli(DummyCommand(lambda: None))

    assert "installed" in installed
    assert "restored" in installed


@pytest.mark.os_agnostic
def test_run_cli_skips_signal_installation_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    called: list[str] = []

    def install_and_record(_: Sequence[SignalSpec]) -> Callable[[], None]:
        called.append("installed")
        return lambda: None

    monkeypatch.setattr(runner, "install_signal_handlers", install_and_record)

    runner.run_cli(DummyCommand(lambda: None), install_signals=False)

    assert called == []
