"""Core-layer exit-code mapping tests.

Purpose:
    Exercise the pure exit-code translation logic without invoking Click or
    signal adapters.
Contents:
    * Behavioural tests covering `SystemExit`, errno/winerror mappings, and
      sysexits mode toggles.
System Integration:
    Validates the guarantees exposed by `lib_cli_exit_tools.core.exit_codes`.
"""

from __future__ import annotations

import signal
import subprocess
import sys

import pytest

from lib_cli_exit_tools.core.configuration import config
from lib_cli_exit_tools.core.exit_codes import get_system_exit_code


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (SystemExit(99), 99),
        (SystemExit(None), 0),
        (SystemExit("2"), 2),
    ],
)
def test_system_exit_variants(exc: SystemExit, expected: int) -> None:
    """SystemExit with integer-like payloads maps to their numeric exit codes."""
    assert get_system_exit_code(exc) == expected


def test_system_exit_invalid_string_falls_back_to_one() -> None:
    """Non-numeric SystemExit payloads fall back to exit code 1."""
    assert get_system_exit_code(SystemExit("oops")) == 1


@pytest.mark.skipif(sys.platform.startswith("win"), reason="POSIX-specific expectations")
def test_posix_errno_mappings() -> None:
    """POSIX errno exceptions translate to their documented numeric codes."""
    assert get_system_exit_code(FileNotFoundError("missing")) == 2
    assert get_system_exit_code(ValueError("bad")) == 22


def test_winerror_attribute_takes_priority(monkeypatch: pytest.MonkeyPatch) -> None:
    """Winerror attribute overrides generic errno mapping when present."""

    class CustomError(RuntimeError):
        pass

    err = CustomError("boom")
    setattr(err, "winerror", 42)  # type: ignore[attr-defined]
    assert getattr(err, "winerror", None) == 42
    assert get_system_exit_code(err) == 42


def test_keyboard_interrupt_maps_to_130() -> None:
    """KeyboardInterrupts propagate the conventional 130 exit code."""
    assert get_system_exit_code(KeyboardInterrupt()) == 130


def test_subprocess_called_process_error() -> None:
    """CalledProcessError surfaces its returncode as the exit status."""
    err = subprocess.CalledProcessError(returncode=7, cmd=["echo", "x"])  # type: ignore[arg-type]
    assert get_system_exit_code(err) == 7


def test_oserror_errno_used_when_available() -> None:
    """OSError instances reuse their errno value for exit codes."""
    err = NotADirectoryError(20, "not a dir")
    assert isinstance(err.errno, int)
    assert err.errno == 20
    assert get_system_exit_code(err) == 20


def test_broken_pipe_respects_configured_code() -> None:
    """BrokenPipeError follows the configurable broken-pipe exit code."""
    config.broken_pipe_exit_code = 141
    assert config.broken_pipe_exit_code == 141
    assert get_system_exit_code(BrokenPipeError()) == 141
    config.broken_pipe_exit_code = 0
    assert config.broken_pipe_exit_code == 0
    assert get_system_exit_code(BrokenPipeError()) == 0


def test_sysexits_overrides_errno_mapping() -> None:
    """Enabling sysexits remaps value and permission errors to BSD codes."""
    config.exit_code_style = "sysexits"
    assert get_system_exit_code(ValueError("bad")) == 64
    assert get_system_exit_code(PermissionError("nope")) == 77


@pytest.mark.skipif(sys.platform.startswith("win"), reason="Simulated Windows mapping unnecessary on Windows")
def test_value_error_windows_mapping_simulated(monkeypatch: pytest.MonkeyPatch) -> None:
    """Switching to Windows semantics maps ValueError to winerror 87."""
    import lib_cli_exit_tools.core.exit_codes as exit_mod

    monkeypatch.setattr(exit_mod.os, "name", "nt", raising=False)
    assert get_system_exit_code(ValueError("x")) == 87


@pytest.mark.skipif(not sys.platform.startswith("win"), reason="Windows-specific behaviour")
def test_value_error_windows_mapping_windows() -> None:
    """On Windows, ValueError maps to winerror 87 without monkeypatching."""
    assert sys.platform.startswith("win")
    assert get_system_exit_code(ValueError("x")) == 87


def test_called_process_error_with_invalid_returncode() -> None:
    """Non-integer return codes on CalledProcessError fall back to 1."""
    err = subprocess.CalledProcessError(returncode="x", cmd=["echo"])  # type: ignore[arg-type]
    assert get_system_exit_code(err) == 1


def test_winerror_with_bad_type_falls_back_to_one() -> None:
    """Invalid winerror values fall back to the generic exit code."""

    class CustomError(Exception):
        pass

    err = CustomError("boom")
    setattr(err, "winerror", "bad")  # type: ignore[attr-defined]
    assert get_system_exit_code(err) == 1


def test_errno_with_bad_type_falls_back_to_one() -> None:
    """Invalid errno values fall back to the generic exit code."""

    class CustomOSError(OSError):
        pass

    err = CustomOSError("oops")
    setattr(err, "errno", "bad")  # type: ignore[attr-defined]
    assert get_system_exit_code(err) == 1


@pytest.mark.skipif(not sys.platform.startswith("win"), reason="Windows-specific behaviour")
def test_default_signal_specs_windows_has_sigbreak() -> None:
    """Ensure SIGBREAK is present on Windows runners."""
    from lib_cli_exit_tools.adapters.signals import default_signal_specs, SigBreakInterrupt

    specs = default_signal_specs()
    signums = {spec.signum for spec in specs}
    assert any(spec.exception is SigBreakInterrupt for spec in specs), "SIGBREAK spec missing on Windows"
    assert hasattr(signal, "SIGBREAK")
    assert signal.SIGBREAK in signums
