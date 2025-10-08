"""Metadata facade that keeps CLI help/version text aligned with packaging data."""

from __future__ import annotations

from functools import cache
from importlib import metadata as _im
from importlib.metadata import PackageMetadata

#: Distribution identifier used for importlib.metadata lookups.
_DIST_NAME = "lib_cli_exit_tools"


def _get_str(meta: PackageMetadata | None, key: str, default: str = "") -> str:
    if meta is None:
        return default
    value = meta.get(key)
    return value if isinstance(value, str) else default


def _meta() -> PackageMetadata | None:
    try:
        meta: PackageMetadata = _im.metadata(_DIST_NAME)
        return meta
    except _im.PackageNotFoundError:
        return None


def _version() -> str:
    """Resolve the installed distribution version string.

    Why:
        Feed the Click ``--version`` option without importing ``pkg_resources``.
    Returns:
        Version string, falling back to ``"0.0.0.dev0"`` when the distribution
        is not installed.
    Examples:
        >>> isinstance(_version(), str)
        True
    """
    try:
        return _im.version(_DIST_NAME)
    except _im.PackageNotFoundError:
        return "0.0.0.dev0"


def _home_page(meta: PackageMetadata | None) -> str:
    if meta is None:
        return "https://github.com/bitranox/lib_cli_exit_tools"
    primary = _get_str(meta, "Home-page")
    fallback = _get_str(meta, "Homepage")
    return primary or fallback or "https://github.com/bitranox/lib_cli_exit_tools"


def _author(meta: PackageMetadata | None) -> tuple[str, str]:
    if meta is None:
        return ("bitranox", "bitranox@gmail.com")
    return (
        _get_str(meta, "Author", "bitranox"),
        _get_str(meta, "Author-email", "bitranox@gmail.com"),
    )


def _summary(meta: PackageMetadata | None) -> str:
    return _get_str(meta, "Summary", "Functions to exit a CLI application properly")


@cache
def _shell_command() -> str:
    """Discover the console-script entry point bound to the CLI.

    Why:
        Ensure ``--version`` text and docs refer to the actual command name users
        will run after installation.
    Returns:
        Console script name or the distribution name when no entry point exists.
    Examples:
        >>> isinstance(_shell_command(), str)
        True
    """
    # Discover console script name mapping to our CLI main, fallback to dist name
    entries = _im.entry_points(group="console_scripts")
    target = "lib_cli_exit_tools.cli:main"
    for entry in entries:
        if entry.value == target:
            return entry.name
    return _DIST_NAME


# Public values (resolve metadata once)
#: Cached metadata mapping to avoid repeated importlib lookups.
_m = _meta()
#: Distribution name used when metadata lookups fail.
name = _DIST_NAME
#: Human-readable project title displayed in CLI help.
title = _summary(_m)
#: Installed package version string surfaced via --version.
version = _version()
#: Project homepage for documentation and issue reporting.
homepage = _home_page(_m)
#: Primary author details used in info output.
author, author_email = _author(_m)
#: Console script entry point that launches this CLI.
shell_command = _shell_command()


def print_info() -> None:
    """Render resolved metadata in an aligned text block.

    Why:
        Provide a single CLI command that surfaces build provenance and support
        links for debugging or audit purposes.
    Returns:
        ``None``.
    Side Effects:
        Writes formatted text to stdout.
    Examples:
        >>> import contextlib, io
        >>> buf = io.StringIO()
        >>> with contextlib.redirect_stdout(buf):
        ...     print_info()
        >>> "Info for" in buf.getvalue()
        True
    """
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
