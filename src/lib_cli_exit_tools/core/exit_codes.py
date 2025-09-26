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
import subprocess
from typing import Any

from .configuration import config

__all__ = ["get_system_exit_code"]


def get_system_exit_code(exc: BaseException) -> int:
    """Map an exception to an OS-appropriate exit status.

    Why:
        Provide a predictable fallback when Click or signal-specific handlers do
        not supply an explicit exit code.
    Parameters:
        exc: Exception raised by application logic.
    Returns:
        Integer exit code honouring Windows ``winerror`` values, POSIX ``errno``
        codes, or BSD ``sysexits`` depending on :data:`config`.
        (POSIX maps ``ValueError`` to 22, while Windows maps it to 87.)
    Side Effects:
        None.
    Examples:
        >>> get_system_exit_code(ValueError("bad input")) in {22, 87}
        True
    """

    if isinstance(exc, subprocess.CalledProcessError):
        try:
            return int(exc.returncode)
        except Exception:
            return 1

    if isinstance(exc, KeyboardInterrupt):
        return 130

    if hasattr(exc, "winerror"):
        try:
            return int(getattr(exc, "winerror"))  # type: ignore[arg-type]
        except (AttributeError, TypeError, ValueError):
            pass

    if isinstance(exc, BrokenPipeError):
        return int(config.broken_pipe_exit_code)

    if isinstance(exc, OSError) and getattr(exc, "errno", None) is not None:
        try:
            return int(exc.errno)  # type: ignore[arg-type]
        except Exception:
            pass

    posix_exceptions = {
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
    windows_exceptions = {
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

    if isinstance(exc, SystemExit):
        code = getattr(exc, "code", None)
        if isinstance(code, int):
            return code
        if code is None:
            return 0
        try:
            return int(str(code))
        except Exception:
            return 1

    if config.exit_code_style == "sysexits":
        return _sysexits_mapping(exc)

    exceptions = posix_exceptions if os.name == "posix" else windows_exceptions
    for exception, code in exceptions.items():
        if isinstance(exc, exception):
            return code

    return 1


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
