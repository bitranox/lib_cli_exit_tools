# lib_cli_exit_tools

<!-- Badges -->
[![CI](https://github.com/bitranox/lib_cli_exit_tools/actions/workflows/ci.yml/badge.svg)](https://github.com/bitranox/lib_cli_exit_tools/actions/workflows/ci.yml)
[![CodeQL](https://github.com/bitranox/lib_cli_exit_tools/actions/workflows/codeql.yml/badge.svg)](https://github.com/bitranox/lib_cli_exit_tools/actions/workflows/codeql.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Jupyter](https://img.shields.io/badge/Jupyter-Launch-orange?logo=jupyter)](https://mybinder.org/v2/gh/bitranox/lib_cli_exit_tools/HEAD?labpath=notebooks%2FQuickstart.ipynb)
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

Pick one of the options below. All methods register the `lib_cli_exit_tools`, `cli-exit-tools`, and `lib-cli-exit-tools` commands on your PATH.

### 0) PyPI (latest release)

```bash
pip install lib_cli_exit_tools
# Pin to the current release if you need reproducibility
pip install "lib_cli_exit_tools==1.1.0"
# Upgrade to the newest release later
pip install --upgrade lib_cli_exit_tools
```

### 1) Standard virtualenv (pip)

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -e .[dev]       # dev install
# or for runtime only:
pip install .
```

### 2) Per-user (no venv)

```bash
pip install --user .
```

Note: respects PEP 668; avoid on system Python if “externally managed”. Ensure `~/.local/bin` (POSIX) is on PATH.

### 3) pipx (isolated, recommended for end users)

```bash
pipx install .
pipx upgrade lib_cli_exit_tools
# From Git tag/commit:
pipx install "git+https://github.com/bitranox/lib_cli_exit_tools@v1.1.0"
```

### 4) uv (fast installer/runner)

```bash
uv pip install -e .[dev]
uv tool install .
uvx lib_cli_exit_tools --help
```

### 5) From artifacts

```bash
python -m build
pip install dist/lib_cli_exit_tools-*.whl
pip install dist/lib_cli_exit_tools-*.tar.gz   # sdist
```

### 6) Poetry / PDM (project-managed envs)

```bash
# Poetry
poetry add lib_cli_exit_tools     # as dependency
poetry install                    # for local dev

# PDM
pdm add lib_cli_exit_tools
pdm install
```

### 7) From Git via pip (CI-friendly)

```bash
pip install "git+https://github.com/bitranox/lib_cli_exit_tools@v1.1.0#egg=lib_cli_exit_tools"
```

### 8) Conda/mamba (optional)

```bash
mamba create -n cli-exit python=3.12 pip
mamba activate cli-exit
pip install .
```

### 9) System package managers (optional distribution)

- Homebrew formula (macOS): `brew install lib_cli_exit_tools` (if published)
- Nix: flake/package for reproducible installs
- Deb/RPM via `fpm` for OS-native packages


## Usage

Console script:

```bash
# After install (pip/pipx/uv tool)
lib_cli_exit_tools --help
cli-exit-tools --help  # alias
lib_cli_exit_tools info
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

- `traceback` (`bool`, default `False`): when `True`, unhandled exceptions bubble up so you see the full traceback. The bundled CLI toggles this via `--traceback/--no-traceback`.
- `exit_code_style` (`"errno"` or `"sysexits"`, default `"errno"`): controls the numeric mapping produced by `get_system_exit_code`. `errno` returns POSIX/Windows-style codes (e.g., `FileNotFoundError → 2`, `SIGINT → 130`); `sysexits` returns BSD-style semantic codes (`EX_NOINPUT`, `EX_USAGE`, etc.).
- `broken_pipe_exit_code` (`int`, default `141`): overrides the exit status when a `BrokenPipeError` is raised (the default mirrors `128 + SIGPIPE`). Set this to `0` if you want truncation to be treated as success.

Remember that `config` is module-level—if you call the library from multiple threads or embed it in another CLI, configure it once during bootstrap before handing control to user code.

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

## Development

See [DEVELOPMENT.md](DEVELOPMENT.md) for contributor workflows, make targets, packaging sync details, and CI/publishing guidance.


## License

MIT
