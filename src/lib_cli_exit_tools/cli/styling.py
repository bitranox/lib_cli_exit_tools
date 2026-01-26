"""Rich-click styling adapter for terminal capability detection.

Purpose:
    Detect terminal capabilities (TTY, encoding) and configure rich-click
    global styling accordingly, falling back to ASCII-safe defaults when
    the output stream cannot render Rich markup.
Contents:
    * :class:`RichClickSnapshot` typed snapshot of rich-click globals.
    * Stream inspection helpers for TTY and encoding detection.
    * :func:`_temporary_rich_click_configuration` context manager.
System Integration:
    Called by :func:`lib_cli_exit_tools.cli.group.main` before every CLI
    invocation to ensure rich-click output matches terminal capabilities.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator, TypedDict

import rich_click as click
from rich_click import rich_click as rich_config


class RichClickSnapshot(TypedDict):
    """Type-safe snapshot of rich-click global styling configuration.

    Attributes:
        FORCE_TERMINAL: Whether to force terminal styling.
        COLOR_SYSTEM: Color system to use (e.g., "auto", "256", "truecolor", None).
        STYLE_OPTIONS_PANEL_BOX: Box style for options panel.
        STYLE_COMMANDS_PANEL_BOX: Box style for commands panel.
        STYLE_ERRORS_PANEL_BOX: Box style for errors panel.

    Note:
        Uses Any for field types to accommodate the dynamic nature of rich-click
        configuration, which doesn't provide stable typing guarantees.
    """

    FORCE_TERMINAL: Any
    COLOR_SYSTEM: Any
    STYLE_OPTIONS_PANEL_BOX: Any
    STYLE_COMMANDS_PANEL_BOX: Any
    STYLE_ERRORS_PANEL_BOX: Any


def _needs_plain_output(stream: object) -> bool:
    """Tell whether ``stream`` will honour Rich styling."""

    return (not _stream_is_tty(stream)) or (not _stream_supports_utf(stream))


def _stream_is_tty(stream: object) -> bool:
    """Return ``True`` when ``stream`` behaves like a TTY."""
    checker = getattr(stream, "isatty", lambda: False)
    try:
        return bool(checker())
    except Exception:  # pragma: no cover - defensive shield
        return False


def _stream_supports_utf(stream: object) -> bool:
    """Tell whether ``stream`` reports a UTF-friendly encoding."""
    encoding = (getattr(stream, "encoding", "") or "").lower()
    return "utf" in encoding


def _prefer_ascii_layout() -> None:
    """Downgrade rich-click global styling to ASCII-friendly defaults."""
    rich_config.FORCE_TERMINAL = False
    rich_config.COLOR_SYSTEM = None
    rich_config.STYLE_OPTIONS_PANEL_BOX = None
    rich_config.STYLE_COMMANDS_PANEL_BOX = None
    rich_config.STYLE_ERRORS_PANEL_BOX = None


def _snapshot_rich_click_options() -> RichClickSnapshot:
    """Capture rich-click global styling toggles for later restoration."""

    return RichClickSnapshot(
        FORCE_TERMINAL=getattr(rich_config, "FORCE_TERMINAL", None),
        COLOR_SYSTEM=getattr(rich_config, "COLOR_SYSTEM", None),
        STYLE_OPTIONS_PANEL_BOX=getattr(rich_config, "STYLE_OPTIONS_PANEL_BOX", None),
        STYLE_COMMANDS_PANEL_BOX=getattr(rich_config, "STYLE_COMMANDS_PANEL_BOX", None),
        STYLE_ERRORS_PANEL_BOX=getattr(rich_config, "STYLE_ERRORS_PANEL_BOX", None),
    )


def _restore_rich_click_options(snapshot: RichClickSnapshot) -> None:
    """Restore rich-click globals to the captured snapshot."""

    rich_config.FORCE_TERMINAL = snapshot["FORCE_TERMINAL"]
    rich_config.COLOR_SYSTEM = snapshot["COLOR_SYSTEM"]
    rich_config.STYLE_OPTIONS_PANEL_BOX = snapshot["STYLE_OPTIONS_PANEL_BOX"]
    rich_config.STYLE_COMMANDS_PANEL_BOX = snapshot["STYLE_COMMANDS_PANEL_BOX"]
    rich_config.STYLE_ERRORS_PANEL_BOX = snapshot["STYLE_ERRORS_PANEL_BOX"]


@contextmanager
def _temporary_rich_click_configuration() -> Iterator[None]:  # pyright: ignore[reportUnusedFunction]
    """Apply plain-output safeguards and restore rich-click globals afterwards."""

    snapshot = _snapshot_rich_click_options()
    stdout_stream = click.get_text_stream("stdout")
    stderr_stream = click.get_text_stream("stderr")
    if _needs_plain_output(stdout_stream) and _needs_plain_output(stderr_stream):
        _prefer_ascii_layout()
    try:
        yield
    finally:
        _restore_rich_click_options(snapshot)
