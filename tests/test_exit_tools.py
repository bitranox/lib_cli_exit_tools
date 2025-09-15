from __future__ import annotations

import io
import subprocess
import sys

import pytest

from lib_cli_exit_tools.lib_cli_exit_tools import (
    flush_streams,
    get_system_exit_code,
    print_exception_message,
    config,
)


def test_get_system_exit_code_system_exit():
    try:
        raise SystemExit(99)
    except SystemExit as e:
        assert get_system_exit_code(e) == 99


def test_get_system_exit_code_system_exit_variants():
    # None -> 0
    try:
        raise SystemExit(None)
    except SystemExit as e:
        assert get_system_exit_code(e) == 0
    # numeric in string -> parsed
    try:
        raise SystemExit("2")
    except SystemExit as e:
        assert get_system_exit_code(e) == 2
    # invalid string -> fallback 1
    try:
        raise SystemExit("oops")
    except SystemExit as e:
        assert get_system_exit_code(e) == 1


@pytest.mark.skipif(sys.platform.startswith("win"), reason="POSIX-specific expectations; skip on Windows")
def test_get_system_exit_code_common_posix():
    try:
        raise FileNotFoundError("x")
    except FileNotFoundError as e:
        assert get_system_exit_code(e) == 2
    try:
        raise ValueError("bad")
    except ValueError as e:
        assert get_system_exit_code(e) == 22


def test_get_system_exit_code_winerror_attr_takes_precedence():
    class MyErr(RuntimeError):
        pass

    e = MyErr("boom")
    setattr(e, "winerror", 42)
    assert get_system_exit_code(e) == 42


def test_get_system_exit_code_keyboard_interrupt_maps_130():
    try:
        raise KeyboardInterrupt()
    except KeyboardInterrupt as e:
        assert get_system_exit_code(e) == 130


def test_get_system_exit_code_called_process_error():
    e = subprocess.CalledProcessError(returncode=7, cmd=["echo", "x"])  # type: ignore[call-arg]
    assert get_system_exit_code(e) == 7


def test_get_system_exit_code_errno_from_oserror():
    try:
        raise NotADirectoryError(20, "not a dir")
    except NotADirectoryError as e:
        assert e.errno is not None
        assert get_system_exit_code(e) == e.errno


def test_get_system_exit_code_broken_pipe_uses_configured_code():
    old = config.broken_pipe_exit_code
    try:
        config.broken_pipe_exit_code = 141
        assert get_system_exit_code(BrokenPipeError()) == 141
        config.broken_pipe_exit_code = 0
        assert get_system_exit_code(BrokenPipeError()) == 0
    finally:
        config.broken_pipe_exit_code = old


def test_sysexits_mode_value_error_and_permissions():
    old_style = config.exit_code_style
    try:
        config.exit_code_style = "sysexits"
        assert get_system_exit_code(ValueError("x")) == 64  # EX_USAGE
        assert get_system_exit_code(PermissionError("x")) == 77  # EX_NOPERM
    finally:
        config.exit_code_style = old_style


def test_print_exception_message_basic():
    # No active exception → should be a no-op
    print_exception_message()

    # With an active exception
    try:
        raise FileNotFoundError("missing.txt")
    except Exception:
        buf = io.StringIO()
        print_exception_message(trace_back=False, stream=buf)
        out = buf.getvalue()
        assert "FileNotFoundError" in out
        assert "missing.txt" in out


def test_print_exception_message_called_process_error_like():
    # Simulate a CalledProcessError with stdout/stderr
    class CpeLike(Exception):
        def __init__(self) -> None:
            self.stdout = b"out"
            self.stderr = b"err"

    try:
        raise CpeLike()
    except Exception:
        buf = io.StringIO()
        print_exception_message(trace_back=False, stream=buf)
        out = buf.getvalue()
        assert "STDOUT: out" in out
        assert "STDERR: err" in out


def test_print_exception_message_string_output():
    class E(Exception):
        stdout = "hello"
        stderr = "world"

    try:
        raise E()
    except Exception:
        buf = io.StringIO()
        print_exception_message(trace_back=False, stream=buf)
        out = buf.getvalue()
        assert "STDOUT: hello" in out
        assert "STDERR: world" in out


def test_print_exception_message_ignores_non_text_output():
    class E(Exception):
        stdout = 123  # type: ignore[assignment]
        stderr = None

    try:
        raise E()
    except Exception:
        buf = io.StringIO()
        print_exception_message(trace_back=False, stream=buf)
        out = buf.getvalue()
        assert "STDOUT:" not in out


def test_flush_streams():
    # Just ensure it doesn't raise
    flush_streams()
