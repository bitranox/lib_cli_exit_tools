"""Exit-code translation helpers for lib_cli_exit_tools.

Purpose:
    Provide deterministic mappings from Python exceptions to operating-system
    exit codes, honouring both POSIX/Windows errno semantics and BSD sysexits
    conventions.
Contents:
    * :func:`get_system_exit_code` – primary mapping entry point.
    * :func:`_sysexits_mapping` – internal helper for sysexits mode.
System Integration:
    Used by application orchestration and CLI adapters to convert unhandled
    exceptions into numeric exit statuses while respecting
    :data:`lib_cli_exit_tools.core.configuration.config` toggles.
"""

from __future__ import annotations

import os
import subprocess  # nosec B404 - imported for CalledProcessError type inspection
from typing import Callable, Iterable, Mapping

from .configuration import config

__all__ = ["get_system_exit_code"]

Resolver = Callable[[BaseException], int | None]


def get_system_exit_code(exc: BaseException) -> int:
    """Why:
        Ensure all uncaught exceptions translate into deterministic exit codes.
    What:
        Iterate resolver strategies until one yields an integer status suitable
        for :func:`sys.exit`.
    Parameters:
        exc: Exception raised by application or adapter code.
    Returns:
        Integer exit code derived from OS conventions or configuration.
    Side Effects:
        None.
    """

    for resolver in _resolver_chain():
        code = resolver(exc)
        if code is not None:
            return code
    return 1


def _resolver_chain() -> Iterable[Resolver]:
    """Why:
        Encapsulate precedence so behaviour stays consistent across callers.
    What:
        Yield resolver callables ordered from most specific to most general.
    Parameters:
        None.
    Returns:
        Iterable of resolver callables.
    Side Effects:
        None.
    """

    return (
        _code_from_called_process_error,
        _code_from_keyboard_interrupt,
        _code_from_winerror_attribute,
        _code_from_broken_pipe,
        _code_from_errno,
        _code_from_system_exit,
        _code_from_sysexits_mode,
        _code_from_platform_mapping,
    )


def _code_from_called_process_error(exc: BaseException) -> int | None:
    """Why:
        Preserve exit statuses produced by failing subprocesses.
    What:
        Inspect ``exc`` for a numeric ``returncode`` attribute and propagate it.
    Parameters:
        exc: Exception raised by :mod:`subprocess` helpers.
    Returns:
        Numeric return code or ``None`` when the value is unusable.
    Side Effects:
        None.
    """
    if not isinstance(exc, subprocess.CalledProcessError):
        return None
    return _safe_int(getattr(exc, "returncode", None)) or 1


def _code_from_keyboard_interrupt(exc: BaseException) -> int | None:
    """Why:
        Align with shell conventions for Ctrl+C interrupts.
    What:
        Return ``130`` when ``exc`` is ``KeyboardInterrupt``.
    Parameters:
        exc: Exception object raised by Python.
    Returns:
        ``130`` or ``None`` when not applicable.
    Side Effects:
        None.
    """
    if isinstance(exc, KeyboardInterrupt):
        return 130
    return None


def _code_from_winerror_attribute(exc: BaseException) -> int | None:
    """Why:
        Windows APIs expose failure reasons via ``winerror`` rather than ``errno``.
    What:
        Parse ``exc.winerror`` into an integer when present.
    Parameters:
        exc: Exception potentially exposing a ``winerror`` attribute.
    Returns:
        Integer winerror or ``None`` when unavailable.
    Side Effects:
        None.
    """
    if not hasattr(exc, "winerror"):
        return None
    return _safe_int(getattr(exc, "winerror"))


def _code_from_broken_pipe(exc: BaseException) -> int | None:
    """Why:
        Honour the configurable exit code for truncated pipelines.
    What:
        Return :data:`config.broken_pipe_exit_code` when ``exc`` is a
        ``BrokenPipeError``.
    Parameters:
        exc: Exception under evaluation.
    Returns:
        Configured exit code or ``None`` when the exception is unrelated.
    Side Effects:
        None.
    """
    if isinstance(exc, BrokenPipeError):
        return int(config.broken_pipe_exit_code)
    return None


def _code_from_errno(exc: BaseException) -> int | None:
    """Why:
        Preserve errno semantics for standard filesystem and OS errors.
    What:
        Convert the ``errno`` attribute into an integer when present.
    Parameters:
        exc: Exception potentially carrying an ``errno`` attribute.
    Returns:
        Parsed integer errno or ``None`` when unavailable.
    Side Effects:
        None.
    """
    if not isinstance(exc, OSError):
        return None
    return _safe_int(getattr(exc, "errno", None))


def _code_from_system_exit(exc: BaseException) -> int | None:
    """Why:
        ``sys.exit`` payloads should be honoured when safe.
    What:
        Validate and return the embedded ``SystemExit.code`` value.
    Parameters:
        exc: Exception propagated by ``sys.exit``.
    Returns:
        Integer payload, ``0`` for ``None`` payloads, or ``1`` on failure.
    Side Effects:
        None.
    """
    if not isinstance(exc, SystemExit):
        return None

    code = getattr(exc, "code", None)
    if isinstance(code, int):
        return code
    if code is None:
        return 0
    candidate = _safe_int(str(code))
    return 1 if candidate is None else candidate


def _code_from_sysexits_mode(exc: BaseException) -> int | None:
    """Why:
        Honour the optional sysexits configuration for shell-centric workflows.
    What:
        Delegate to :func:`_sysexits_mapping` when sysexits mode is enabled.
    Parameters:
        exc: Exception under evaluation.
    Returns:
        Sysexits-derived integer or ``None`` when mode is disabled.
    Side Effects:
        None.
    """
    if config.exit_code_style != "sysexits":
        return None
    return _sysexits_mapping(exc)


def _code_from_platform_mapping(exc: BaseException) -> int | None:
    """Why:
        Provide sensible defaults for common exceptions when specific resolvers fail.
    What:
        Consult the platform table for an exit code matching ``exc``.
    Parameters:
        exc: Exception under evaluation.
    Returns:
        Integer exit code or ``None``.
    Side Effects:
        None.
    """
    for exc_type, code in _platform_exception_map().items():
        if isinstance(exc, exc_type):
            return code
    return None


def _platform_exception_map() -> Mapping[type[BaseException], int]:
    """Why:
        Different platforms use distinct numeric codes for the same errors.
    What:
        Return either the POSIX or Windows mapping dictionary based on
        :data:`os.name`.
    Parameters:
        None.
    Returns:
        Dictionary mapping exception types to integer exit codes.
    Side Effects:
        None.
    """
    if os.name == "posix":
        return _posix_exception_map()
    return _windows_exception_map()


def _posix_exception_map() -> Mapping[type[BaseException], int]:
    """Why:
        Keep POSIX-specific errno defaults centralised and documented.
    What:
        Provide a dictionary mapping high-level exceptions to POSIX exit codes.
    Parameters:
        None.
    Returns:
        Dictionary of exception types and exit codes.
    Side Effects:
        None.
    """
    return {
        FileNotFoundError: 2,
        PermissionError: 13,
        FileExistsError: 17,
        IsADirectoryError: 21,
        NotADirectoryError: 20,
        TimeoutError: 110,
        TypeError: 22,
        ValueError: 22,
        RuntimeError: 1,
    }


def _windows_exception_map() -> Mapping[type[BaseException], int]:
    """Why:
        Keep Windows-specific winerror defaults centralised and documented.
    What:
        Provide a dictionary mapping high-level exceptions to Windows exit codes.
    Parameters:
        None.
    Returns:
        Dictionary of exception types and exit codes.
    Side Effects:
        None.
    """
    return {
        FileNotFoundError: 2,
        PermissionError: 5,
        FileExistsError: 80,
        IsADirectoryError: 267,
        NotADirectoryError: 267,
        TimeoutError: 1460,
        TypeError: 87,
        ValueError: 87,
        RuntimeError: 1,
    }


def _safe_int(value: object | None) -> int | None:
    """Attempt to coerce ``value`` into an integer, returning ``None`` on failure.

    Why:
        ``errno`` and ``winerror`` fields may be ``None`` or non-numeric
        objects; this helper converts safely without raising.
    Parameters:
        value: Object expected to represent an integer.
    Returns:
        Parsed integer or ``None`` when conversion fails.
    Side Effects:
        None.
    """
    try:
        if value is None:
            return None
        return int(value)  # type: ignore[arg-type]
    except Exception:
        return None


def _sysexits_mapping(exc: BaseException) -> int:
    """Why:
        Provide shell-friendly exit codes when callers opt into sysexits mode.
    What:
        Map exceptions onto BSD ``sysexits`` constants.
    Parameters:
        exc: Exception raised by application logic.
    Returns:
        Integer drawn from the sysexits range (e.g. ``64`` for usage errors).
    Side Effects:
        None.
    """

    if isinstance(exc, SystemExit):
        try:
            return int(exc.code)  # type: ignore[attr-defined]
        except Exception:
            return 1
    if isinstance(exc, KeyboardInterrupt):
        return 130
    if isinstance(exc, subprocess.CalledProcessError):
        try:
            return int(exc.returncode)
        except Exception:
            return 1
    if isinstance(exc, BrokenPipeError):
        return int(config.broken_pipe_exit_code)
    if isinstance(exc, (TypeError, ValueError)):
        return 64
    if isinstance(exc, FileNotFoundError):
        return 66
    if isinstance(exc, PermissionError):
        return 77
    if isinstance(exc, (OSError, IOError)):
        return 74
    return 1
