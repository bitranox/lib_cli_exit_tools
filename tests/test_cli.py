"""CLI stories verifying lib_cli_exit_tools' Click adapter."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from click.testing import CliRunner, Result

import lib_cli_exit_tools
from lib_cli_exit_tools import cli as cli_mod
from lib_cli_exit_tools import __init__conf__ as metadata
from lib_cli_exit_tools.application import runner as runner_mod


@pytest.mark.os_agnostic
def test_when_main_is_called_it_delegates_to_run_cli(monkeypatch: pytest.MonkeyPatch) -> None:
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
        ledger.update(
            {
                "command": command,
                "argv": argv,
                "prog_name": prog_name,
                "install_signals": install_signals,
                "exception_handler": exception_handler,
                "signal_installer": signal_installer,
            }
        )
        return 123

    monkeypatch.setattr("lib_cli_exit_tools.lib_cli_exit_tools.run_cli", fake_run_cli)
    monkeypatch.setattr(runner_mod, "run_cli", fake_run_cli)

    exit_code = cli_mod.main(["info"])

    assert exit_code == 123
    assert ledger["command"] is cli_mod.cli
    assert ledger["argv"] == ["info"]
    assert ledger["prog_name"] == metadata.shell_command


@pytest.mark.os_agnostic
def test_when_traceback_flag_is_used_the_configuration_is_enabled(
    cli_runner: CliRunner,
    preserve_traceback_state: None,
) -> None:
    lib_cli_exit_tools.reset_config()

    result: Result = cli_runner.invoke(cli_mod.cli, ["--traceback", "info"])

    assert result.exit_code == 0
    assert lib_cli_exit_tools.config.traceback is True


@pytest.mark.os_agnostic
def test_when_info_is_invoked_metadata_is_displayed(cli_runner: CliRunner, strip_ansi: Callable[[str], str]) -> None:
    result: Result = cli_runner.invoke(cli_mod.cli, ["info"])
    plain_output = strip_ansi(result.output)

    assert result.exit_code == 0
    assert f"Info for {metadata.name}:" in plain_output
    for field in ("name", "title", "version", "homepage", "author", "author_email", "shell_command"):
        assert field in plain_output


@pytest.mark.os_agnostic
def test_when_version_flag_is_used_metadata_banner_is_returned(
    cli_runner: CliRunner,
    strip_ansi: Callable[[str], str],
) -> None:
    result: Result = cli_runner.invoke(cli_mod.cli, ["--version"])
    plain_output = strip_ansi(result.output).strip()

    assert result.exit_code == 0
    assert plain_output == f"{metadata.shell_command} version {metadata.version}"


@pytest.mark.os_agnostic
def test_when_fail_is_invoked_a_runtime_error_surfaces(cli_runner: CliRunner) -> None:
    result: Result = cli_runner.invoke(cli_mod.cli, ["fail"])

    assert result.exit_code == 1
    assert isinstance(result.exception, RuntimeError)
    assert "i should fail" in str(result.exception)


@pytest.mark.os_agnostic
def test_when_unknown_command_is_used_a_helpful_message_is_emitted(cli_runner: CliRunner, strip_ansi: Callable[[str], str]) -> None:
    result: Result = cli_runner.invoke(cli_mod.cli, ["does-not-exist"])
    plain_output = strip_ansi(result.output)

    assert result.exit_code != 0
    assert "No such command" in plain_output


@pytest.mark.os_agnostic
def test_when_stream_supports_utf_recognises_encoding_true_for_utf(monkeypatch: pytest.MonkeyPatch) -> None:
    stream = type("Stream", (), {"encoding": "UTF-8"})()
    assert cli_mod._stream_supports_utf(stream) is True  # pyright: ignore[reportPrivateUsage]


@pytest.mark.os_agnostic
def test_when_stream_supports_utf_returns_false_for_non_utf(monkeypatch: pytest.MonkeyPatch) -> None:
    stream = type("Stream", (), {"encoding": "latin-1"})()
    assert cli_mod._stream_supports_utf(stream) is False  # pyright: ignore[reportPrivateUsage]


@pytest.mark.os_agnostic
def test_when_both_streams_need_plain_output_ascii_layout_is_preferred(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyStream:
        def __init__(self) -> None:
            self.encoding = "ascii"

        def isatty(self) -> bool:
            return False

    original = cli_mod._snapshot_rich_click_options()  # pyright: ignore[reportPrivateUsage]

    def fake_stream(_: str) -> DummyStream:
        return DummyStream()

    monkeypatch.setattr(cli_mod.click, "get_text_stream", fake_stream)

    with cli_mod._temporary_rich_click_configuration():  # pyright: ignore[reportPrivateUsage]
        assert cli_mod.rich_config.FORCE_TERMINAL is False
        assert cli_mod.rich_config.COLOR_SYSTEM is None

    for key, value in original.items():
        assert getattr(cli_mod.rich_config, key) == value


@pytest.mark.os_agnostic
def test_when_streams_support_rich_output_layout_is_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    class FancyStream:
        def __init__(self) -> None:
            self.encoding = "utf-8"

        def isatty(self) -> bool:
            return True

    original = cli_mod._snapshot_rich_click_options()  # pyright: ignore[reportPrivateUsage]

    def fancy_stream(_: str) -> FancyStream:
        return FancyStream()

    monkeypatch.setattr(cli_mod.click, "get_text_stream", fancy_stream)

    with cli_mod._temporary_rich_click_configuration():  # pyright: ignore[reportPrivateUsage]
        assert cli_mod.rich_config.COLOR_SYSTEM == original.get("COLOR_SYSTEM")

    for key, value in original.items():
        assert getattr(cli_mod.rich_config, key) == value
