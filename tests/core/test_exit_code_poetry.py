"""The exit-code mapper speaks plainly in these tests."""

from __future__ import annotations

import subprocess
import sys

import pytest
from hypothesis import given, strategies as st

import lib_cli_exit_tools.core.exit_codes as exit_mod
from lib_cli_exit_tools.core.configuration import config_overrides
from lib_cli_exit_tools.core.exit_codes import get_system_exit_code

_sysexits = getattr(exit_mod, "_sysexits_mapping")


pytestmark = [
    pytest.mark.usefixtures("reset_config_state"),
    pytest.mark.os_agnostic,
]


def test_when_system_exit_carries_a_number_it_returns_that_number() -> None:
    assert get_system_exit_code(SystemExit(7)) == 7


def test_when_system_exit_carries_none_success_is_returned() -> None:
    assert get_system_exit_code(SystemExit(None)) == 0


def test_when_system_exit_carries_a_numeric_string_it_is_int_cast() -> None:
    assert get_system_exit_code(SystemExit("9")) == 9


def test_when_system_exit_carries_unparseable_text_it_becomes_failure() -> None:
    assert get_system_exit_code(SystemExit("boom")) == 1


def test_when_keyboard_interrupt_arrives_the_shell_convention_is_kept() -> None:
    assert get_system_exit_code(KeyboardInterrupt()) == 130


def test_when_called_process_error_has_integer_return_it_is_used() -> None:
    err = subprocess.CalledProcessError(returncode=5, cmd=["echo", "x"])  # type: ignore[arg-type]
    assert get_system_exit_code(err) == 5


def test_when_called_process_error_has_str_return_fallback_to_failure() -> None:
    err = subprocess.CalledProcessError(returncode="x", cmd=["echo"])  # type: ignore[arg-type]
    assert get_system_exit_code(err) == 1


def test_when_broken_pipe_occurs_the_configured_exit_code_is_obeyed() -> None:
    with config_overrides(broken_pipe_exit_code=77):
        assert get_system_exit_code(BrokenPipeError()) == 77


def test_when_broken_pipe_is_set_to_zero_it_is_returned() -> None:
    with config_overrides(broken_pipe_exit_code=0):
        assert get_system_exit_code(BrokenPipeError()) == 0


def test_when_oserror_has_errno_the_errno_is_returned() -> None:
    err = NotADirectoryError(20, "not a directory")
    assert get_system_exit_code(err) == 20


def test_when_oserror_errno_is_invalid_it_falls_back_to_failure() -> None:
    class NoisyOSError(OSError):
        """An error pretending to have an unusable errno."""

    err = NoisyOSError("oops")
    setattr(err, "errno", "bad")  # type: ignore[attr-defined]
    assert get_system_exit_code(err) == 1


def test_when_winerror_attribute_exists_it_takes_priority() -> None:
    class WithWinError(RuntimeError):
        """A runtime error that brags about winerror."""

    err = WithWinError("boom")
    setattr(err, "winerror", 55)  # type: ignore[attr-defined]
    assert get_system_exit_code(err) == 55


def test_when_winerror_attribute_is_invalid_it_falls_back_to_failure() -> None:
    class WithBadWinError(RuntimeError):
        """A runtime error with unusable winerror."""

    err = WithBadWinError("boom")
    setattr(err, "winerror", "bad")  # type: ignore[attr-defined]
    assert get_system_exit_code(err) == 1


@pytest.mark.posix_only
@pytest.mark.skipif(sys.platform.startswith("win"), reason="Windows uses winerror mapping instead of errno here")
def test_on_posix_value_error_becomes_errno_twenty_two() -> None:
    assert get_system_exit_code(ValueError("bad")) == 22


@pytest.mark.posix_only
@pytest.mark.skipif(sys.platform.startswith("win"), reason="Windows uses winerror mapping instead of errno here")
def test_on_posix_missing_file_becomes_errno_two() -> None:
    assert get_system_exit_code(FileNotFoundError("missing")) == 2


@pytest.mark.windows_only
@pytest.mark.skipif(not sys.platform.startswith("win"), reason="Winerror mapping applies only to Windows")
def test_on_windows_value_error_becomes_winerror_eighty_seven() -> None:
    assert get_system_exit_code(ValueError("bad")) == 87


@pytest.mark.os_agnostic
@pytest.mark.skipif(sys.platform.startswith("win"), reason="This simulation applies to non-Windows hosts only")
def test_when_windows_mapping_is_simulated_value_error_becomes_winerror(monkeypatch: pytest.MonkeyPatch) -> None:
    import lib_cli_exit_tools.core.exit_codes as exit_mod

    monkeypatch.setattr(exit_mod.os, "name", "nt", raising=False)
    assert get_system_exit_code(ValueError("bad")) == 87


def test_when_sysexits_style_is_enabled_value_error_becomes_usage() -> None:
    with config_overrides(exit_code_style="sysexits"):
        assert get_system_exit_code(ValueError("bad")) == 64


def test_when_sysexits_style_is_enabled_permission_error_becomes_permission_denied() -> None:
    with config_overrides(exit_code_style="sysexits"):
        assert get_system_exit_code(PermissionError("nope")) == 77


def test_when_sysexits_style_meets_system_exit_string_the_number_returns() -> None:
    assert _sysexits(SystemExit("12")) == 12


def test_when_sysexits_style_meets_bad_system_exit_string_it_falls_back_to_one() -> None:
    assert _sysexits(SystemExit("not-a-number")) == 1


def test_when_sysexits_style_meets_keyboard_interrupt_the_code_is_one_thirty() -> None:
    assert _sysexits(KeyboardInterrupt()) == 130


def test_when_sysexits_style_meets_called_process_error_the_returncode_is_used() -> None:
    err = subprocess.CalledProcessError(returncode=7, cmd=["echo"])  # type: ignore[arg-type]
    assert _sysexits(err) == 7


def test_when_sysexits_style_meets_called_process_error_with_bad_code_it_returns_one() -> None:
    err = subprocess.CalledProcessError(returncode="bad", cmd=["echo"])  # type: ignore[arg-type]
    assert _sysexits(err) == 1


def test_when_sysexits_style_meets_broken_pipe_it_uses_the_configured_exit_code() -> None:
    with config_overrides(exit_code_style="sysexits", broken_pipe_exit_code=222):
        assert _sysexits(BrokenPipeError()) == 222


def test_when_sysexits_style_meets_missing_file_it_returns_sixty_six() -> None:
    assert _sysexits(FileNotFoundError("missing")) == 66


def test_when_sysexits_style_meets_oserror_it_returns_seventy_four() -> None:
    assert _sysexits(OSError("broken")) == 74


def test_when_sysexits_style_meets_unknown_exception_it_returns_one() -> None:
    assert _sysexits(RuntimeError("mystery")) == 1


def test_when_exception_type_is_unknown_it_becomes_generic_failure() -> None:
    class Oddball(Exception):
        """An exception without a mapping."""

    assert get_system_exit_code(Oddball("mystery")) == 1


@given(st.integers(min_value=-1_000_000, max_value=1_000_000))
def test_for_all_numeric_system_exit_payloads_the_number_returns(value: int) -> None:
    assert get_system_exit_code(SystemExit(value)) == value


@given(st.integers(min_value=-1_000_000, max_value=1_000_000))
def test_for_all_numeric_strings_system_exit_roundtrips(value: int) -> None:
    assert get_system_exit_code(SystemExit(str(value))) == value


@given(st.integers(min_value=-1_000, max_value=1_000))
def test_for_all_broken_pipe_overrides_the_request_is_honoured(exit_code: int) -> None:
    with config_overrides(broken_pipe_exit_code=exit_code):
        assert get_system_exit_code(BrokenPipeError()) == exit_code
