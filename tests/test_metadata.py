"""Metadata stories ensuring generated constants stay authoritative."""

from __future__ import annotations

import pytest

from lib_cli_exit_tools import __init__conf__ as metadata
from scripts import _utils


@pytest.mark.os_agnostic
def test_when_print_info_runs_it_lists_every_field(capsys: pytest.CaptureFixture[str]) -> None:
    metadata.print_info()

    captured = capsys.readouterr().out.splitlines()
    banner, *detail_lines = [line.strip() for line in captured if line.strip()]
    assert banner == f"Info for {metadata.name}:"

    rows = {}
    for line in detail_lines:
        if " = " not in line:
            continue
        label, value = line.split(" = ", 1)
        rows[label.strip()] = value.strip()

    assert rows == {
        "name": metadata.name,
        "title": metadata.title,
        "version": metadata.version,
        "homepage": metadata.homepage,
        "author": metadata.author,
        "author_email": metadata.author_email,
        "shell_command": metadata.shell_command,
    }


@pytest.mark.os_agnostic
def test_metadata_constants_match_pyproject() -> None:
    project = _utils.get_project_metadata()

    assert metadata.name == project.name
    assert metadata.title == project.summary
    assert metadata.version == project.version
    assert metadata.homepage == project.homepage or project.repo_url or ""
    assert metadata.author == project.author_name
    assert metadata.author_email == project.author_email
    assert metadata.shell_command == project.shell_command
