from __future__ import annotations

import io
import subprocess

import pytest

from lib_cli_exit_tools.lib_cli_exit_tools import (
    get_system_exit_code,
    print_exception_message,
)


def test_value_error_windows_mapping(monkeypatch: pytest.MonkeyPatch) -> None:
    # Force windows mapping by monkeypatching os.name used in module
    import lib_cli_exit_tools.lib_cli_exit_tools as tools

    monkeypatch.setattr(tools.os, "name", "nt", raising=False)
    assert get_system_exit_code(ValueError("x")) == 87


def test_get_system_exit_code_cpe_bad_returncode() -> None:
    e = subprocess.CalledProcessError(returncode="x", cmd=["echo"])  # type: ignore[arg-type]
    assert get_system_exit_code(e) == 1


def test_get_system_exit_code_winerror_bad_type() -> None:
    class E(Exception):
        pass

    e = E("boom")
    setattr(e, "winerror", "bad")  # type: ignore[attr-defined]
    # falls through to fallback mapping → RuntimeError not matched → 1
    assert get_system_exit_code(e) == 1


def test_get_system_exit_code_errno_bad_type() -> None:
    class E(OSError):
        pass

    e = E("oops")
    setattr(e, "errno", "bad")  # type: ignore[attr-defined]
    # conversion fails, falls through to fallback mapping → 1
    assert get_system_exit_code(e) == 1


def test_print_exception_message_traceback_and_truncate() -> None:
    # Trigger traceback formatting
    buf = io.StringIO()
    try:
        raise ValueError("x" * 200)
    except Exception:
        print_exception_message(True, length_limit=40, stream=buf)
    out = buf.getvalue()
    assert "Traceback Information:" in out

    # Trigger truncation branch (traceback False) with tight limit
    buf = io.StringIO()
    try:
        raise RuntimeError("y" * 200)
    except Exception:
        print_exception_message(False, length_limit=10, stream=buf)
    out = buf.getvalue()
    assert "[TRUNCATED" in out


def test_print_output_defaults_to_stderr_and_bytes(capsys: pytest.CaptureFixture[str]) -> None:
    from lib_cli_exit_tools import lib_cli_exit_tools as mod

    class E:  # simple exception-like object with stdout
        stdout = b"hello"

    # call private helper via getattr to avoid static checker complaints
    getattr(mod, "_print_output")(E(), "stdout")  # pyright: ignore[reportPrivateUsage]
    _, err = capsys.readouterr()
    assert "STDOUT: hello" in err
