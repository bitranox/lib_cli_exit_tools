# lib_cli_exit_tools

<!-- Badges -->
[![CI](https://github.com/bitranox/lib_cli_exit_tools/actions/workflows/ci.yml/badge.svg)](https://github.com/bitranox/lib_cli_exit_tools/actions/workflows/ci.yml)
[![CodeQL](https://github.com/bitranox/lib_cli_exit_tools/actions/workflows/codeql.yml/badge.svg)](https://github.com/bitranox/lib_cli_exit_tools/actions/workflows/codeql.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Open in Codespaces](https://img.shields.io/badge/Codespaces-Open-blue?logo=github&logoColor=white&style=flat-square)](https://codespaces.new/bitranox/lib_cli_exit_tools?quickstart=1)
[![PyPI](https://img.shields.io/pypi/v/lib_cli_exit_tools.svg)](https://pypi.org/project/lib_cli_exit_tools/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/lib_cli_exit_tools.svg)](https://pypi.org/project/lib_cli_exit_tools/)
[![Code Style: Ruff](https://img.shields.io/badge/Code%20Style-Ruff-46A3FF?logo=ruff&labelColor=000)](https://docs.astral.sh/ruff/)
[![codecov](https://codecov.io/gh/bitranox/lib_cli_exit_tools/graph/badge.svg?token=z1D8JSjWEH)](https://codecov.io/gh/bitranox/lib_cli_exit_tools)
[![Maintainability](https://qlty.sh/gh/bitranox/projects/lib_cli_exit_tools/maintainability.svg)](https://qlty.sh/gh/bitranox/projects/lib_cli_exit_tools)
[![Known Vulnerabilities](https://snyk.io/test/github/bitranox/lib_cli_exit_tools/badge.svg)](https://snyk.io/test/github/bitranox/lib_cli_exit_tools)

Small helpers for robust CLI exit handling:
- Portable signal handling (SIGINT, SIGTERM/SIGBREAK)
- Consistent exception → exit code mapping
- Concise error printing with optional traceback and subprocess stdout/stderr capture

## Install

Requires Python 3.13 or newer.

```bash
pip install lib_cli_exit_tools
```

See [INSTALL.md](INSTALL.md) for editable installs, pipx/uv, package-manager builds, and troubleshooting tips.

## Usage

Console script:

```bash
# After install (pip/pipx/uv tool)
lib_cli_exit_tools --help
cli-exit-tools --help  # alias
lib_cli_exit_tools info
lib_cli_exit_tools fail  # intentionally trigger RuntimeError to test error paths
```

### Embed in your own CLI

The `run_cli` helper wraps any Click command with lib_cli_exit_tools’ signal and error handling.

```python
from __future__ import annotations

import click

from lib_cli_exit_tools import run_cli


@click.command()
def hello() -> None:
    """Minimal Click command with automatic signal-aware exit handling."""

    click.echo("Hello from lib_cli_exit_tools!")


if __name__ == "__main__":
    # run_cli handles SIGINT/SIGTERM/SIGBREAK, Click exceptions, and converts
    # any other exception into an appropriate exit code.
    raise SystemExit(run_cli(hello))
```

Run it with:

```bash
python hello.py
```

Library:

```python
import lib_cli_exit_tools

lib_cli_exit_tools.config.traceback = False  # show short messages
try:
    raise FileNotFoundError("missing.txt")
except Exception as e:
    code = lib_cli_exit_tools.get_system_exit_code(e)   # 2 on POSIX
    lib_cli_exit_tools.print_exception_message()        # prints: FileNotFoundError: missing.txt
    raise SystemExit(code)
```

Command names registered on install
- lib_cli_exit_tools (default)
- cli-exit-tools (alias)
- python -m lib_cli_exit_tools (module entry)

If you installed with --user or in a venv, make sure the corresponding bin directory is on PATH:
- Linux/macOS venv: .venv/bin
- Linux/macOS user: ~/.local/bin
- Windows venv: .venv\Scripts
- Windows user: %APPDATA%\Python\PythonXY\Scripts

### Runtime configuration

All configuration lives on the module-level `lib_cli_exit_tools.config` object. Adjust it once during startup; the settings apply process-wide:

```python
from lib_cli_exit_tools import config

config.traceback = True              # emit full tracebacks instead of short messages
config.exit_code_style = "sysexits"  # emit BSD-style exit codes (EX_USAGE, EX_NOINPUT, …)
config.broken_pipe_exit_code = 0     # treat BrokenPipeError as a benign truncation
```

Field reference:

- `traceback` (`bool`, default `False`): when `True`, `handle_cli_exception` renders a full Rich traceback to stderr and then returns a non-zero exit code. The original exception is not re-raised; callers should rely on the rendered output and returned status. The bundled CLI toggles this via `--traceback/--no-traceback`.
- `exit_code_style` (`"errno"` or `"sysexits"`, default `"errno"`): controls the numeric mapping produced by `get_system_exit_code`. `errno` returns POSIX/Windows-style codes (e.g., `FileNotFoundError → 2`, `SIGINT → 130`); `sysexits` returns BSD-style semantic codes (`EX_NOINPUT`, `EX_USAGE`, etc.).
- `broken_pipe_exit_code` (`int`, default `141`): overrides the exit status when a `BrokenPipeError` is raised (the default mirrors `128 + SIGPIPE`). Set this to `0` if you want truncation to be treated as success.

Remember that `config` is module-level—if you call the library from multiple threads or embed it in another CLI, configure it once during bootstrap before handing control to user code. When you need temporary overrides (for tests or nested CLIs), wrap the change with the built-in context manager so state is restored automatically:

```python
from lib_cli_exit_tools import config_overrides, config

with config_overrides(traceback=True):
    # tracebacks enabled only within this block
    run_something()

# state restored to previous values here
```

To return to baseline defaults, call `lib_cli_exit_tools.reset_config()`.

## Testing

Install the project with development extras before running the full test matrix:

```bash
pip install -e .[dev]
```

Afterwards, execute the consolidated quality gate:

```bash
make test
```

The suite includes OS-aware cases (POSIX, Windows-specific signal handling), so
run it on each target platform you support to keep coverage consistent.

If your environment reports “cannot execute” when running `pytest`, the auto-generated entry-point script likely points at a removed interpreter. Reinstall the dev extras or invoke tests with `python -m pytest` (for example, `python -m pytest tests/`).

When coverage uploads are skipped (no Codecov token), `make test` still writes `coverage.xml` and `codecov.xml` to the project root so you can inspect results locally or feed them into other tooling.

## Public API Reference

The package re-exports the helpers below via `lib_cli_exit_tools.__all__`. Import them directly with `from lib_cli_exit_tools import …`.

### `config`
Mutable dataclass-like singleton holding process-wide settings. Configure it during CLI startup.

- `traceback` (`bool`): `True` to surface full Python tracebacks; `False` keeps short, coloured summaries.
- `exit_code_style` (`'errno' | 'sysexits'`): Selects POSIX/Windows errno-style exit codes or BSD `sysexits` semantics.
- `broken_pipe_exit_code` (`int`): Overrides the exit status for `BrokenPipeError` (default `141`).
- `traceback_force_color` (`bool`): Forces Rich-coloured tracebacks even when stderr is not a TTY.

### `run_cli(cli, argv=None, *, prog_name=None, signal_specs=None, install_signals=True, exception_handler=None, signal_installer=None) -> int`
Wrap a Click command or group so every invocation shares the same signal handling and exit-code policy. Returns the numeric exit code instead of exiting the process.

Parameters:
- `cli`: `click.BaseCommand` to execute.
- `argv`: Optional iterable of CLI arguments (excluding program name).
- `prog_name`: Override the program name shown in help/version output.
- `signal_specs`: Iterable of `SignalSpec` objects to customise signal handling; defaults to `default_signal_specs()`.
- `install_signals`: Set `False` when the host application already manages signal handlers.
- `exception_handler`: Optional callable receiving the raised exception and returning an exit code; defaults to ``handle_cli_exception``.
- `signal_installer`: Optional callable mirroring ``install_signal_handlers`` for embedding scenarios.

### `handle_cli_exception(exc, *, signal_specs=None, echo=None) -> int`
Translate exceptions raised by Click commands into deterministic exit codes, honouring configured signal mappings and traceback policy.

Parameters:
- `exc`: Exception instance to classify.
- `signal_specs`: Optional iterable of `SignalSpec` objects for custom signal handling.
- `echo`: Callable matching `click.echo` signature, allowing custom stderr routing during tests or embedding.

### `get_system_exit_code(exc) -> int`
Compute a platform-aware exit status for arbitrary exceptions (errno mappings on POSIX/Windows or BSD `sysexits` when enabled).

Parameters:
- `exc`: Exception instance to classify.

### `print_exception_message(trace_back=config.traceback, length_limit=500, stream=None) -> None`
Emit the active exception using Rich formatting. Produces a coloured traceback when `trace_back` is `True`, otherwise prints a truncated summary in red. Respects `config.traceback_force_color` and mirrors the behaviour of `handle_cli_exception` (tracebacks are rendered before the helper returns an exit status).

Parameters:
- `trace_back`: Toggle between full traceback rendering (`True`) and short summary (`False`).
- `length_limit`: Maximum characters for summary output.
- `stream`: Target text stream; defaults to `sys.stderr`.

### `i_should_fail()`
Deterministically raise `RuntimeError('i should fail')` to exercise error-handling paths. Useful for smoke-testing exit-code translation, CLI traceback toggles, and log formatting without inventing ad-hoc failing commands.

### `flush_streams() -> None`
Best-effort flush of `sys.stdout` and `sys.stderr`, ensuring buffered output is written before exit.

### `default_signal_specs() -> list[SignalSpec]`
Return the default signal mapping for the current platform (always includes `SIGINT`, plus `SIGTERM`/`SIGBREAK` when available).

### `install_signal_handlers(specs=None) -> Callable[[], None]`
Register handlers that raise structured exceptions for the provided specs and return a restoration callback. Invoke the callback (typically in a `finally` block) to restore previous handlers.

Parameters:
- `specs`: Iterable of `SignalSpec` objects; defaults to `default_signal_specs()`.

### `SignalSpec(signum: int, exception: type[BaseException], message: str, exit_code: int)`
Lightweight dataclass describing how a signal maps to an exception, stderr message, and exit code.

Fields:
- `signum`: Numeric signal value passed to `signal.signal`.
- `exception`: Exception type raised by the handler.
- `message`: Human-readable text echoed when the signal fires.
- `exit_code`: Exit status returned to the OS.

### `CliSignalError` and subclasses
Hierarchy of marker exceptions raised when signal handlers trigger. Use them to differentiate signal-driven exits from other failures.

- `CliSignalError`: Base class.
- `SigIntInterrupt`: Raised on `SIGINT` (Ctrl+C); maps to exit code `130`.
- `SigTermInterrupt`: Raised on `SIGTERM`; maps to exit code `143`.
- `SigBreakInterrupt`: Raised on Windows `SIGBREAK`; maps to exit code `149`.

### `default_signal_specs`, `install_signal_handlers`, and `run_cli` contract summary
When `run_cli` executes your Click command it will:
1. Build a signal spec list (custom or default).
2. Optionally install handlers that raise the exceptions above.
3. Execute the command with `standalone_mode=False`.
4. Funnel any exception through `handle_cli_exception`.
5. Restore prior signal handlers and flush streams before returning (or rely on any injected replacements).

This behaviour keeps CLI wiring consistent across projects embedding `lib_cli_exit_tools` while still allowing custom hooks when needed.

### Advanced CLI wiring

For larger applications, keep module execution, console scripts, and shared helpers aligned. The snippet below shows how `__main__.py` can catch unexpected errors and map them through `lib_cli_exit_tools` before exiting:

```python
# src/your_package/__main__.py
from __future__ import annotations

import lib_cli_exit_tools

from .cli import main

if __name__ == "__main__":
    try:
        exit_code = int(main())
    except BaseException as exc:  # fallback to shared exit helpers
        lib_cli_exit_tools.print_exception_message()
        exit_code = lib_cli_exit_tools.get_system_exit_code(exc)
    raise SystemExit(exit_code)
```

A multi-command Click CLI can reuse the same configuration object and expose custom commands while still delegating wiring to `run_cli`:

```python
# src/your_package/cli.py
from __future__ import annotations

from typing import Optional, Sequence

import click
import lib_cli_exit_tools

from . import __init__conf__
from .lib_template import hello_world as _hello_world
from .lib_template import i_should_fail as _fail

CLICK_CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])  # noqa: C408


@click.group(help=__init__conf__.title, context_settings=CLICK_CONTEXT_SETTINGS)
@click.version_option(
    version=__init__conf__.version,
    prog_name=__init__conf__.shell_command,
    message=f"{__init__conf__.shell_command} version {__init__conf__.version}",
)
@click.option(
    "--traceback/--no-traceback",
    is_flag=True,
    default=False,
    help="Show full Python traceback on errors",
)
@click.pass_context
def cli(ctx: click.Context, traceback: bool) -> None:
    """Root CLI group. Stores global opts in context & shared config."""
    ctx.ensure_object(dict)
    ctx.obj["traceback"] = traceback
    lib_cli_exit_tools.config.traceback = traceback


@cli.command("info", context_settings=CLICK_CONTEXT_SETTINGS)
def cli_info() -> None:
    """Print project information."""
    __init__conf__.print_info()


@cli.command("hello", context_settings=CLICK_CONTEXT_SETTINGS)
def cli_hello() -> None:
    """Print the standard hello message."""
    _hello_world()


@cli.command("fail", context_settings=CLICK_CONTEXT_SETTINGS)
def cli_fail() -> None:
    """Trigger the intentional failure helper."""
    _fail()


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Entrypoint returning an exit code via shared run_cli helper."""
    return lib_cli_exit_tools.run_cli(
        cli,
        argv=list(argv) if argv is not None else None,
        prog_name=__init__conf__.shell_command,
    )
```

When installed, the generated console scripts (`lib_cli_exit_tools`, `cli-exit-tools`, `lib-cli-exit-tools`) will import `your_package.cli:main`, and `python -m your_package` will follow the same code path via `__main__.py`.

## Exit Codes

- SIGINT → 130, SIGTERM → 143 (POSIX), SIGBREAK → 149 (Windows)
- SystemExit(n) → n
- Common exceptions map to POSIX/Windows codes (FileNotFoundError, PermissionError, ValueError, etc.)

### Broken pipe behavior
- Default: exit 141 quietly (128+SIGPIPE), no noisy error output.
- Configure: `config.broken_pipe_exit_code = 0` to treat as benign truncation, or `32` (EPIPE).

### Sysexits mode (optional)
- Set `config.exit_code_style = "sysexits"` to map ValueError/TypeError → EX_USAGE(64),
  FileNotFoundError → EX_NOINPUT(66), PermissionError → EX_NOPERM(77), generic OSError → EX_IOERR(74).

## Additional Documentation

- [INSTALL](INSTALL.md)
- [CHANGELOG](CHANGELOG.md)
- [CONTRIBUTING](CONTRIBUTING.md)
- [DEVELOPMENT](DEVELOPMENT.md)
- [MODULE REFERENCE](docs/system-design/module_reference.md)
- [LICENSE](LICENSE)
