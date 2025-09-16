from __future__ import annotations

from _pytest.capture import CaptureFixture

from lib_cli_exit_tools import (
    SigBreakInterrupt,
    SigIntInterrupt,
    SigTermInterrupt,
    config,
    handle_cli_exception,
)
from lib_cli_exit_tools import lib_cli_exit_tools as tools
from lib_cli_exit_tools.cli import main


def test_cli_info_command_runs_ok(capsys: CaptureFixture[str]) -> None:
    code = main(["info"])  # prints project info
    assert code == 0
    out_text, err = capsys.readouterr()
    assert "Info for lib_cli_exit_tools" in out_text
    assert err == ""


def test_cli_unknown_option_returns_usage_error(capsys: CaptureFixture[str]) -> None:
    code = main(["--does-not-exist"])  # click will raise a ClickException handled by run_cli
    assert code == 2
    _out, err = capsys.readouterr()
    assert "No such option" in err


def test_handle_exception_signal_codes(capsys: CaptureFixture[str]) -> None:
    code = handle_cli_exception(SigIntInterrupt())
    assert code == 130
    _out, err = capsys.readouterr()
    assert "Aborted" in err

    capsys.readouterr()  # clear
    code = handle_cli_exception(SigTermInterrupt())
    assert code == 143
    _out, err = capsys.readouterr()
    assert "Terminated" in err

    capsys.readouterr()
    specs = tools.default_signal_specs()
    sigbreak_spec = next((spec for spec in specs if spec.exception is SigBreakInterrupt), None)
    if sigbreak_spec is None:
        specs = specs + [tools.SignalSpec(signum=0, exception=SigBreakInterrupt, message="Terminated (SIGBREAK).", exit_code=149)]
    code = handle_cli_exception(SigBreakInterrupt(), signal_specs=specs)
    assert code == 149
    _out, err = capsys.readouterr()
    assert "SIGBREAK" in err


def test_handle_exception_broken_pipe_is_quiet(capsys: CaptureFixture[str]) -> None:
    old = tools.config.broken_pipe_exit_code
    try:
        tools.config.broken_pipe_exit_code = 141
        code = handle_cli_exception(BrokenPipeError())
        out, err = capsys.readouterr()
        assert out == ""
        assert err == ""
        assert code == 141
    finally:
        tools.config.broken_pipe_exit_code = old


def test_handle_exception_generic_uses_helpers(monkeypatch, capsys: CaptureFixture[str]) -> None:
    called: dict[str, object] = {}

    def fake_print() -> None:
        called["print"] = True

    def fake_exit(exc: BaseException) -> int:
        called["exc"] = exc
        return 55

    monkeypatch.setattr(tools, "print_exception_message", fake_print)
    monkeypatch.setattr(tools, "get_system_exit_code", fake_exit)
    monkeypatch.setattr(config, "traceback", False, raising=False)

    err = RuntimeError("boom")
    code = handle_cli_exception(err)
    assert code == 55
    assert called == {"print": True, "exc": err}
    capsys.readouterr()
