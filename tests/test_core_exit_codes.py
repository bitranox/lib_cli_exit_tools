"""Tests for exit code translation.

Each test verifies exactly one exit code mapping behavior:
- CalledProcessError returns subprocess exit codes
- KeyboardInterrupt maps to 130
- BrokenPipeError respects configuration
- SystemExit preserves payloads
- Platform-specific mappings for POSIX and Windows
- Sysexits mode mappings
"""

from __future__ import annotations

import subprocess

import pytest
from hypothesis import given, strategies as st

from lib_cli_exit_tools.core import configuration as cfg
from lib_cli_exit_tools.core import exit_codes as codes


# =============================================================================
# CalledProcessError Exit Codes
# =============================================================================


@pytest.mark.os_agnostic
def test_called_process_error_returns_subprocess_exit_code() -> None:
    error = subprocess.CalledProcessError(returncode=7, cmd=["echo"])
    assert codes.get_system_exit_code(error) == 7


@pytest.mark.os_agnostic
def test_called_process_error_with_zero_returns_one() -> None:
    # Note: Due to `or 1` fallback, zero returncode is treated as falsy and returns 1
    error = subprocess.CalledProcessError(returncode=0, cmd=["true"])
    assert codes.get_system_exit_code(error) == 1


@pytest.mark.os_agnostic
def test_called_process_error_with_negative_code_returns_negative() -> None:
    error = subprocess.CalledProcessError(returncode=-9, cmd=["killed"])
    assert codes.get_system_exit_code(error) == -9


# =============================================================================
# KeyboardInterrupt Exit Code
# =============================================================================


@pytest.mark.os_agnostic
def test_keyboard_interrupt_returns_130() -> None:
    assert codes.get_system_exit_code(KeyboardInterrupt()) == 130


# =============================================================================
# Windows Error Attribute
# =============================================================================


@pytest.mark.os_agnostic
def test_winerror_attribute_becomes_exit_code() -> None:
    class WindowsStyleError(Exception):
        def __init__(self, winerror: int) -> None:
            super().__init__()
            self.winerror = winerror

    error = WindowsStyleError(winerror=120)
    assert codes.get_system_exit_code(error) == 120


# =============================================================================
# BrokenPipeError Exit Code
# =============================================================================


@pytest.mark.os_agnostic
def test_broken_pipe_returns_configured_exit_code(reset_config: None) -> None:
    cfg.config.broken_pipe_exit_code = 42
    assert codes.get_system_exit_code(BrokenPipeError()) == 42


@pytest.mark.os_agnostic
def test_broken_pipe_default_is_141(reset_config: None) -> None:
    assert codes.get_system_exit_code(BrokenPipeError()) == 141


# =============================================================================
# OSError with errno
# =============================================================================


@pytest.mark.os_agnostic
def test_oserror_with_errno_returns_errno() -> None:
    error = FileNotFoundError()
    error.errno = 2  # type: ignore[attr-defined]
    assert codes.get_system_exit_code(error) == 2


# =============================================================================
# SystemExit Payloads
# =============================================================================


@pytest.mark.os_agnostic
def test_system_exit_with_integer_returns_that_integer() -> None:
    assert codes.get_system_exit_code(SystemExit(5)) == 5


@pytest.mark.os_agnostic
def test_system_exit_with_none_returns_zero() -> None:
    exit_request = SystemExit()
    exit_request.code = None  # type: ignore[attr-defined]
    assert codes.get_system_exit_code(exit_request) == 0


@pytest.mark.os_agnostic
def test_system_exit_with_numeric_string_coerces_to_integer() -> None:
    assert codes.get_system_exit_code(SystemExit("9")) == 9


@pytest.mark.os_agnostic
def test_system_exit_with_non_numeric_string_returns_one() -> None:
    exit_request = SystemExit()
    exit_request.code = "not-a-number"  # type: ignore[attr-defined]
    assert codes.get_system_exit_code(exit_request) == 1


@pytest.mark.os_agnostic
def test_system_exit_with_unconvertible_object_returns_one() -> None:
    exit_request = SystemExit()
    exit_request.code = object()  # type: ignore[attr-defined]
    assert codes.get_system_exit_code(exit_request) == 1


# =============================================================================
# Default Fallback
# =============================================================================


@pytest.mark.os_agnostic
def test_unknown_exception_returns_one() -> None:
    assert codes.get_system_exit_code(RuntimeError("opaque failure")) == 1


@pytest.mark.os_agnostic
def test_first_resolved_code_returns_none_for_unknown_exceptions() -> None:
    class UnknownError(Exception):
        pass

    assert codes._first_resolved_code(UnknownError()) is None  # pyright: ignore[reportPrivateUsage]


# =============================================================================
# Platform-Specific Mappings (POSIX)
# =============================================================================


@pytest.mark.posix_only
def test_posix_value_error_maps_to_22() -> None:
    assert codes.get_system_exit_code(ValueError("bad value")) == 22


@pytest.mark.posix_only
def test_posix_type_error_maps_to_22() -> None:
    assert codes.get_system_exit_code(TypeError("wrong type")) == 22


@pytest.mark.posix_only
def test_posix_file_not_found_maps_to_2() -> None:
    error = FileNotFoundError()
    error.errno = None  # type: ignore[attr-defined]  # force platform map
    assert codes.get_system_exit_code(error) == 2


@pytest.mark.posix_only
def test_posix_permission_error_maps_to_13() -> None:
    error = PermissionError()
    error.errno = None  # type: ignore[attr-defined]  # force platform map
    assert codes.get_system_exit_code(error) == 13


# =============================================================================
# Platform-Specific Mappings (Windows)
# =============================================================================


@pytest.mark.windows_only
def test_windows_permission_error_maps_to_5(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(codes, "_is_posix_platform", lambda: False)
    error = PermissionError()
    error.errno = None  # type: ignore[attr-defined]  # force platform map
    assert codes.get_system_exit_code(error) == 5


@pytest.mark.windows_only
def test_windows_file_exists_maps_to_80(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(codes, "_is_posix_platform", lambda: False)
    error = FileExistsError()
    error.errno = None  # type: ignore[attr-defined]  # force platform map
    assert codes.get_system_exit_code(error) == 80


# =============================================================================
# Sysexits Mode
# =============================================================================


@pytest.mark.os_agnostic
def test_sysexits_mode_disabled_skips_sysexits_resolver(reset_config: None) -> None:
    assert codes._code_from_sysexits_mode(ValueError("ignored")) is None  # pyright: ignore[reportPrivateUsage]


@pytest.mark.os_agnostic
def test_sysexits_type_error_maps_to_64(sysexits_mode: None) -> None:
    assert codes.get_system_exit_code(TypeError("bad args")) == 64


@pytest.mark.os_agnostic
def test_sysexits_value_error_maps_to_64(sysexits_mode: None) -> None:
    assert codes.get_system_exit_code(ValueError("bad value")) == 64


@pytest.mark.os_agnostic
def test_sysexits_permission_error_maps_to_77(sysexits_mode: None) -> None:
    assert codes.get_system_exit_code(PermissionError("stop")) == 77


@pytest.mark.os_agnostic
def test_sysexits_file_not_found_maps_to_66(sysexits_mode: None) -> None:
    assert codes.get_system_exit_code(FileNotFoundError("missing")) == 66


@pytest.mark.os_agnostic
def test_sysexits_oserror_maps_to_74(sysexits_mode: None) -> None:
    assert codes.get_system_exit_code(OSError("io")) == 74


@pytest.mark.os_agnostic
def test_sysexits_broken_pipe_respects_config(sysexits_mode: None) -> None:
    cfg.config.broken_pipe_exit_code = 12
    assert codes.get_system_exit_code(BrokenPipeError()) == 12


@pytest.mark.os_agnostic
def test_sysexits_keyboard_interrupt_returns_130(sysexits_mode: None) -> None:
    result = codes._sysexits_from_keyboard_interrupt(KeyboardInterrupt())  # pyright: ignore[reportPrivateUsage]
    assert result == 130


@pytest.mark.os_agnostic
def test_sysexits_system_exit_with_unconvertible_returns_one(sysexits_mode: None) -> None:
    exit_request = SystemExit()
    exit_request.code = object()  # type: ignore[attr-defined]
    result = codes._sysexits_from_system_exit(exit_request)  # pyright: ignore[reportPrivateUsage]
    assert result == 1


@pytest.mark.os_agnostic
def test_sysexits_called_process_error_with_invalid_returncode_returns_one(sysexits_mode: None) -> None:
    err = subprocess.CalledProcessError(returncode="bad", cmd=["cmd"])  # type: ignore[arg-type]
    result = codes._sysexits_from_called_process_error(err)  # pyright: ignore[reportPrivateUsage]
    assert result == 1


@pytest.mark.os_agnostic
def test_sysexits_unknown_exception_returns_one(sysexits_mode: None) -> None:
    class NovelError(Exception):
        pass

    result = codes._sysexits_resolved_code(NovelError("none"))  # pyright: ignore[reportPrivateUsage]
    assert result == 1


@pytest.mark.os_agnostic
def test_sysexits_default_resolver_returns_one() -> None:
    assert codes._sysexits_default(RuntimeError("")) == 1  # pyright: ignore[reportPrivateUsage]


@pytest.mark.os_agnostic
def test_sysexits_broken_pipe_resolver_reflects_config(reset_config: None) -> None:
    cfg.config.broken_pipe_exit_code = 55
    result = codes._sysexits_from_broken_pipe(BrokenPipeError())  # pyright: ignore[reportPrivateUsage]
    assert result == 55


@pytest.mark.os_agnostic
def test_sysexits_fallback_when_default_returns_none(monkeypatch: pytest.MonkeyPatch, sysexits_mode: None) -> None:
    def default_none(_: BaseException) -> None:
        return None

    monkeypatch.setattr(codes, "_sysexits_default", default_none)
    result = codes._sysexits_resolved_code(Exception("fallback"))  # pyright: ignore[reportPrivateUsage]
    assert result == 1


# =============================================================================
# Safe Int Helper
# =============================================================================


@pytest.mark.os_agnostic
def test_safe_int_with_unconvertible_returns_none() -> None:
    assert codes._safe_int("not-int") is None  # pyright: ignore[reportPrivateUsage]


@pytest.mark.os_agnostic
def test_safe_int_with_none_returns_none() -> None:
    assert codes._safe_int(None) is None  # pyright: ignore[reportPrivateUsage]


@pytest.mark.os_agnostic
def test_safe_int_with_integer_returns_same_integer() -> None:
    assert codes._safe_int(42) == 42  # pyright: ignore[reportPrivateUsage]


# =============================================================================
# Property-Based Tests
# =============================================================================


@given(st.integers(min_value=-10_000, max_value=10_000))
def test_system_exit_payload_round_trips(payload: int) -> None:
    assert codes.get_system_exit_code(SystemExit(payload)) == payload


@given(st.integers(min_value=-10_000, max_value=10_000))
def test_sysexits_preserves_system_exit_payload(payload: int) -> None:
    cfg.config.exit_code_style = "sysexits"
    try:
        assert codes.get_system_exit_code(SystemExit(payload)) == payload
    finally:
        cfg.reset_config()


@given(st.integers(min_value=-10_000, max_value=10_000))
def test_broken_pipe_respects_any_configured_code(exit_code: int) -> None:
    cfg.config.broken_pipe_exit_code = exit_code
    try:
        assert codes.get_system_exit_code(BrokenPipeError()) == exit_code
    finally:
        cfg.reset_config()


@given(
    st.one_of(
        st.none(),
        st.integers(),
        st.text(),
        st.binary(),
        st.booleans(),
        st.floats(allow_nan=False, allow_infinity=False),
    )
)
def test_safe_int_never_raises(value: object | None) -> None:
    result = codes._safe_int(value)  # pyright: ignore[reportPrivateUsage]
    assert result is None or isinstance(result, int)
