"""Runtime metadata facade loaded from installed package metadata.

Reads values from the installed distribution's metadata via `importlib.metadata`
so that `pyproject.toml` remains the single source of truth.

Falls back to defaults when not installed (e.g., running from a working tree
without an editable install).
"""

from __future__ import annotations

from importlib import metadata as _im
from importlib.metadata import EntryPoints as _EntryPoints

_DIST_NAME = "lib_cli_exit_tools"


def _meta() -> _im.PackageMetadata | None:
    try:
        return _im.metadata(_DIST_NAME)
    except _im.PackageNotFoundError:
        return None


def _version() -> str:
    try:
        return _im.version(_DIST_NAME)
    except _im.PackageNotFoundError:
        return "0.0.0.dev0"


def _home_page(m: _im.PackageMetadata | None) -> str:
    if not m:
        return "https://github.com/bitranox/lib_cli_exit_tools"
    return m.get("Home-page") or m.get("Homepage") or "https://github.com/bitranox/lib_cli_exit_tools"


def _author(m: _im.PackageMetadata | None) -> tuple[str, str]:
    if not m:
        return ("Robert Nowotny", "bitranox@gmail.com")
    return (m.get("Author", ""), m.get("Author-email", ""))


def _summary(m: _im.PackageMetadata | None) -> str:
    if not m:
        return "Functions to exit a CLI application properly"
    return m.get("Summary", "Functions to exit a CLI application properly")


def _shell_command() -> str:
    # Discover console script name mapping to our CLI main, fallback to dist name
    eps: _EntryPoints = _im.entry_points(group="console_scripts")
    target = "lib_cli_exit_tools.cli:main"
    for ep in list(eps):
        if ep.value == target:
            return ep.name
    return _DIST_NAME


# Public values
name = _DIST_NAME
title = _summary(_meta())
version = _version()
url = _home_page(_meta())
author, author_email = _author(_meta())
shell_command = _shell_command()


def print_info() -> None:
    """Print resolved metadata in a compact, aligned block."""
    fields = [
        ("name", name),
        ("title", title),
        ("version", version),
        ("url", url),
        ("author", author),
        ("author_email", author_email),
        ("shell_command", shell_command),
    ]
    pad = max(len(k) for k, _ in fields)
    lines = [f"Info for {name}:", ""]
    lines += [f"    {k.ljust(pad)} = {v}" for k, v in fields]
    print("\n".join(lines))
