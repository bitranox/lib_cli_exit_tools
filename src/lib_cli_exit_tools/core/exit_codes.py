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
    """Map an exception to an OS-appropriate exit status."""

    for resolver in _resolver_chain():
        code = resolver(exc)
        if code is not None:
            return code
    return 1


def _resolver_chain() -> Iterable[Resolver]:
    """Return resolvers in the order we honour them."""

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
    if not isinstance(exc, subprocess.CalledProcessError):
        return None
    return _safe_int(getattr(exc, "returncode", None)) or 1


def _code_from_keyboard_interrupt(exc: BaseException) -> int | None:
    if isinstance(exc, KeyboardInterrupt):
        return 130
    return None


def _code_from_winerror_attribute(exc: BaseException) -> int | None:
    if not hasattr(exc, "winerror"):
        return None
    return _safe_int(getattr(exc, "winerror"))


def _code_from_broken_pipe(exc: BaseException) -> int | None:
    if isinstance(exc, BrokenPipeError):
        return int(config.broken_pipe_exit_code)
    return None


def _code_from_errno(exc: BaseException) -> int | None:
    if not isinstance(exc, OSError):
        return None
    return _safe_int(getattr(exc, "errno", None))


def _code_from_system_exit(exc: BaseException) -> int | None:
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
    if config.exit_code_style != "sysexits":
        return None
    return _sysexits_mapping(exc)


def _code_from_platform_mapping(exc: BaseException) -> int | None:
    for exc_type, code in _platform_exception_map().items():
        if isinstance(exc, exc_type):
            return code
    return None


def _platform_exception_map() -> Mapping[type[BaseException], int]:
    if os.name == "posix":
        return _posix_exception_map()
    return _windows_exception_map()


def _posix_exception_map() -> Mapping[type[BaseException], int]:
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
    try:
        if value is None:
            return None
        return int(value)  # type: ignore[arg-type]
    except Exception:
        return None


def _sysexits_mapping(exc: BaseException) -> int:
    """Translate an exception into BSD ``sysexits`` semantics.

    Why:
        Provide shell-friendly exit codes when callers opt into sysexits mode
        via :data:`config.exit_code_style`.
    Parameters:
        exc: Exception raised by application logic.
    Returns:
        Integer drawn from the sysexits range (e.g. 64 for usage errors).
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
