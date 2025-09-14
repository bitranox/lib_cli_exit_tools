from __future__ import annotations

from _pytest.capture import CaptureFixture
from lib_cli_exit_tools.cli import main, SigIntError, SigTermError, SigBreakError
from lib_cli_exit_tools import lib_cli_exit_tools as tools
import lib_cli_exit_tools.cli as cli_mod


def test_cli_info_command_runs_ok(capsys: CaptureFixture[str]) -> None:
    code = main(["info"])  # prints project info
    assert code == 0
    out, err = capsys.readouterr()
    assert "Info for lib_cli_exit_tools" in out
    assert err == ""


def test_cli_unknown_option_returns_usage_error() -> None:
    code = main(["--does-not-exist"])  # click will raise a ClickException
    assert code == 2


def test_handle_exception_signal_codes() -> None:
    handle = getattr(cli_mod, "_handle_exception")
    assert handle(SigIntError()) == 130  # pyright: ignore[reportPrivateUsage]
    assert handle(SigTermError()) == 143  # pyright: ignore[reportPrivateUsage]
    assert handle(SigBreakError()) == 149  # pyright: ignore[reportPrivateUsage]


def test_handle_exception_broken_pipe_is_quiet(capsys: CaptureFixture[str]) -> None:
    tools.config.broken_pipe_exit_code = 141
    handle = getattr(cli_mod, "_handle_exception")
    code = handle(BrokenPipeError())  # pyright: ignore[reportPrivateUsage]
    out, err = capsys.readouterr()
    assert out == ""
    assert err == ""
    assert code == 141
