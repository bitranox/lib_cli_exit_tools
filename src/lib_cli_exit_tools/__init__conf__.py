"""Metadata facade that keeps CLI help/version text aligned with packaging data.

Purpose:
    Expose read-only metadata helpers the CLI can use without importing heavy
    packaging libraries.
Contents:
    * Metadata lookup helpers prefixed with ``_`` to cache and normalise states.
    * Public constants (`name`, `title`, `version`, etc.) derived from metadata.
    * :func:`print_info` for human-friendly provenance output.
System Integration:
    Read by :mod:`lib_cli_exit_tools.cli` and documented in
    ``docs/system-design/module_reference.md`` so CLI output matches project
    release metadata.
"""

from __future__ import annotations

from functools import cache
from importlib import metadata as _im
from importlib.metadata import PackageMetadata

#: Distribution identifier used for importlib.metadata lookups. Mirrors the
#: project name declared in ``pyproject.toml`` so metadata resolution stays in
#: sync with packaging configuration.
_DIST_NAME = "lib_cli_exit_tools"


def _get_str(meta: PackageMetadata | None, key: str, default: str = "") -> str:
    """Why:
        Normalise metadata lookups so CLI output stays predictable.
    What:
        Fetch the string value for ``key`` from ``meta`` or fall back to
        ``default`` when the entry is missing or not a plain string.
    Parameters:
        meta: Metadata mapping for the installed distribution, or ``None``
            when running from source.
        key: Field name to fetch (e.g. ``"Summary"``).
        default: Fallback string when the key is absent or unsuitable.
    Returns:
        The resolved string value to display in CLI output.
    Side Effects:
        None.
    """
    if meta is None:
        return default
    value = meta.get(key)
    return value if isinstance(value, str) else default


def _meta() -> PackageMetadata | None:
    """Why:
        Provide a single location that tolerates missing installations.
    What:
        Attempt to read the distribution metadata via ``importlib.metadata``.
    Parameters:
        None.
    Returns:
        Metadata mapping when available, otherwise ``None``.
    Side Effects:
        None.
    """
    try:
        meta: PackageMetadata = _im.metadata(_DIST_NAME)
        return meta
    except _im.PackageNotFoundError:
        return None


def _version() -> str:
    """Why:
        Surface the installed version for CLI flags and documentation.
    What:
        Retrieve the distribution version, falling back to a development label
        when metadata is unavailable.
    Parameters:
        None.
    Returns:
        Semantic-version string.
    Side Effects:
        None.
    Examples:
        >>> isinstance(_version(), str)
        True
    """
    try:
        return _im.version(_DIST_NAME)
    except _im.PackageNotFoundError:
        return "0.0.0.dev0"


def _home_page(meta: PackageMetadata | None) -> str:
    """Why:
        Normalise homepage lookups across build backends.
    What:
        Return the documented project homepage, favouring metadata values but
        defaulting to GitHub when absent.
    Parameters:
        meta: Metadata mapping or ``None`` when unavailable.
    Returns:
        Homepage URL string.
    Side Effects:
        None.
    """
    if meta is None:
        return "https://github.com/bitranox/lib_cli_exit_tools"
    primary = _get_str(meta, "Home-page")
    fallback = _get_str(meta, "Homepage")
    return primary or fallback or "https://github.com/bitranox/lib_cli_exit_tools"


def _author(meta: PackageMetadata | None) -> tuple[str, str]:
    """Why:
        Ensure provenance output always includes a name and contact address.
    What:
        Extract the author name and email from metadata, applying defaults.
    Parameters:
        meta: Metadata mapping or ``None`` when unavailable.
    Returns:
        Tuple of ``(author_name, author_email)``.
    Side Effects:
        None.
    """
    if meta is None:
        return ("bitranox", "bitranox@gmail.com")
    return (
        _get_str(meta, "Author", "bitranox"),
        _get_str(meta, "Author-email", "bitranox@gmail.com"),
    )


def _summary(meta: PackageMetadata | None) -> str:
    """Why:
        Guarantee a descriptive summary in CLI output even when metadata is sparse.
    What:
        Return the ``Summary`` field or a human-readable default.
    Parameters:
        meta: Metadata mapping or ``None`` when missing.
    Returns:
        Summary string.
    Side Effects:
        None.
    """
    return _get_str(meta, "Summary", "Functions to exit a CLI application properly")


@cache
def _shell_command() -> str:
    """Why:
        Surface the console-script name so documentation matches installation.
    What:
        Inspect entry points for the target referencing ``cli:main`` and return
        its advertised name.
    Parameters:
        None.
    Returns:
        Console-script name or the distribution identifier when unresolved.
    Side Effects:
        None.
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
    """Why:
        Offer operators a quick snapshot of build provenance and support links.
    What:
        Emit a formatted block containing metadata derived from this module.
    Parameters:
        None.
    Returns:
        ``None``.
    Side Effects:
        Writes text to ``stdout``.
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
