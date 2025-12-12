"""Tests for metadata consistency between pyproject.toml and __init__conf__.py.

Each test verifies exactly one metadata behavior:
- print_info() lists all expected fields
- Metadata constants match pyproject.toml values
"""

from __future__ import annotations

import runpy
from pathlib import Path
from typing import Any, cast

import pytest
import rtoml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PYPROJECT_PATH = PROJECT_ROOT / "pyproject.toml"
TARGET_FIELDS = ("name", "title", "version", "homepage", "author", "author_email", "shell_command")


# =============================================================================
# Helper Functions
# =============================================================================


def _load_pyproject() -> dict[str, Any]:
    return rtoml.load(PYPROJECT_PATH)


def _resolve_init_conf_path(pyproject: dict[str, Any]) -> Path:
    project_table = cast(dict[str, Any], pyproject["project"])
    tool_table = cast(dict[str, Any], pyproject.get("tool", {}))
    hatch_table = cast(dict[str, Any], tool_table.get("hatch", {}))
    targets_table = cast(dict[str, Any], cast(dict[str, Any], hatch_table.get("build", {})).get("targets", {}))
    wheel_table = cast(dict[str, Any], targets_table.get("wheel", {}))
    packages = cast(list[Any], wheel_table.get("packages", []))

    for package_entry in packages:
        if isinstance(package_entry, str):
            candidate = PROJECT_ROOT / package_entry / "__init__conf__.py"
            if candidate.is_file():
                return candidate

    fallback = PROJECT_ROOT / "src" / project_table["name"].replace("-", "_") / "__init__conf__.py"
    if fallback.is_file():
        return fallback

    raise AssertionError("Unable to locate __init__conf__.py")


def _load_init_conf_metadata(init_conf_path: Path) -> dict[str, str]:
    fragments: list[str] = []
    for raw_line in init_conf_path.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        for key in TARGET_FIELDS:
            prefix = f"{key} = "
            if stripped.startswith(prefix):
                fragments.append(stripped)
                break
    if not fragments:
        raise AssertionError("No metadata assignments found in __init__conf__.py")
    metadata_text = "[metadata]\n" + "\n".join(fragments)
    parsed = rtoml.loads(metadata_text)
    metadata_table = cast(dict[str, str], parsed["metadata"])
    return metadata_table


def _load_init_conf_module(init_conf_path: Path) -> dict[str, Any]:
    return runpy.run_path(str(init_conf_path))


# =============================================================================
# print_info() Tests
# =============================================================================


@pytest.mark.os_agnostic
def test_print_info_runs_without_error(capsys: pytest.CaptureFixture[str]) -> None:
    pyproject = _load_pyproject()
    init_conf_path = _resolve_init_conf_path(pyproject)
    init_conf_module = _load_init_conf_module(init_conf_path)

    print_info = init_conf_module["print_info"]
    print_info()

    # Should not raise


@pytest.mark.os_agnostic
def test_print_info_shows_name_field(capsys: pytest.CaptureFixture[str]) -> None:
    pyproject = _load_pyproject()
    init_conf_path = _resolve_init_conf_path(pyproject)
    init_conf_module = _load_init_conf_module(init_conf_path)

    print_info = init_conf_module["print_info"]
    print_info()

    assert "name" in capsys.readouterr().out


@pytest.mark.os_agnostic
def test_print_info_shows_version_field(capsys: pytest.CaptureFixture[str]) -> None:
    pyproject = _load_pyproject()
    init_conf_path = _resolve_init_conf_path(pyproject)
    init_conf_module = _load_init_conf_module(init_conf_path)

    print_info = init_conf_module["print_info"]
    print_info()

    assert "version" in capsys.readouterr().out


@pytest.mark.os_agnostic
def test_print_info_shows_homepage_field(capsys: pytest.CaptureFixture[str]) -> None:
    pyproject = _load_pyproject()
    init_conf_path = _resolve_init_conf_path(pyproject)
    init_conf_module = _load_init_conf_module(init_conf_path)

    print_info = init_conf_module["print_info"]
    print_info()

    assert "homepage" in capsys.readouterr().out


@pytest.mark.os_agnostic
def test_print_info_shows_author_field(capsys: pytest.CaptureFixture[str]) -> None:
    pyproject = _load_pyproject()
    init_conf_path = _resolve_init_conf_path(pyproject)
    init_conf_module = _load_init_conf_module(init_conf_path)

    print_info = init_conf_module["print_info"]
    print_info()

    assert "author" in capsys.readouterr().out


# =============================================================================
# Metadata Constant Consistency
# =============================================================================


@pytest.mark.os_agnostic
def test_metadata_name_matches_pyproject() -> None:
    pyproject = _load_pyproject()
    project_table = cast(dict[str, Any], pyproject["project"])
    init_conf_path = _resolve_init_conf_path(pyproject)
    metadata = _load_init_conf_metadata(init_conf_path)

    assert metadata["name"] == project_table["name"]


@pytest.mark.os_agnostic
def test_metadata_title_matches_pyproject_description() -> None:
    pyproject = _load_pyproject()
    project_table = cast(dict[str, Any], pyproject["project"])
    init_conf_path = _resolve_init_conf_path(pyproject)
    metadata = _load_init_conf_metadata(init_conf_path)

    assert metadata["title"] == project_table["description"]


@pytest.mark.os_agnostic
def test_metadata_version_matches_pyproject() -> None:
    pyproject = _load_pyproject()
    project_table = cast(dict[str, Any], pyproject["project"])
    init_conf_path = _resolve_init_conf_path(pyproject)
    metadata = _load_init_conf_metadata(init_conf_path)

    assert metadata["version"] == project_table["version"]


@pytest.mark.os_agnostic
def test_metadata_homepage_matches_pyproject_urls() -> None:
    pyproject = _load_pyproject()
    project_table = cast(dict[str, Any], pyproject["project"])
    init_conf_path = _resolve_init_conf_path(pyproject)
    metadata = _load_init_conf_metadata(init_conf_path)
    urls = cast(dict[str, str], project_table.get("urls", {}))

    assert "Homepage" in urls, "pyproject.toml must define project.urls.Homepage"
    assert metadata["homepage"] == urls["Homepage"]


@pytest.mark.os_agnostic
def test_metadata_author_matches_pyproject() -> None:
    pyproject = _load_pyproject()
    project_table = cast(dict[str, Any], pyproject["project"])
    init_conf_path = _resolve_init_conf_path(pyproject)
    metadata = _load_init_conf_metadata(init_conf_path)
    authors = cast(list[dict[str, str]], project_table.get("authors", []))

    assert authors, "pyproject.toml must declare at least one author entry"
    assert metadata["author"] == authors[0]["name"]


@pytest.mark.os_agnostic
def test_metadata_author_email_matches_pyproject() -> None:
    pyproject = _load_pyproject()
    project_table = cast(dict[str, Any], pyproject["project"])
    init_conf_path = _resolve_init_conf_path(pyproject)
    metadata = _load_init_conf_metadata(init_conf_path)
    authors = cast(list[dict[str, str]], project_table.get("authors", []))

    assert authors, "pyproject.toml must declare at least one author entry"
    assert metadata["author_email"] == authors[0]["email"]


@pytest.mark.os_agnostic
def test_metadata_shell_command_is_in_pyproject_scripts() -> None:
    pyproject = _load_pyproject()
    project_table = cast(dict[str, Any], pyproject["project"])
    init_conf_path = _resolve_init_conf_path(pyproject)
    metadata = _load_init_conf_metadata(init_conf_path)
    scripts = cast(dict[str, Any], project_table.get("scripts", {}))

    assert metadata["shell_command"] in scripts
