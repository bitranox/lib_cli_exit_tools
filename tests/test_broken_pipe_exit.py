"""A run whose stdout reader went away exits with the broken-pipe code and prints nothing.

``run_cli`` maps ``BrokenPipeError`` to ``config.broken_pipe_exit_code`` (141), but a gone reader
rarely arrives as one. click's own ``main()`` turns EPIPE into ``SystemExit(1)`` whatever
``standalone_mode`` says, and output smaller than the stream buffer reaches the pipe only in the
final flush, which swallowed the error and left the interpreter's exit flush to fail with 120 and an
"Exception ignored" line. Measured before the fix on Linux: 1 for ``click.echo``, small or large;
120 for a small ``sys.stdout.write``. On Windows, where the C runtime reports a closed pipe as a bare
``EINVAL``, it was 120 or 22 with ``OSError: [Errno 22]`` lines on stderr, and a command that exited 3
exited 120.

Each child runs ``run_cli`` with its stdout reader closed before it writes a byte.
"""

from __future__ import annotations

import errno
import os
import subprocess
import sys
import textwrap
from typing import TYPE_CHECKING

import pytest

from lib_cli_exit_tools.application import runner

if TYPE_CHECKING:
    from pathlib import Path

_CHILD = textwrap.dedent(
    """
    import sys

    import rich_click as click

    from lib_cli_exit_tools import run_cli


    @click.group()
    @click.version_option(version="1.2.3", prog_name="child")
    def cli() -> None:
        pass


    @cli.command()
    @click.option("--size", type=int, default=3)
    def echo(size: int) -> None:
        click.echo("x" * size)


    @cli.command()
    def write() -> None:
        sys.stdout.write("hi\\n")


    @cli.command()
    @click.pass_context
    def refuse(ctx: click.Context) -> None:
        sys.stdout.write("hi\\n")
        ctx.exit(3)


    raise SystemExit(run_cli(cli, sys.argv[1:]))
    """
)


def _run_with_reader_gone(tmp_path: Path, *argv: str) -> tuple[int, str]:
    script = tmp_path / "child.py"
    script.write_text(_CHILD, encoding="utf-8")
    read_end, write_end = os.pipe()
    os.close(read_end)
    try:
        process = subprocess.Popen([sys.executable, str(script), *argv], stdout=write_end, stderr=subprocess.PIPE)
    finally:
        os.close(write_end)
    _, stderr = process.communicate(timeout=60)
    return process.returncode, stderr.decode("utf-8", "replace")


@pytest.mark.parametrize(
    "argv",
    [
        pytest.param(["echo"], id="small echo"),
        pytest.param(["echo", "--size", "200000"], id="large echo"),
        pytest.param(["write"], id="small write"),
        pytest.param(["--version"], id="click's own version printer"),
        pytest.param(["--help"], id="help"),
    ],
)
def test_a_gone_reader_exits_with_the_broken_pipe_code_and_says_nothing(tmp_path: Path, argv: list[str]) -> None:
    assert _run_with_reader_gone(tmp_path, *argv) == (141, "")


def test_a_command_s_own_failure_keeps_its_code_when_the_reader_is_gone(tmp_path: Path) -> None:
    assert _run_with_reader_gone(tmp_path, "refuse") == (3, "")


@pytest.mark.parametrize(
    ("error", "windows", "gone"),
    [
        pytest.param(BrokenPipeError(errno.EPIPE, "Broken pipe"), False, True, id="EPIPE"),
        pytest.param(OSError(errno.EINVAL, "Invalid argument"), True, True, id="bare EINVAL on Windows"),
        pytest.param(OSError(errno.EINVAL, "Invalid argument"), False, False, id="EINVAL elsewhere"),
        pytest.param(OSError(errno.EINVAL, "Invalid argument", "bad?name"), True, False, id="EINVAL naming a file"),
        pytest.param(OSError(errno.ENOSPC, "No space left on device"), False, False, id="a full disk"),
    ],
)
def test_the_gone_reader_predicate(error: OSError, windows: bool, gone: bool) -> None:
    assert runner.is_gone_reader_error(error, windows=windows) is gone


def test_click_s_exit_raised_while_handling_a_broken_pipe_maps_to_the_broken_pipe_code(reset_config: None) -> None:
    try:
        try:
            raise BrokenPipeError(errno.EPIPE, "Broken pipe")
        except BrokenPipeError:
            raise SystemExit(1)  # noqa: B904 - click raises it this way, chaining only by context
    except SystemExit as exit_:
        assert runner.handle_cli_exception(exit_) == 141


def test_a_plain_system_exit_keeps_its_code(reset_config: None) -> None:
    assert runner.handle_cli_exception(SystemExit(1)) == 1
