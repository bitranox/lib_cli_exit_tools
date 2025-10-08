"""Exit codes behave like a clear contract."""

from __future__ import annotations

import subprocess
import sys

import pytest

from lib_cli_exit_tools.core.configuration import config
from lib_cli_exit_tools.core.exit_codes import get_system_exit_code


pytestmark = pytest.mark.usefixtures("reset_config_state")


def test_system_exit_carries_explicit_integer() -> None:
    assert get_system_exit_code(SystemExit(7)) == 7


def test_system_exit_none_means_success() -> None:
    assert get_system_exit_code(SystemExit(None)) == 0


def test_system_exit_string_is_cast_to_int() -> None:
    assert get_system_exit_code(SystemExit("9")) == 9


def test_system_exit_unparsable_string_falls_back_to_generic_failure() -> None:
    assert get_system_exit_code(SystemExit("boom")) == 1


def test_keyboard_interrupt_abides_by_shell_convention() -> None:
    assert get_system_exit_code(KeyboardInterrupt()) == 130


def test_called_process_error_yields_returncode() -> None:
    error = subprocess.CalledProcessError(returncode=5, cmd=["echo", "x"])  # type: ignore[arg-type]
    assert get_system_exit_code(error) == 5


def test_called_process_error_with_str_returncode_falls_back_to_generic_failure() -> None:
    error = subprocess.CalledProcessError(returncode="x", cmd=["echo"])  # type: ignore[arg-type]
    assert get_system_exit_code(error) == 1


def test_broken_pipe_obeys_configured_exit_code() -> None:
    config.broken_pipe_exit_code = 77
    assert get_system_exit_code(BrokenPipeError()) == 77


def test_broken_pipe_reflects_updated_configuration() -> None:
    config.broken_pipe_exit_code = 0
    assert get_system_exit_code(BrokenPipeError()) == 0


def test_oserror_uses_errno_value() -> None:
    error = NotADirectoryError(20, "not a directory")
    assert get_system_exit_code(error) == 20


def test_oserror_with_bad_errno_returns_generic_failure() -> None:
    class UnrulyOSError(OSError):
        """An OSError that advertises a bogus errno."""

    error = UnrulyOSError("oops")
    setattr(error, "errno", "bad")  # type: ignore[attr-defined]
    assert get_system_exit_code(error) == 1


def test_winerror_attribute_trumps_errno() -> None:
    class CustomError(RuntimeError):
        """Carries a winerror attribute for Windows mapping."""

    error = CustomError("boom")
    setattr(error, "winerror", 55)  # type: ignore[attr-defined]
    assert get_system_exit_code(error) == 55


def test_winerror_with_bad_type_falls_back_to_generic_failure() -> None:
    class CustomError(RuntimeError):
        """Carries a non-integer winerror attribute."""

    error = CustomError("boom")
    setattr(error, "winerror", "bad")  # type: ignore[attr-defined]
    assert get_system_exit_code(error) == 1


@pytest.mark.skipif(sys.platform.startswith("win"), reason="POSIX errno table differs on Windows")
def test_posix_value_error_maps_to_errno_22() -> None:
    assert get_system_exit_code(ValueError("bad")) == 22


@pytest.mark.skipif(sys.platform.startswith("win"), reason="POSIX errno table differs on Windows")
def test_posix_file_not_found_maps_to_errno_2() -> None:
    assert get_system_exit_code(FileNotFoundError("missing")) == 2


@pytest.mark.skipif(not sys.platform.startswith("win"), reason="Windows-only behaviour")
def test_windows_value_error_maps_to_winerror_87() -> None:
    assert get_system_exit_code(ValueError("bad")) == 87


@pytest.mark.skipif(sys.platform.startswith("win"), reason="Simulate Windows mapping when not on Windows")
def test_windows_value_error_simulation_maps_to_winerror(monkeypatch: pytest.MonkeyPatch) -> None:
    import lib_cli_exit_tools.core.exit_codes as exit_mod

    monkeypatch.setattr(exit_mod.os, "name", "nt", raising=False)
    assert get_system_exit_code(ValueError("bad")) == 87


def test_sysexits_value_error_maps_to_usage_code() -> None:
    config.exit_code_style = "sysexits"
    assert get_system_exit_code(ValueError("bad")) == 64


def test_sysexits_permission_error_maps_to_permission_code() -> None:
    config.exit_code_style = "sysexits"
    assert get_system_exit_code(PermissionError("nope")) == 77


def test_unknown_exception_falls_back_to_generic_failure() -> None:
    class Oddball(Exception):
        pass

    assert get_system_exit_code(Oddball("mystery")) == 1
