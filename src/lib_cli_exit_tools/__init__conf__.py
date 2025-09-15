"""Runtime metadata facade loaded from installed package metadata.

Reads values from the installed distribution's metadata via `importlib.metadata`
so that `pyproject.toml` remains the single source of truth.

Falls back to defaults when not installed (e.g., running from a working tree
without an editable install).
"""

from __future__ import annotations

from importlib import metadata as _im
from typing import Any, Protocol, runtime_checkable

_DIST_NAME = "lib_cli_exit_tools"


@runtime_checkable
class _MetaMapping(Protocol):
    """Minimal protocol for package metadata across Python versions.

    On Python < 3.12, `importlib.metadata.metadata()` returns an
    `email.message.Message` which supports `.get(key, default)`.
    On Python >= 3.12, it returns `PackageMetadata`, which also supports `.get`.
    We type to this protocol to keep Pyright happy on 3.10.
    """

    def get(self, __key: str, __default: object = ...) -> object: ...


def _get_str(m: _MetaMapping, key: str, default: str = "") -> str:
    """Return metadata value as string or a default if missing/not a string."""
    v = m.get(key, default)
    return v if isinstance(v, str) else default


def _meta() -> Any | None:
    try:
        return _im.metadata(_DIST_NAME)
    except _im.PackageNotFoundError:
        return None


def _version() -> str:
    try:
        return _im.version(_DIST_NAME)
    except _im.PackageNotFoundError:
        return "0.0.0.dev0"


def _home_page(m: Any | None) -> str:
    if not m:
        return "https://github.com/bitranox/lib_cli_exit_tools"
    # cast to protocol for typing purposes
    mm: _MetaMapping = m  # type: ignore[assignment]
    hp = _get_str(mm, "Home-page") or _get_str(mm, "Homepage")
    return hp or "https://github.com/bitranox/lib_cli_exit_tools"


def _author(m: Any | None) -> tuple[str, str]:
    if not m:
        return ("bitranox", "bitranox@gmail.com")
    mm: _MetaMapping = m  # type: ignore[assignment]
    return (_get_str(mm, "Author", ""), _get_str(mm, "Author-email", ""))


def _summary(m: Any | None) -> str:
    if not m:
        return "Functions to exit a CLI application properly"
    mm: _MetaMapping = m  # type: ignore[assignment]
    return _get_str(mm, "Summary", "Functions to exit a CLI application properly")


def _shell_command() -> str:
    # Discover console script name mapping to our CLI main, fallback to dist name
    eps = _im.entry_points(group="console_scripts")
    target = "lib_cli_exit_tools.cli:main"
    for ep in list(eps):
        if ep.value == target:
            return ep.name
    return _DIST_NAME


# Public values (resolve metadata once)
_m = _meta()
name = _DIST_NAME
title = _summary(_m)
version = _version()
homepage = _home_page(_m)
author, author_email = _author(_m)
shell_command = _shell_command()


def print_info() -> None:
    """Print resolved metadata in a compact, aligned block."""
    fields = [
        ("name", name),
        ("title", title),
        ("version", version),
        ("homepage", homepage),
        ("author", author),
        ("author_email", author_email),
        ("shell_command", shell_command),
    ]
    pad = max(len(k) for k, _ in fields)
    lines = [f"Info for {name}:", ""]
    lines += [f"    {k.ljust(pad)} = {v}" for k, v in fields]
    print("\n".join(lines))
