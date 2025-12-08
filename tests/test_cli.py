"""Tests for the CLI adapter module.

Each test verifies exactly one CLI behavior:
- Command delegation to run_cli
- Traceback flag handling
- Info and version commands
- Stream encoding detection
- Rich-click configuration management
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from click.testing import CliRunner, Result

import lib_cli_exit_tools
from lib_cli_exit_tools import __init__conf__ as metadata
from lib_cli_exit_tools import cli as cli_mod
from lib_cli_exit_tools.application import runner as runner_mod


# =============================================================================
# Main Function Delegation
# =============================================================================


@pytest.mark.os_agnostic
def test_main_delegates_to_run_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    ledger: dict[str, Any] = {}

    def fake_run_cli(
        command: Any,
        *,
        argv: list[str] | None = None,
        prog_name: str | None = None,
        signal_specs: Any = None,
        install_signals: bool = True,
        exception_handler: Any = None,
        signal_installer: Any = None,
    ) -> int:
        ledger.update(command=command, argv=argv, prog_name=prog_name)
        return 123

    monkeypatch.setattr("lib_cli_exit_tools.lib_cli_exit_tools.run_cli", fake_run_cli)
    monkeypatch.setattr(runner_mod, "run_cli", fake_run_cli)

    exit_code = cli_mod.main(["info"])

    assert exit_code == 123


@pytest.mark.os_agnostic
def test_main_passes_command_to_run_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    ledger: dict[str, Any] = {}

    def fake_run_cli(command: Any, **kwargs: Any) -> int:
        ledger["command"] = command
        return 0

    monkeypatch.setattr("lib_cli_exit_tools.lib_cli_exit_tools.run_cli", fake_run_cli)
    monkeypatch.setattr(runner_mod, "run_cli", fake_run_cli)

    cli_mod.main(["info"])

    assert ledger["command"] is cli_mod.cli


@pytest.mark.os_agnostic
def test_main_passes_prog_name_from_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    ledger: dict[str, Any] = {}

    def fake_run_cli(command: Any, *, prog_name: str | None = None, **kwargs: Any) -> int:
        ledger["prog_name"] = prog_name
        return 0

    monkeypatch.setattr("lib_cli_exit_tools.lib_cli_exit_tools.run_cli", fake_run_cli)
    monkeypatch.setattr(runner_mod, "run_cli", fake_run_cli)

    cli_mod.main(["info"])

    assert ledger["prog_name"] == metadata.shell_command


# =============================================================================
# Traceback Flag
# =============================================================================


@pytest.mark.os_agnostic
def test_traceback_flag_enables_traceback_config(
    cli_runner: CliRunner,
    preserve_traceback_state: None,
) -> None:
    lib_cli_exit_tools.reset_config()

    cli_runner.invoke(cli_mod.cli, ["--traceback", "info"])

    assert lib_cli_exit_tools.config.traceback is True


@pytest.mark.os_agnostic
def test_traceback_flag_allows_successful_command_execution(
    cli_runner: CliRunner,
    preserve_traceback_state: None,
) -> None:
    lib_cli_exit_tools.reset_config()

    result: Result = cli_runner.invoke(cli_mod.cli, ["--traceback", "info"])

    assert result.exit_code == 0


# =============================================================================
# Info Command
# =============================================================================


@pytest.mark.os_agnostic
def test_info_command_succeeds(cli_runner: CliRunner) -> None:
    result: Result = cli_runner.invoke(cli_mod.cli, ["info"])
    assert result.exit_code == 0


@pytest.mark.os_agnostic
def test_info_command_shows_package_name(cli_runner: CliRunner, strip_ansi: Callable[[str], str]) -> None:
    result: Result = cli_runner.invoke(cli_mod.cli, ["info"])
    plain_output = strip_ansi(result.output)
    assert f"Info for {metadata.name}:" in plain_output


@pytest.mark.os_agnostic
def test_info_command_shows_name_field(cli_runner: CliRunner, strip_ansi: Callable[[str], str]) -> None:
    result: Result = cli_runner.invoke(cli_mod.cli, ["info"])
    assert "name" in strip_ansi(result.output)


@pytest.mark.os_agnostic
def test_info_command_shows_version_field(cli_runner: CliRunner, strip_ansi: Callable[[str], str]) -> None:
    result: Result = cli_runner.invoke(cli_mod.cli, ["info"])
    assert "version" in strip_ansi(result.output)


@pytest.mark.os_agnostic
def test_info_command_shows_homepage_field(cli_runner: CliRunner, strip_ansi: Callable[[str], str]) -> None:
    result: Result = cli_runner.invoke(cli_mod.cli, ["info"])
    assert "homepage" in strip_ansi(result.output)


# =============================================================================
# Version Flag
# =============================================================================


@pytest.mark.os_agnostic
def test_version_flag_succeeds(cli_runner: CliRunner) -> None:
    result: Result = cli_runner.invoke(cli_mod.cli, ["--version"])
    assert result.exit_code == 0


@pytest.mark.os_agnostic
def test_version_flag_shows_shell_command(cli_runner: CliRunner, strip_ansi: Callable[[str], str]) -> None:
    result: Result = cli_runner.invoke(cli_mod.cli, ["--version"])
    plain_output = strip_ansi(result.output).strip()
    assert plain_output == f"{metadata.shell_command} version {metadata.version}"


# =============================================================================
# Fail Command
# =============================================================================


@pytest.mark.os_agnostic
def test_fail_command_raises_runtime_error(cli_runner: CliRunner) -> None:
    result: Result = cli_runner.invoke(cli_mod.cli, ["fail"])
    assert isinstance(result.exception, RuntimeError)


@pytest.mark.os_agnostic
def test_fail_command_exits_with_nonzero(cli_runner: CliRunner) -> None:
    result: Result = cli_runner.invoke(cli_mod.cli, ["fail"])
    assert result.exit_code == 1


@pytest.mark.os_agnostic
def test_fail_command_error_message_is_correct(cli_runner: CliRunner) -> None:
    result: Result = cli_runner.invoke(cli_mod.cli, ["fail"])
    assert "i should fail" in str(result.exception)


# =============================================================================
# Unknown Command
# =============================================================================


@pytest.mark.os_agnostic
def test_unknown_command_exits_nonzero(cli_runner: CliRunner) -> None:
    result: Result = cli_runner.invoke(cli_mod.cli, ["does-not-exist"])
    assert result.exit_code != 0


@pytest.mark.os_agnostic
def test_unknown_command_shows_helpful_message(cli_runner: CliRunner, strip_ansi: Callable[[str], str]) -> None:
    result: Result = cli_runner.invoke(cli_mod.cli, ["does-not-exist"])
    assert "No such command" in strip_ansi(result.output)


# =============================================================================
# Stream UTF Support Detection
# =============================================================================


@pytest.mark.os_agnostic
def test_stream_supports_utf_returns_true_for_utf8() -> None:
    stream = type("Stream", (), {"encoding": "UTF-8"})()
    assert cli_mod._stream_supports_utf(stream) is True  # pyright: ignore[reportPrivateUsage]


@pytest.mark.os_agnostic
def test_stream_supports_utf_returns_true_for_utf16() -> None:
    stream = type("Stream", (), {"encoding": "utf-16"})()
    assert cli_mod._stream_supports_utf(stream) is True  # pyright: ignore[reportPrivateUsage]


@pytest.mark.os_agnostic
def test_stream_supports_utf_returns_false_for_latin1() -> None:
    stream = type("Stream", (), {"encoding": "latin-1"})()
    assert cli_mod._stream_supports_utf(stream) is False  # pyright: ignore[reportPrivateUsage]


@pytest.mark.os_agnostic
def test_stream_supports_utf_returns_false_for_ascii() -> None:
    stream = type("Stream", (), {"encoding": "ascii"})()
    assert cli_mod._stream_supports_utf(stream) is False  # pyright: ignore[reportPrivateUsage]


# =============================================================================
# Rich-Click Configuration
# =============================================================================


@pytest.mark.os_agnostic
def test_ascii_streams_disable_force_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyStream:
        encoding = "ascii"

        def isatty(self) -> bool:
            return False

    original = cli_mod._snapshot_rich_click_options()  # pyright: ignore[reportPrivateUsage]

    def _get_dummy_stream(name: str) -> DummyStream:
        return DummyStream()

    monkeypatch.setattr(cli_mod.click, "get_text_stream", _get_dummy_stream)

    with cli_mod._temporary_rich_click_configuration():  # pyright: ignore[reportPrivateUsage]
        assert cli_mod.rich_config.FORCE_TERMINAL is False

    for key, value in original.items():
        assert getattr(cli_mod.rich_config, key) == value


@pytest.mark.os_agnostic
def test_ascii_streams_disable_color_system(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyStream:
        encoding = "ascii"

        def isatty(self) -> bool:
            return False

    original = cli_mod._snapshot_rich_click_options()  # pyright: ignore[reportPrivateUsage]

    def _get_dummy_stream(name: str) -> DummyStream:
        return DummyStream()

    monkeypatch.setattr(cli_mod.click, "get_text_stream", _get_dummy_stream)

    with cli_mod._temporary_rich_click_configuration():  # pyright: ignore[reportPrivateUsage]
        assert cli_mod.rich_config.COLOR_SYSTEM is None

    for key, value in original.items():
        assert getattr(cli_mod.rich_config, key) == value


@pytest.mark.os_agnostic
def test_utf8_tty_streams_preserve_color_system(monkeypatch: pytest.MonkeyPatch) -> None:
    class FancyStream:
        encoding = "utf-8"

        def isatty(self) -> bool:
            return True

    original = cli_mod._snapshot_rich_click_options()  # pyright: ignore[reportPrivateUsage]

    def _get_fancy_stream(name: str) -> FancyStream:
        return FancyStream()

    monkeypatch.setattr(cli_mod.click, "get_text_stream", _get_fancy_stream)

    with cli_mod._temporary_rich_click_configuration():  # pyright: ignore[reportPrivateUsage]
        assert cli_mod.rich_config.COLOR_SYSTEM == original.get("COLOR_SYSTEM")

    for key, value in original.items():
        assert getattr(cli_mod.rich_config, key) == value
