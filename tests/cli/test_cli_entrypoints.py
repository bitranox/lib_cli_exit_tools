"""CLI behaviour described in plain words."""

from __future__ import annotations

import subprocess
import sys

from _pytest.capture import CaptureFixture

import pytest

import lib_cli_exit_tools
from lib_cli_exit_tools import i_should_fail, run_cli
from lib_cli_exit_tools.cli import cli as root_cli, main


def test_i_should_fail_always_raises_runtime_error() -> None:
    with pytest.raises(RuntimeError, match="i should fail"):
        i_should_fail()


def test_cli_info_command_writes_metadata(capsys: CaptureFixture[str]) -> None:
    exit_code = main(["info"])
    out, err = capsys.readouterr()
    assert exit_code == 0 and "Info for lib_cli_exit_tools" in out and err == ""


def test_cli_fail_command_prints_runtime_error(capsys: CaptureFixture[str]) -> None:
    exit_code = main(["fail"])
    out, err = capsys.readouterr()
    assert exit_code == 1 and out == "" and "RuntimeError: i should fail" in err


def test_cli_fail_with_traceback_renders_rich_output(capsys: CaptureFixture[str]) -> None:
    exit_code = main(["--traceback", "fail"])
    _out, err = capsys.readouterr()
    expected = lib_cli_exit_tools.get_system_exit_code(RuntimeError("i should fail"))
    assert exit_code == expected and "Traceback" in err


def test_cli_reports_unknown_option(capsys: CaptureFixture[str]) -> None:
    exit_code = main(["--does-not-exist"])
    _out, err = capsys.readouterr()
    assert exit_code == 2 and "No such option" in err


def test_module_execution_matches_run_cli(capsys: CaptureFixture[str]) -> None:
    exit_main = main(["info"])
    out_main, err_main = capsys.readouterr()

    exit_runner = run_cli(root_cli, argv=["info"], install_signals=False)
    out_runner, err_runner = capsys.readouterr()

    assert exit_main == exit_runner == 0
    assert out_main == out_runner and err_main == err_runner


def test_python_m_help_flag_returns_usage_text() -> None:
    proc = subprocess.run([sys.executable, "-m", "lib_cli_exit_tools", "--help"], capture_output=True, text=True, check=False)
    assert proc.returncode == 0 and ("Usage" in proc.stdout or "--help" in proc.stdout)


def test_main_downgrades_rich_click_when_stream_cannot_handle_utf(monkeypatch: pytest.MonkeyPatch) -> None:
    class FakeStream:
        encoding = "cp1252"

        def isatty(self) -> bool:
            return False

    import lib_cli_exit_tools.cli as cli_mod

    def provide_fake_stream(_: str) -> FakeStream:
        return FakeStream()

    monkeypatch.setattr(cli_mod.click, "get_text_stream", provide_fake_stream)
    cli_mod.rich_config.FORCE_TERMINAL = True
    cli_mod.rich_config.COLOR_SYSTEM = "standard"

    exit_code = cli_mod.main(["info"])

    assert exit_code == 0
    assert cli_mod.rich_config.FORCE_TERMINAL is False
    assert cli_mod.rich_config.COLOR_SYSTEM is None


def test_python_m_invocation_for_info_succeeds() -> None:
    proc = subprocess.run([sys.executable, "-m", "lib_cli_exit_tools", "info"], capture_output=True, text=True, check=False)
    assert proc.returncode == 0 and "Info for lib_cli_exit_tools" in proc.stdout
