"""Application-layer runner tests.

Purpose:
    Verify that the orchestration helpers manage signals, traceback output,
    and Click integration according to documented policy.
Contents:
    * Error-handling scenarios for `handle_cli_exception`.
    * Rendering and flushing behaviour for `print_exception_message`.
    * Integration paths for `run_cli` hooks.
System Integration:
    Ensures entrypoints and adapters can rely on consistent orchestration
    semantics.
"""

from __future__ import annotations

import io
from collections.abc import Callable

import click
import pytest

from lib_cli_exit_tools.application.runner import (
    flush_streams,
    handle_cli_exception,
    print_exception_message,
    run_cli,
)
from lib_cli_exit_tools.application import runner as runner_module
from lib_cli_exit_tools.core.configuration import config
from lib_cli_exit_tools.adapters.signals import SignalSpec, SigIntInterrupt


@pytest.fixture(autouse=True)
def _stub_signal_install(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent tests from mutating global signal handlers by default."""

    monkeypatch.setattr(
        "lib_cli_exit_tools.application.runner.install_signal_handlers",
        lambda specs=None: lambda: None,
    )


def test_handle_cli_exception_emits_signal_message(capsys: pytest.CaptureFixture[str]) -> None:
    """Signal-derived exceptions emit user-facing messages and codes."""
    exit_code = handle_cli_exception(SigIntInterrupt())
    _out, err = capsys.readouterr()
    assert exit_code == 130
    assert "Aborted" in err


def test_handle_cli_exception_broken_pipe_uses_configured_code(capsys: pytest.CaptureFixture[str]) -> None:
    """BrokenPipeError results honour the configured exit code and stay quiet."""
    config.broken_pipe_exit_code = 141
    exit_code = handle_cli_exception(BrokenPipeError())
    out, err = capsys.readouterr()
    assert (out, err) == ("", "")
    assert exit_code == 141


def test_handle_cli_exception_generic_delegates(monkeypatch: pytest.MonkeyPatch) -> None:
    """Generic exceptions delegate to printers and exit-code helpers."""
    calls: dict[str, object] = {}

    def fake_print() -> None:
        calls["printed"] = True

    def fake_exit(exc: BaseException) -> int:
        calls["exc"] = exc
        return 55

    monkeypatch.setattr("lib_cli_exit_tools.application.runner.print_exception_message", fake_print)
    monkeypatch.setattr("lib_cli_exit_tools.application.runner.get_system_exit_code", fake_exit)
    config.traceback = False

    err = RuntimeError("boom")
    assert handle_cli_exception(err) == 55
    assert calls == {"printed": True, "exc": err}


def test_handle_cli_exception_prints_rich_traceback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Traceback mode renders rich tracebacks and returns exit codes."""
    calls: dict[str, object] = {}

    def _fake_print(*_args, **kwargs) -> None:
        calls["called"] = True
        calls["trace_back"] = kwargs.get("trace_back")

    def _fake_exit(exc: BaseException) -> int:
        calls["exc"] = exc
        return 17

    monkeypatch.setattr("lib_cli_exit_tools.application.runner.print_exception_message", _fake_print)
    monkeypatch.setattr("lib_cli_exit_tools.application.runner.get_system_exit_code", _fake_exit)

    config.traceback = True
    err = RuntimeError("boom")
    assert handle_cli_exception(err) == 17
    assert calls == {"called": True, "trace_back": True, "exc": err}


def test_print_exception_message_outputs_summary() -> None:
    """Plain summary output is produced when tracebacks are suppressed."""
    try:
        raise FileNotFoundError("missing.txt")
    except Exception:
        buf = io.StringIO()
        print_exception_message(trace_back=False, stream=buf)
        output = buf.getvalue()
        assert "FileNotFoundError" in output
        assert "missing.txt" in output


def test_print_exception_message_renders_traceback() -> None:
    """Traceback rendering emits the formatted stack trace."""
    try:
        raise ValueError("broken")
    except Exception:
        buf = io.StringIO()
        print_exception_message(trace_back=True, stream=buf)
        assert "Traceback" in buf.getvalue()


def test_print_exception_message_force_color(monkeypatch: pytest.MonkeyPatch) -> None:
    """Forced colour mode drives Rich console configuration."""
    calls: dict[str, object] = {}

    class _DummyConsole:
        def __init__(self, *, file, force_terminal, color_system, soft_wrap):
            calls["force_terminal"] = force_terminal
            calls["color_system"] = color_system
            calls["soft_wrap"] = soft_wrap
            self.file = file

        def print(self, renderable) -> None:  # pragma: no cover - behaviour mocked
            calls["renderable"] = renderable

    def _fake_traceback(*_args, **_kwargs):
        calls["traceback_called"] = True
        return "traceback"

    monkeypatch.setattr(runner_module, "Console", _DummyConsole, raising=False)
    monkeypatch.setattr(runner_module.Traceback, "from_exception", _fake_traceback, raising=False)
    config.traceback_force_color = True

    try:
        raise ValueError("boom")
    except ValueError:
        print_exception_message(True, stream=io.StringIO())

    assert calls.get("traceback_called") is True
    assert calls.get("force_terminal") is True
    assert calls.get("color_system") == "auto"


def test_print_exception_message_handles_bytes_output(capsys: pytest.CaptureFixture[str]) -> None:
    """Subprocess byte output is decoded and printed."""

    class FakeException(Exception):
        stdout = b"hello"

    try:
        raise FakeException()
    except FakeException:
        print_exception_message(trace_back=False)

    _out, err = capsys.readouterr()
    assert "STDOUT: hello" in err


def test_flush_streams_is_noop() -> None:
    """Stream flushing completes without raising."""
    flush_streams()


def test_run_cli_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Successful command execution returns 0 and completes without signals."""

    @click.command()
    def cli_cmd() -> None:
        click.echo("ok")

    exit_code = run_cli(cli_cmd, argv=["--help"], install_signals=False)
    assert exit_code == 0


def test_run_cli_handles_click_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """Click exceptions propagate their exit codes through run_cli."""

    @click.command()
    def cli_cmd() -> None:
        raise click.ClickException("fail")

    exit_code = run_cli(cli_cmd, argv=[], install_signals=False)
    assert exit_code == 1


def test_run_cli_accepts_custom_exception_handler() -> None:
    """Custom exception handlers can override exit codes."""

    @click.command()
    def cli_cmd() -> None:
        raise RuntimeError("boom")

    captured: dict[str, BaseException] = {}

    def fake_handler(exc: BaseException) -> int:
        captured["exc"] = exc
        return 99

    exit_code = run_cli(cli_cmd, argv=[], install_signals=True, exception_handler=fake_handler)
    assert exit_code == 99
    assert isinstance(captured["exc"], RuntimeError)


def test_run_cli_uses_custom_signal_installer() -> None:
    """Custom signal installers receive specs and restoration executes."""

    @click.command()
    def cli_cmd() -> None:
        pass

    installs: list[list[SignalSpec]] = []
    restored: list[bool] = []

    def fake_installer(specs: list[SignalSpec] | None) -> Callable[[], None]:
        installs.append(list(specs or []))
        return lambda: restored.append(True)

    exit_code = run_cli(cli_cmd, argv=[], signal_installer=fake_installer, install_signals=True)
    assert exit_code == 0
    assert installs and isinstance(installs[0][0], SignalSpec)
    assert restored == [True]


def test_custom_signal_installer_can_raise(monkeypatch: pytest.MonkeyPatch) -> None:
    """Errors from custom signal installers bubble up for visibility."""

    @click.command()
    def cli_cmd() -> None:
        pass

    def boom(_specs):
        raise RuntimeError("installer failed")

    with pytest.raises(RuntimeError, match="installer failed"):
        run_cli(cli_cmd, argv=[], signal_installer=boom, install_signals=True)
