"""Metadata facade that keeps CLI help/version text aligned with packaging data.

Purpose:
    Mirror :mod:`importlib.metadata` lookups so command output and documentation
    always reflect the installed distribution without duplicating literals.
Contents:
    * Lightweight protocol for metadata objects returned by
      :func:`importlib.metadata.metadata` across Python versions.
    * Helpers that resolve individual attributes (version, homepage, author).
    * Module-level constants exported to CLI consumers.
System Integration:
    :mod:`lib_cli_exit_tools.cli` calls into this module to populate ``--version``
    output and the ``info`` subcommand. Inline documentation references the same
    constants to keep project facts synchronized.
"""

from __future__ import annotations

from importlib import metadata as _im
from typing import Any, Protocol, runtime_checkable

#: Distribution identifier used for importlib.metadata lookups.
_DIST_NAME = "lib_cli_exit_tools"


@runtime_checkable
class _MetaMapping(Protocol):
    """Structural type covering legacy and modern metadata objects.

    Why:
        ``importlib.metadata.metadata`` returns ``Message`` objects on older
        Python versions and ``PackageMetadata`` on newer ones; both expose ``get``.
    Methods:
        get(str, object | None) -> object:
            Retrieve a metadata field with a default fallback.
    """

    def get(self, __key: str, __default: object = ...) -> object: ...


def _get_str(m: _MetaMapping, key: str, default: str = "") -> str:
    """Read a metadata field as a string with a safe fallback.

    Why:
        ``PackageMetadata`` values may not be strings (e.g., None or email headers).
        This helper normalises them for CLI output.
    Parameters:
        m: Metadata mapping returned by :mod:`importlib.metadata`.
        key: Metadata field name.
        default: Value to use when the field is missing or not a string.
    Returns:
        Extracted string or ``default``.
    Examples:
        >>> class Dummy(dict):
        ...     def get(self, key, default=""):
        ...         return super().get(key, default)
        >>> _get_str(Dummy({"Summary": "demo"}), "Summary", "fallback")
        'demo'
        >>> _get_str(Dummy({}), "Summary", "fallback")
        'fallback'
    """
    v = m.get(key, default)
    return v if isinstance(v, str) else default


def _meta() -> Any | None:
    """Return raw package metadata or ``None`` when the distribution is absent.

    Why:
        Downstream helpers reuse the same metadata object to avoid redundant
        :mod:`importlib.metadata` lookups.
    Returns:
        Metadata mapping or ``None`` if the project has not been installed.
    Examples:
        >>> result = _meta()
        >>> result is None or hasattr(result, "get")
        True
    """
    try:
        return _im.metadata(_DIST_NAME)
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


def _home_page(m: Any | None) -> str:
    """Extract the homepage URL from metadata with a GitHub fallback.

    Why:
        Keep CLI output pointing at the canonical documentation host.
    Parameters:
        m: Metadata mapping or ``None``.
    Returns:
        Homepage URL string.
    Examples:
        >>> _home_page(None)
        'https://github.com/bitranox/lib_cli_exit_tools'
    """
    if not m:
        return "https://github.com/bitranox/lib_cli_exit_tools"
    # cast to protocol for typing purposes
    mm: _MetaMapping = m  # type: ignore[assignment]
    hp = _get_str(mm, "Home-page") or _get_str(mm, "Homepage")
    return hp or "https://github.com/bitranox/lib_cli_exit_tools"


def _author(m: Any | None) -> tuple[str, str]:
    """Return author name/email pair with safe defaults.

    Why:
        Populate CLI info output even when metadata is missing or incomplete.
    Parameters:
        m: Metadata mapping or ``None``.
    Returns:
        Tuple ``(author_name, author_email)``.
    Examples:
        >>> _author(None)
        ('bitranox', 'bitranox@gmail.com')
    """
    if not m:
        return ("bitranox", "bitranox@gmail.com")
    mm: _MetaMapping = m  # type: ignore[assignment]
    return (_get_str(mm, "Author", ""), _get_str(mm, "Author-email", ""))


def _summary(m: Any | None) -> str:
    """Derive a human-friendly summary string.

    Why:
        Reuse the packaging summary for CLI help and docs.
    Parameters:
        m: Metadata mapping or ``None``.
    Returns:
        Summary text, falling back to a descriptive default.
    Examples:
        >>> _summary(None)
        'Functions to exit a CLI application properly'
    """
    if not m:
        return "Functions to exit a CLI application properly"
    mm: _MetaMapping = m  # type: ignore[assignment]
    return _get_str(mm, "Summary", "Functions to exit a CLI application properly")


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
    eps = _im.entry_points(group="console_scripts")
    target = "lib_cli_exit_tools.cli:main"
    for ep in list(eps):
        if ep.value == target:
            return ep.name
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
