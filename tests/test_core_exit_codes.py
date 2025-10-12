from __future__ import annotations

import subprocess
from types import SimpleNamespace

import pytest
from hypothesis import given, strategies as st

from lib_cli_exit_tools.core import configuration as cfg
from lib_cli_exit_tools.core import exit_codes as codes


@pytest.mark.os_agnostic
def test_when_called_process_error_occurs_the_return_code_is_preserved() -> None:
    error = subprocess.CalledProcessError(returncode=7, cmd=["echo"])
    assert codes.get_system_exit_code(error) == 7


@pytest.mark.os_agnostic
def test_when_keyboard_interrupt_occurs_exit_code_is_130() -> None:
    assert codes.get_system_exit_code(KeyboardInterrupt()) == 130


@pytest.mark.os_agnostic
def test_when_exception_contains_winerror_the_value_is_used() -> None:
    class WindowsStyleError(Exception):
        def __init__(self, winerror: int) -> None:
            super().__init__()
            self.winerror = winerror

    error = WindowsStyleError(120)
    assert codes.get_system_exit_code(error) == 120


@pytest.mark.os_agnostic
def test_when_broken_pipe_occurs_configured_exit_code_is_returned() -> None:
    cfg.config.broken_pipe_exit_code = 42
    try:
        assert codes.get_system_exit_code(BrokenPipeError()) == 42
    finally:
        cfg.reset_config()


@pytest.mark.os_agnostic
def test_when_oserror_has_errno_it_is_returned() -> None:
    error = FileNotFoundError()
    error.errno = 2  # type: ignore[attr-defined]
    assert codes.get_system_exit_code(error) == 2


@pytest.mark.os_agnostic
def test_when_system_exit_has_string_payload_the_string_is_coerced() -> None:
    exit_request = SystemExit("9")
    assert codes.get_system_exit_code(exit_request) == 9


@pytest.mark.os_agnostic
def test_when_system_exit_has_none_payload_zero_is_returned() -> None:
    exit_request = SystemExit()
    exit_request.code = None  # type: ignore[attr-defined]
    assert codes.get_system_exit_code(exit_request) == 0


@pytest.mark.os_agnostic
def test_when_sysexits_mode_is_enabled_type_error_maps_to_usage() -> None:
    cfg.config.exit_code_style = "sysexits"
    try:
        assert codes.get_system_exit_code(TypeError("bad args")) == 64
    finally:
        cfg.reset_config()


@pytest.mark.os_agnostic
def test_when_sysexits_mode_sees_broken_pipe_it_respects_configured_code() -> None:
    cfg.config.exit_code_style = "sysexits"
    cfg.config.broken_pipe_exit_code = 12
    try:
        assert codes.get_system_exit_code(BrokenPipeError()) == 12
    finally:
        cfg.reset_config()


@pytest.mark.posix_only
def test_when_platform_map_handles_posix_value_error_the_errno_is_22(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(codes, "os", SimpleNamespace(name="posix"))
    assert codes.get_system_exit_code(ValueError("bad value")) == 22


@pytest.mark.windows_only
def test_when_platform_map_handles_windows_permission_error_the_code_is_5(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(codes, "os", SimpleNamespace(name="nt"))
    assert codes.get_system_exit_code(PermissionError("no permission")) == 5


@pytest.mark.os_agnostic
def test_when_no_resolver_matches_default_exit_code_is_one() -> None:
    assert codes.get_system_exit_code(RuntimeError("opaque failure")) == 1


@pytest.mark.os_agnostic
def test_when_first_resolved_code_find_nothing_it_returns_none() -> None:
    class UnknownError(Exception):
        pass

    assert codes._first_resolved_code(UnknownError()) is None  # pyright: ignore[reportPrivateUsage]


@pytest.mark.os_agnostic
def test_when_system_exit_has_uncoercible_payload_one_is_returned() -> None:
    exit_request = SystemExit()
    exit_request.code = "not-a-number"  # type: ignore[attr-defined]
    assert codes.get_system_exit_code(exit_request) == 1


@pytest.mark.os_agnostic
def test_when_system_exit_has_int_payload_the_exit_code_is_preserved() -> None:
    exit_request = SystemExit(5)
    assert codes.get_system_exit_code(exit_request) == 5


@pytest.mark.os_agnostic
def test_when_sysexits_mode_disabled_returns_none() -> None:
    cfg.reset_config()
    assert codes._code_from_sysexits_mode(ValueError("ignored")) is None  # pyright: ignore[reportPrivateUsage]


@pytest.mark.os_agnostic
def test_when_sysexits_system_exit_cannot_convert_it_returns_one() -> None:
    cfg.config.exit_code_style = "sysexits"
    try:
        exit_request = SystemExit()
        exit_request.code = object()  # type: ignore[attr-defined]
        assert codes._sysexits_from_system_exit(exit_request) == 1  # pyright: ignore[reportPrivateUsage]
    finally:
        cfg.reset_config()


@pytest.mark.os_agnostic
def test_when_sysexits_called_process_error_has_invalid_returncode_it_falls_back_to_one() -> None:
    cfg.config.exit_code_style = "sysexits"
    try:
        err = subprocess.CalledProcessError(returncode="bad", cmd=["cmd"])  # type: ignore[arg-type]
        assert codes._sysexits_from_called_process_error(err) == 1  # pyright: ignore[reportPrivateUsage]
    finally:
        cfg.reset_config()


@pytest.mark.os_agnostic
def test_when_sysexits_permission_error_maps_to_noperm() -> None:
    cfg.config.exit_code_style = "sysexits"
    try:
        assert codes.get_system_exit_code(PermissionError("stop")) == 77
    finally:
        cfg.reset_config()


@pytest.mark.os_agnostic
def test_when_sysexits_missing_resource_maps_to_noinput() -> None:
    cfg.config.exit_code_style = "sysexits"
    try:
        assert codes.get_system_exit_code(FileNotFoundError("missing")) == 66
    finally:
        cfg.reset_config()


@pytest.mark.os_agnostic
def test_when_sysexits_io_error_maps_to_ioerr() -> None:
    cfg.config.exit_code_style = "sysexits"
    try:
        assert codes.get_system_exit_code(OSError("io")) == 74
    finally:
        cfg.reset_config()


@pytest.mark.os_agnostic
def test_when_sysexits_keyboard_interrupt_maps_to_130() -> None:
    cfg.config.exit_code_style = "sysexits"
    try:
        assert codes._sysexits_from_keyboard_interrupt(KeyboardInterrupt()) == 130  # pyright: ignore[reportPrivateUsage]
    finally:
        cfg.reset_config()


@pytest.mark.os_agnostic
def test_when_sysexits_resolvers_have_no_match_default_one_returns() -> None:
    cfg.config.exit_code_style = "sysexits"
    try:

        class NovelError(Exception):
            pass

        assert codes._sysexits_resolved_code(NovelError("none")) == 1  # pyright: ignore[reportPrivateUsage]
    finally:
        cfg.reset_config()


@pytest.mark.os_agnostic
def test_when_sysexits_default_resolver_returns_one() -> None:
    assert codes._sysexits_default(RuntimeError("")) == 1  # pyright: ignore[reportPrivateUsage]


@given(st.integers(min_value=-10_000, max_value=10_000))
def test_system_exit_payload_round_trips_through_exit_code(payload: int) -> None:
    assert codes.get_system_exit_code(SystemExit(payload)) == payload


@given(st.integers(min_value=-10_000, max_value=10_000))
def test_sysexits_mode_preserves_system_exit_payload(payload: int) -> None:
    cfg.config.exit_code_style = "sysexits"
    try:
        assert codes.get_system_exit_code(SystemExit(payload)) == payload
    finally:
        cfg.reset_config()


@given(st.integers(min_value=-10_000, max_value=10_000))
def test_configured_broken_pipe_exit_code_matches_setting(exit_code: int) -> None:
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
def test_safe_int_never_raises_and_returns_int_or_none(value: object | None) -> None:
    result = codes._safe_int(value)  # pyright: ignore[reportPrivateUsage]
    assert result is None or isinstance(result, int)


@pytest.mark.os_agnostic
def test_when_sysexits_broken_pipe_resolver_reflects_configured_code() -> None:
    cfg.config.broken_pipe_exit_code = 55
    try:
        assert codes._sysexits_from_broken_pipe(BrokenPipeError()) == 55  # pyright: ignore[reportPrivateUsage]
    finally:
        cfg.reset_config()


@pytest.mark.os_agnostic
def test_when_sysexits_default_returns_none_the_resolved_code_falls_back(monkeypatch: pytest.MonkeyPatch) -> None:
    cfg.config.exit_code_style = "sysexits"
    try:

        def default_none(_: BaseException) -> None:
            return None

        monkeypatch.setattr(codes, "_sysexits_default", default_none)  # pyright: ignore[reportPrivateUsage]
        assert codes._sysexits_resolved_code(Exception("fallback")) == 1  # pyright: ignore[reportPrivateUsage]
    finally:
        cfg.reset_config()


@pytest.mark.os_agnostic
def test_when_safe_int_cannot_convert_it_returns_none() -> None:
    assert codes._safe_int("not-int") is None  # pyright: ignore[reportPrivateUsage]
