"""The CLI sings its behaviors through these tests."""

from __future__ import annotations

import runpy
import subprocess
import sys
from typing import Any

import pytest

import lib_cli_exit_tools
from lib_cli_exit_tools.cli import cli as root_cli, main


pytestmark = [pytest.mark.os_agnostic]


def test_when_the_failure_helper_is_called_it_raises_runtime_error() -> None:
    with pytest.raises(RuntimeError, match="i should fail"):
        lib_cli_exit_tools.i_should_fail()


def test_when_info_command_runs_the_exit_code_is_zero(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["info"]) == 0
    capsys.readouterr()


def test_when_info_command_runs_the_output_announces_metadata(capsys: pytest.CaptureFixture[str]) -> None:
    main(["info"])
    out, _err = capsys.readouterr()
    assert "Info for lib_cli_exit_tools" in out


def test_when_fail_command_runs_the_exit_code_is_one(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["fail"]) == 1
    capsys.readouterr()


def test_when_fail_command_runs_the_error_mentions_runtime_failure(capsys: pytest.CaptureFixture[str]) -> None:
    main(["fail"])
    _out, err = capsys.readouterr()
    assert "RuntimeError: i should fail" in err


def test_when_traceback_is_requested_the_rich_traceback_is_emitted(capsys: pytest.CaptureFixture[str]) -> None:
    main(["--traceback", "fail"])
    _out, err = capsys.readouterr()
    assert "Traceback" in err


def test_when_unknown_option_is_used_the_exit_code_is_two(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--does-not-exist"]) == 2
    capsys.readouterr()


def test_when_unknown_option_is_used_the_error_mentions_the_unknown(capsys: pytest.CaptureFixture[str]) -> None:
    main(["--does-not-exist"])
    _out, err = capsys.readouterr()
    assert "No such option" in err


def test_when_main_runs_and_run_cli_runs_the_exit_codes_match(capsys: pytest.CaptureFixture[str]) -> None:
    exit_main = main(["info"])
    capsys.readouterr()
    exit_runner = lib_cli_exit_tools.run_cli(root_cli, argv=["info"], install_signals=False)
    capsys.readouterr()
    assert exit_main == exit_runner


def test_when_main_runs_and_run_cli_runs_the_outputs_match(capsys: pytest.CaptureFixture[str]) -> None:
    main(["info"])
    out_main, err_main = capsys.readouterr()
    lib_cli_exit_tools.run_cli(root_cli, argv=["info"], install_signals=False)
    out_runner, err_runner = capsys.readouterr()
    assert (out_main, err_main) == (out_runner, err_runner)


def test_when_python_dash_m_help_is_invoked_the_exit_code_is_zero() -> None:
    proc = subprocess.run([sys.executable, "-m", "lib_cli_exit_tools", "--help"], capture_output=True, text=True, check=False)
    assert proc.returncode == 0


def test_when_python_dash_m_help_is_invoked_the_output_mentions_usage() -> None:
    proc = subprocess.run([sys.executable, "-m", "lib_cli_exit_tools", "--help"], capture_output=True, text=True, check=False)
    assert "Usage" in proc.stdout or "--help" in proc.stdout


def test_when_python_dash_m_info_is_invoked_the_output_mentions_metadata() -> None:
    proc = subprocess.run([sys.executable, "-m", "lib_cli_exit_tools", "info"], capture_output=True, text=True, check=False)
    assert "Info for lib_cli_exit_tools" in proc.stdout


def test_when_module_entrypoint_runs_it_delegates_to_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    import lib_cli_exit_tools.cli as cli_mod

    called: dict[str, Any] = {}

    def fake_main(argv: list[str] | None = None) -> int:
        called["argv"] = argv
        return 42

    monkeypatch.setattr(cli_mod, "main", fake_main)

    with pytest.raises(SystemExit) as exc_info:
        runpy.run_module("lib_cli_exit_tools.__main__", run_name="__main__")

    assert exc_info.value.code == 42


def test_when_module_entrypoint_runs_it_passes_none_for_argv(monkeypatch: pytest.MonkeyPatch) -> None:
    import lib_cli_exit_tools.cli as cli_mod

    called: dict[str, Any] = {}

    def fake_main(argv: list[str] | None = None) -> int:
        called["argv"] = argv
        raise SystemExit(0)

    monkeypatch.setattr(cli_mod, "main", fake_main)

    with pytest.raises(SystemExit):
        runpy.run_module("lib_cli_exit_tools.__main__", run_name="__main__")

    assert called == {"argv": None}


def test_when_stream_lacks_utf_support_rich_click_is_downgraded(monkeypatch: pytest.MonkeyPatch) -> None:
    import lib_cli_exit_tools.cli as cli_mod

    class PlainStream:
        encoding = "cp1252"

        def isatty(self) -> bool:
            return False

    def fake_stream(_: str) -> PlainStream:
        return PlainStream()

    monkeypatch.setattr(cli_mod.click, "get_text_stream", fake_stream)
    original_force = cli_mod.rich_config.FORCE_TERMINAL = True
    original_color = cli_mod.rich_config.COLOR_SYSTEM = "standard"
    assert cli_mod.main(["info"]) == 0
    cli_mod.rich_config.FORCE_TERMINAL = original_force
    cli_mod.rich_config.COLOR_SYSTEM = original_color


def test_when_rich_click_is_downgraded_run_cli_sees_plain_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    import lib_cli_exit_tools.cli as cli_mod

    class PlainStream:
        encoding = "cp1252"

        def isatty(self) -> bool:
            return False

    def fake_stream(_: str) -> PlainStream:
        return PlainStream()

    observed: dict[str, Any] = {}

    def fake_run_cli(*args: object, **kwargs: object) -> int:
        observed.update(
            {
                "FORCE_TERMINAL": cli_mod.rich_config.FORCE_TERMINAL,
                "COLOR_SYSTEM": cli_mod.rich_config.COLOR_SYSTEM,
            }
        )
        return 0

    monkeypatch.setattr(cli_mod.click, "get_text_stream", fake_stream)
    monkeypatch.setattr(cli_mod.lib_cli_exit_tools, "run_cli", fake_run_cli)
    monkeypatch.setattr(lib_cli_exit_tools, "run_cli", fake_run_cli)
    cli_mod.main(["info"])
    assert observed == {"FORCE_TERMINAL": False, "COLOR_SYSTEM": None}


def test_when_rich_click_is_downgraded_the_settings_are_restored(monkeypatch: pytest.MonkeyPatch) -> None:
    import lib_cli_exit_tools.cli as cli_mod

    class PlainStream:
        encoding = "cp1252"

        def isatty(self) -> bool:
            return False

    def fake_stream(_: str) -> PlainStream:
        return PlainStream()

    def fake_run_cli(*args: object, **kwargs: object) -> int:
        return 0

    monkeypatch.setattr(cli_mod.click, "get_text_stream", fake_stream)
    monkeypatch.setattr(cli_mod.lib_cli_exit_tools, "run_cli", fake_run_cli)
    monkeypatch.setattr(lib_cli_exit_tools, "run_cli", fake_run_cli)
    baseline_force = cli_mod.rich_config.FORCE_TERMINAL
    baseline_color = cli_mod.rich_config.COLOR_SYSTEM
    cli_mod.main(["info"])
    assert (baseline_force, baseline_color) == (cli_mod.rich_config.FORCE_TERMINAL, cli_mod.rich_config.COLOR_SYSTEM)


def test_when_run_cli_fails_the_rich_click_settings_are_restored(monkeypatch: pytest.MonkeyPatch) -> None:
    import lib_cli_exit_tools.cli as cli_mod

    class PlainStream:
        encoding = "cp1252"

        def isatty(self) -> bool:
            return False

    def fake_stream(_: str) -> PlainStream:
        return PlainStream()

    def failing_run_cli(*args: object, **kwargs: object) -> int:
        raise RuntimeError("boom")

    monkeypatch.setattr(cli_mod.click, "get_text_stream", fake_stream)
    monkeypatch.setattr(cli_mod.lib_cli_exit_tools, "run_cli", failing_run_cli)
    monkeypatch.setattr(lib_cli_exit_tools, "run_cli", failing_run_cli)
    baseline_force = cli_mod.rich_config.FORCE_TERMINAL
    baseline_color = cli_mod.rich_config.COLOR_SYSTEM
    with pytest.raises(RuntimeError):
        cli_mod.main(["info"])
    assert (baseline_force, baseline_color) == (cli_mod.rich_config.FORCE_TERMINAL, cli_mod.rich_config.COLOR_SYSTEM)


def test_when_only_one_stream_needs_plain_output_the_layout_stays_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    import lib_cli_exit_tools.cli as cli_mod

    class PlainStream:
        encoding = "cp1252"

        def isatty(self) -> bool:
            return False

    class UtfStream:
        encoding = "utf-8"

        def isatty(self) -> bool:
            return True

    streams = [PlainStream(), UtfStream()]

    def next_stream(_: str) -> object:
        return streams.pop(0)

    def fake_run_cli(*args: object, **kwargs: object) -> int:
        return 0

    monkeypatch.setattr(cli_mod.click, "get_text_stream", next_stream)
    monkeypatch.setattr(cli_mod.lib_cli_exit_tools, "run_cli", fake_run_cli)
    monkeypatch.setattr(lib_cli_exit_tools, "run_cli", fake_run_cli)
    baseline_force = cli_mod.rich_config.FORCE_TERMINAL
    baseline_color = cli_mod.rich_config.COLOR_SYSTEM
    cli_mod.main(["info"])
    assert (baseline_force, baseline_color) == (cli_mod.rich_config.FORCE_TERMINAL, cli_mod.rich_config.COLOR_SYSTEM)


def test_when_public_api_goes_out_of_sync_the_import_guard_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib

    facade = importlib.import_module("lib_cli_exit_tools.lib_cli_exit_tools")
    original_public_api = facade.PUBLIC_API
    monkeypatch.setattr(facade, "PUBLIC_API", original_public_api + ("made_up_symbol",))
    with pytest.raises(ImportError, match="exports out of sync"):
        importlib.reload(lib_cli_exit_tools)
    monkeypatch.setattr(facade, "PUBLIC_API", original_public_api)
    importlib.reload(lib_cli_exit_tools)


def test_when_public_api_is_reloaded_normally_the_module_imports_cleanly() -> None:
    import importlib

    module = importlib.reload(lib_cli_exit_tools)
    assert module.run_cli is lib_cli_exit_tools.run_cli


def test_when_main_module_is_imported_normally_it_does_not_exit() -> None:
    import importlib

    module = importlib.import_module("lib_cli_exit_tools.__main__")
    assert module.__name__ == "lib_cli_exit_tools.__main__"


def test_when_stream_says_utf_the_helper_returns_true() -> None:
    import lib_cli_exit_tools.cli as cli_mod

    def utf_stream() -> object:
        class Stream:
            encoding = "UTF-8"

        return Stream()

    supports_utf = getattr(cli_mod, "_stream_supports_utf")
    assert supports_utf(utf_stream()) is True


def test_when_stream_has_no_encoding_the_helper_returns_false() -> None:
    import lib_cli_exit_tools.cli as cli_mod

    class Stream:
        encoding = ""

    supports_utf = getattr(cli_mod, "_stream_supports_utf")
    assert supports_utf(Stream()) is False
