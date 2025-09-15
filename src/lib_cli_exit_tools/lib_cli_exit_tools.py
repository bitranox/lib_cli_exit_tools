"""Core helpers for clean CLI exits and error printing.

Exposed API:
- config: runtime options (traceback toggle, exit code style, broken pipe behavior)
- get_system_exit_code(exc): map exceptions → OS-appropriate exit codes
- print_exception_message(...): print concise error, optional traceback, stdout/stderr if present
- flush_streams(): flush stdout/stderr safely
"""

from __future__ import annotations

import os
import subprocess
import sys
import traceback
from dataclasses import dataclass
from typing import Any, Literal, Optional, TextIO


@dataclass(slots=True)
class _Config:
    """Runtime configuration for library behavior."""

    traceback: bool = False
    # errno → numeric OS codes (default) | sysexits (64–78 semantics)
    exit_code_style: Literal["errno", "sysexits"] = "errno"
    # Exit code to use for BrokenPipeError (common in pipelines). Typical choices:
    # 141 (128+SIGPIPE), 0 (treat as benign truncation), or 32 (EPIPE).
    broken_pipe_exit_code: int = 141


config = _Config()


def get_system_exit_code(exc: BaseException) -> int:
    """
    Return the exit code for linux or Windows os, based on the exception.
    If, on windows, the winerror code is passed with the Exception, we return that winerror code.


    Parameter
    ---------
    exc
        the exception to analyze


    Result
    ------
    exit_code
        as integer


    Examples
    --------

    >>> try:
    ...     raise RuntimeError()
    ... except RuntimeError as my_exc:
    ...     get_system_exit_code(my_exc)
    1
    >>> try:
    ...     raise RuntimeError()
    ... except RuntimeError as my_exc:
    ...     setattr(my_exc, 'winerror', 42)
    ...     get_system_exit_code(my_exc)
    42
    >>> try:
    ...     raise RuntimeError()
    ... except RuntimeError as my_exc:
    ...     setattr(my_exc, 'winerror', None)
    ...     get_system_exit_code(my_exc)
    1
    >>> try:
    ...     exit(99)
    ... except SystemExit as my_exc:
    ...     get_system_exit_code(my_exc)
    99

    """

    # Prefer precise sources first: explicit returncodes, signals, winerror/errno
    # subprocess returncode
    if isinstance(exc, subprocess.CalledProcessError):
        try:
            return int(exc.returncode)
        except Exception:
            return 1

    # KeyboardInterrupt should map to 130 regardless of platform
    if isinstance(exc, KeyboardInterrupt):
        return 130

    # Windows-specific error code passthrough
    if hasattr(exc, "winerror"):
        try:
            return int(getattr(exc, "winerror"))  # type: ignore[arg-type]
        except (AttributeError, TypeError, ValueError):
            pass

    # Broken pipe (common when piping to head/less): don't be noisy
    if isinstance(exc, BrokenPipeError):
        return int(config.broken_pipe_exit_code)

    # If an errno is present (OSError family), prefer it
    if isinstance(exc, OSError) and getattr(exc, "errno", None) is not None:
        try:
            return int(exc.errno)  # type: ignore[arg-type]
        except Exception:
            pass

    # Fallback mappings (ordered from specific to general)
    # POSIX references: errno.h; Windows: common Win32/WSA equivalents when errno/winerror absent
    posix_exceptions = {
        FileNotFoundError: 2,  # ENOENT
        PermissionError: 13,  # EACCES
        FileExistsError: 17,  # EEXIST
        IsADirectoryError: 21,  # EISDIR
        NotADirectoryError: 20,  # ENOTDIR
        TimeoutError: 110,  # ETIMEDOUT
        TypeError: 22,  # EINVAL
        ValueError: 22,  # EINVAL
        RuntimeError: 1,
    }
    windows_exceptions = {
        FileNotFoundError: 2,  # ERROR_FILE_NOT_FOUND
        PermissionError: 5,  # ERROR_ACCESS_DENIED
        FileExistsError: 80,  # ERROR_FILE_EXISTS
        IsADirectoryError: 267,  # ERROR_DIRECTORY
        NotADirectoryError: 267,  # ERROR_DIRECTORY
        TimeoutError: 1460,  # ERROR_TIMEOUT
        TypeError: 87,  # ERROR_INVALID_PARAMETER
        ValueError: 87,  # map to invalid parameter
        RuntimeError: 1,
    }

    # Handle SystemExit robustly
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

    # At this point, if a sysexits mapping is requested, apply it
    if config.exit_code_style == "sysexits":
        return _sysexits_mapping(exc)

    if os.name == "posix":
        exceptions = posix_exceptions
    else:
        exceptions = windows_exceptions

    # Handle all other Exceptions
    for exception in exceptions:
        if isinstance(exc, exception):
            return exceptions[exception]

    # this should never happen
    return 1


def _sysexits_mapping(exc: BaseException) -> int:
    """Map common exceptions to sysexits(3) style codes.

    EX_USAGE(64), EX_NOINPUT(66), EX_NOPERM(77), EX_IOERR(74)
    Defaults to 1 if no good fit is found.
    """
    result: int
    if isinstance(exc, SystemExit):
        try:
            result = int(exc.code)  # type: ignore[attr-defined]
        except Exception:
            result = 1
    elif isinstance(exc, KeyboardInterrupt):
        result = 130
    elif isinstance(exc, subprocess.CalledProcessError):
        try:
            result = int(exc.returncode)
        except Exception:
            result = 1
    elif isinstance(exc, BrokenPipeError):
        # Broken pipe often considered benign; keep configured behavior
        result = int(config.broken_pipe_exit_code)
    elif isinstance(exc, (TypeError, ValueError)):
        result = 64  # EX_USAGE
    elif isinstance(exc, FileNotFoundError):
        result = 66  # EX_NOINPUT
    elif isinstance(exc, PermissionError):
        result = 77  # EX_NOPERM
    elif isinstance(exc, (OSError, IOError)):
        result = 74  # EX_IOERR
    else:
        result = 1
    return result


def print_exception_message(trace_back: bool = config.traceback, length_limit: int = 500, stream: Optional[TextIO] = None) -> None:
    """
    Prints the Exception Message to stderr. If trace_back is True, it also prints the traceback information.
    If the exception has stdout, stderr attributes (like subprocess.CalledProcessError), those will also be printed.

    Parameters
    ----------
    trace_back : bool, optional
        Whether to print traceback information. Default is False.
    length_limit : int, optional
        Maximum length of the exception message to be printed. Default is 500.
    stream : Optional[TextIO], optional
        The stream to print to. Default is sys.stderr.

    Examples
    --------

    >>> # test with exc_info = None
    >>> print_exception_message()

    >>> # test with exc_info
    >>> try:
    ...     raise FileNotFoundError('unknown_command_test1')
    ... except Exception:       # noqa
    ...     print_exception_message(True, length_limit=15, stream=sys.stdout)
    ...     print_exception_message(False, stream=sys.stdout)
    ...     print_exception_message(True, stream=sys.stdout)
    Traceback Info...

    >>> # test with subprocess to get stdout, stderr
    >>> import subprocess
    >>> try:
    ...     discard=subprocess.run('unknown_command_test2_this_should_fail', shell=True, check=True)
    ... except subprocess.CalledProcessError:
    ...     print_exception_message(False, stream=sys.stdout)
    ...     print_exception_message(True, stream=sys.stdout)
    ...     print_exception_message(True, stream=sys.stdout)
    CalledProcessError...

    """
    flush_streams()

    if stream is None:
        stream = sys.stderr

    exc_info = sys.exc_info()[1]  # Get the current exception
    if exc_info is not None:
        exc_info_type = type(exc_info).__name__
        exc_info_msg = f"{exc_info_type}: {str(exc_info)}"

        # Print traceback if trace_back is True
        if trace_back:
            exc_info_msg = f"Traceback Information:\n{traceback.format_exc()}"

        # If message exceeds length limit, truncate it
        if len(exc_info_msg) > length_limit:
            exc_info_msg = f"{exc_info_msg[:length_limit]} ...[TRUNCATED at {length_limit} characters]"

        # Print stdout/stderr if they exist in the exception
        _print_output(exc_info, "stdout", stream)
        _print_output(exc_info, "stderr", stream)

        # Print the exception message
        print(exc_info_msg, file=stream)
        flush_streams()


def _print_output(exc_info: Any, attr: str, stream: Optional[TextIO] = None) -> None:
    """
    Helper function to print an attribute (stdout, stderr) of the exc_info if it exists.

    Parameters
    ----------
    exc_info : Any
        The exception object that may contain stdout or stderr.
    attr : str
        The attribute name ('stdout' or 'stderr').
    stream : Optional[TextIO]
        The stream to print to. Default is sys.stderr.

    >>> class ExcInfo(object):
    ...    pass

    >>> my_exc_info = ExcInfo()

    >>> # test no stdout attribute
    >>> _print_output(my_exc_info, 'stdout')

    >>> # test stdout=None
    >>> my_exc_info.stdout=None
    >>> _print_output(my_exc_info, 'stdout')

    >>> # test stdout
    >>> my_exc_info.stdout=b'test'
    >>> _print_output(my_exc_info, 'stdout', stream=sys.stdout)
    STDOUT: test

    >>> my_exc_info = ExcInfo()

    >>> # test no stderr attribute
    >>> _print_output(my_exc_info, 'stderr')

    >>> # test stderr=None
    >>> my_exc_info.stderr=None
    >>> _print_output(my_exc_info, 'stderr')

    >>> # test stderr
    >>> my_exc_info.stderr=b'test'
    >>> _print_output(my_exc_info, 'stderr', stream=sys.stdout)
    STDERR: test

    """
    if stream is None:
        stream = sys.stderr

    if hasattr(exc_info, attr):
        output = getattr(exc_info, attr)
        if output is None:
            return
        text: Optional[str] = None
        if isinstance(output, bytes):
            try:
                text = output.decode("utf-8", errors="replace")
            except Exception:
                text = None
        elif isinstance(output, str):
            text = output
        if text is not None:
            print(f"{attr.upper()}: {text}", file=stream)


def flush_streams() -> None:
    """
    flush the streams - make sure the output is written early,
    otherwise the output might be printed even after another CLI
    command is launched


    Examples
    --------


    >>> flush_streams()

    """
    try:
        sys.stdout.flush()
    except Exception:
        pass
    try:
        sys.stderr.flush()
    except Exception:
        pass
