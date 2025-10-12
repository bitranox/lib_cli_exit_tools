"""Metadata stories ensuring importlib fallbacks stay predictable."""

from __future__ import annotations

import importlib

import pytest

from lib_cli_exit_tools import __init__conf__ as metadata


@pytest.mark.os_agnostic
def test_when_print_info_runs_it_lists_every_field(capsys: pytest.CaptureFixture[str]) -> None:
    metadata.print_info()

    captured = capsys.readouterr().out

    for label in ("name", "title", "version", "homepage", "author", "author_email", "shell_command"):
        assert label in captured


@pytest.mark.os_agnostic
def test_when_distribution_is_missing_fallback_values_surface(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class FailingLookup:
        def __call__(self, _dist: str) -> None:
            raise metadata._im.PackageNotFoundError  # type: ignore[attr-defined]

    with monkeypatch.context() as ctx:
        ctx.setattr(metadata._im, "metadata", FailingLookup())  # type: ignore[attr-defined]
        ctx.setattr(metadata._im, "version", FailingLookup())  # type: ignore[attr-defined]
        reloaded = importlib.reload(metadata)

        reloaded.print_info()

        captured = capsys.readouterr().out

        assert "0.0.0.dev0" in captured
        assert "lib_cli_exit_tools" in captured
        assert "bitranox@gmail.com" in captured

    importlib.reload(metadata)


@pytest.mark.os_agnostic
def test_when_shell_command_is_resolved_matching_entry_point_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    class EntryPoint:
        def __init__(self, name: str, value: str) -> None:
            self.name = name
            self.value = value

    def fake_entry_points(*, group: str) -> list[EntryPoint]:
        assert group == "console_scripts"
        return [
            EntryPoint("alt-cli", "other.module:main"),
            EntryPoint("lib-cli-exit-tools", "lib_cli_exit_tools.cli:main"),
        ]

    with monkeypatch.context() as ctx:
        ctx.setattr(metadata._im, "entry_points", fake_entry_points)  # type: ignore[attr-defined]
        reloaded = importlib.reload(metadata)

        assert reloaded.shell_command == "lib-cli-exit-tools"

    importlib.reload(metadata)


@pytest.mark.os_agnostic
def test_when_shell_command_has_no_match_the_distribution_name_is_used(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_entry_points(*, group: str) -> list[object]:
        assert group == "console_scripts"
        return []

    with monkeypatch.context() as ctx:
        ctx.setattr(metadata._im, "entry_points", fake_entry_points)  # type: ignore[attr-defined]
        reloaded = importlib.reload(metadata)
        assert reloaded.shell_command == "lib_cli_exit_tools"

    importlib.reload(metadata)


@pytest.mark.os_agnostic
def test_when_metadata_values_are_not_strings_defaults_apply(monkeypatch: pytest.MonkeyPatch) -> None:
    class OddMeta:
        def get(self, key: str, default: object | None = None) -> object:
            return 123

    def fake_metadata(_dist: str) -> OddMeta:
        return OddMeta()

    with monkeypatch.context() as ctx:
        ctx.setattr(metadata._im, "metadata", fake_metadata)  # type: ignore[attr-defined]
        reloaded = importlib.reload(metadata)

        assert reloaded.author == "bitranox"
        assert reloaded.author_email == "bitranox@gmail.com"
        assert reloaded.title == "Functions to exit a CLI application properly"

    importlib.reload(metadata)
